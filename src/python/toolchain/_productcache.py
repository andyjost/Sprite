'''
The product cache: the compiled products of a module, kept outside its tree
and found again by content.

The C++ compiler is the slow step of the toolchain.  A tree compiles each
module of the Curry library and of the test pool once per ABI stamp, and a
tree whose products were removed, or made stale by an edit and its revert,
compiles them again.  The cache keeps a copy of the products of each compile
under a key made from what the products depend on, so that a later compile
of the same module under the same conditions places the copy instead.

Layout.  The cache is a directory of entries::

    <root>/<stamp digest>/<key>/<Module>.cpp
                               /<Module>.so
                               /<Module>.so.abi

The root is ``config.product_cache_dir`` (the environment variable
SPRITE_PRODUCT_CACHE; the empty string turns the cache off).  The stamp
digest is the digest of the ABI stamp (``toolchain.object_digest`` of the
C++ backend): the runtime headers, the flags of the flavor and of the
collector, so an entry serves one runtime.  The key is a digest of the facts
that decide the generated code and the object (see ``product_key``): the
module's name and its own texts (its Curry source, its ICurry file and its
JSON, each one that exists; the JSON is the input of the code generator,
and a new JSON from the same source, after a change to the ICurry reader or
to a pinned ICurry file, must miss), the sources of the modules it imports,
and the facts the backend names (the format of the generated code, the
sources of the code generator, the flags of the optimizer, the route from
Curry to ICurry, the real paths of the installation, which is the second
line of the stamp, and of the source directory; see
``Cpp2So.product_facts`` of the C++ backend for the list and the reasons).
An object names the two paths, so an entry
serves one tree: the same tree after its products were removed, or after
an edit and its revert; two trees share an entry once the object names no
absolute path.  The names of the files in an entry are the names of the
products beside the source.  The stamp stored in an entry is the one the
compile wrote; a restore writes a stamp of its own for the installation
that restores.

Concurrency.  Two processes may store the same key at once: a store writes
its files into a temporary directory beside the entry and renames the
directory into place, so an entry is whole or absent; the second writer
finds the entry and removes its own files.  A restore places a file through
a temporary name in the product directory and a rename, so a reader never
sees a partial file.  The shared object is hard-linked, in both directions,
when the cache and the product directory lie on one file system (the linker
and the compile step write a new file, never into the old one), else
copied; the generated C++ and the stamp are copied, because the emitter
writes the generated file in place.

The modification times of the restored files are set in the order of the
toolchain (the C++ after the JSON, the object after the C++), so the plan
finds the object the newest file of the module (``_findcurry.currentfile``).

Growth.  Nothing in the toolchain removes an entry: each change to the
runtime headers, to the compiler or to the flags starts a new digest
directory, and the old one stays.  ``prune`` removes the digest directories
other than the ones given, and the temporary directories of a store that
was interrupted; the test runner calls it on its own cache after the
prepare pass (tests/README, section 10).  The directory may be deleted at
any time.
'''

from .. import cache, config
from ..utility import filesys
import hashlib, logging, os, shutil, tempfile, time

logger = logging.getLogger(__name__)

__all__ = [
    'KEY_FORMAT', 'chain_digest', 'counts', 'enabled', 'entry_dir', 'excluded'
  , 'import_closure', 'lookup', 'product_key', 'prune', 'reset_counts'
  , 'restore', 'root', 'store'
  ]

# The format of the key.  Raise it when the layout of an entry or the parts
# of the key change; the entries of the old format are then never found.
# Format 2 added the ICurry file and the JSON of the module to the chain.
KEY_FORMAT = 2

# The suffixes of the files a store and a restore may hard-link.  The others
# are copied: the emitter writes a generated file in place, and a link would
# carry the next generation into the entry.
LINK_SUFFIXES = ('.so',)

# The counts of this process: the products restored from the cache and the
# products stored in it.  sprite-make reports them.
counts = {'restored': 0, 'stored': 0}

def reset_counts():
  counts['restored'] = 0
  counts['stored'] = 0

def root():
  '''The root directory of the cache, or None when the cache is off.'''
  return config.product_cache_dir()

def enabled():
  '''Tells whether the cache is on (SPRITE_PRODUCT_CACHE is not the empty string).'''
  return root() is not None

def _module_texts(curryfile):
  '''
  The module's own texts, as pairs of a label and the bytes: its Curry
  source, its ICurry file and its JSON, each one that exists, in that
  order.  Empty when none of them exists.  The JSON is the input of the
  code generator, so a JSON written again from the same source by another
  ICurry reader, or from a pinned ICurry file that was replaced, changes
  the key; the source alone would not see it.
  '''
  from . import _filenames
  candidates = [('curry', curryfile), ('icy', _filenames.icurryfilename(curryfile))]
  candidates += [('json', name) for name in _filenames.jsonfilenames(curryfile)]
  texts = []
  for label, filename in candidates:
    try:
      with open(filename, 'rb') as stream:
        texts.append((label, stream.read()))
    except FileNotFoundError:
      continue
  return texts

def _imports(curryfile):
  '''
  The names of the modules the module of ``curryfile`` imports: a scan of
  the source when it exists (``cache.SourceInfo``), else the imports of the
  JSON beside the products; nothing when neither exists.
  '''
  from . import _filenames, _loadcurry
  if os.path.isfile(curryfile):
    return cache._sourceinfo(curryfile).imports
  for jsonfile in _filenames.jsonfilenames(curryfile):
    if os.path.isfile(jsonfile):
      try:
        return list(_loadcurry.loadjson(jsonfile).imports)
      except Exception:
        return []
  return []

def import_closure(curryfile, currypath=()):
  '''
  The modules that the module of ``curryfile`` imports, transitively, as
  Curry source files in the Curry path and in the library of the
  installation, by name: ``cache.import_closure`` for a module that may
  lack a source (its imports then come from its JSON).  The Prelude is
  implicit.  A module without a source in either place is left out.
  '''
  curryfile = os.path.abspath(curryfile)
  searchpaths = [os.path.dirname(curryfile)]
  searchpaths += [os.path.abspath(p) for p in currypath if p]
  # The library of the installation is always on the path of a compile
  # (config.currypath appends it), so the key sees the Prelude and the other
  # library modules whatever path the caller gives.
  searchpaths.append(os.path.abspath(config.system_curry_path()))
  closure = {}
  pending = ['Prelude'] + list(_imports(curryfile))
  seen = set()
  while pending:
    name = pending.pop()
    if name in seen:
      continue
    seen.add(name)
    relpath = name.replace('.', os.sep) + '.curry'
    for found in filesys.findfiles(searchpaths, relpath):
      found = os.path.abspath(found)
      if found != curryfile:
        info = cache._sourceinfo(found)
        closure[name] = info
        pending.extend(info.imports)
      break
  return closure

def excluded(curryfile):
  '''
  Tells whether the products of a module stay out of the cache: its source
  lies in the temporary directory of the system (tempfile.gettempdir) or in
  a directory that str2module made.  Such products die with their
  directory, and a test run makes hundreds of them.
  '''
  from . import _str2module
  directory = os.path.realpath(os.path.dirname(os.path.abspath(curryfile)))
  tmpdir = os.path.realpath(tempfile.gettempdir())
  if directory == tmpdir or directory.startswith(tmpdir + os.sep):
    return True
  return _str2module.is_temporary(curryfile)

def chain_digest(curryfile, currypath=()):
  '''
  A digest of the source chain of a module: its own texts (see
  ``_module_texts``: the source, the ICurry file and the JSON, each one
  that exists) and the name and the text of every module it imports,
  transitively, that has a source in the Curry path (``import_closure``;
  the Prelude is implicit).  None when the module has no text.  The
  directory of the module is not part of it.
  '''
  texts = _module_texts(curryfile)
  if not texts:
    return None
  hasher = hashlib.sha256()
  for label, text in texts:
    hasher.update(label.encode('utf-8'))
    hasher.update(b'\0')
    hasher.update(hashlib.sha256(text).hexdigest().encode('utf-8'))
    hasher.update(b'\0')
  for name, info in sorted(import_closure(curryfile, currypath).items()):
    hasher.update(name.encode('utf-8'))
    hasher.update(b'\0')
    hasher.update(info.digest.encode('utf-8'))
    hasher.update(b'\0')
  return hasher.hexdigest()

def product_key(curryfile, currypath=(), facts=()):
  '''
  The key of the products of the module of ``curryfile``: a digest of
  KEY_FORMAT, of the name of the module, of ``facts`` (strings the backend
  names, in order) and of the source chain (``chain_digest``).  The name is
  part of it because the generated code and the symbols of the object carry
  it: two modules of one text under two names get two entries.  None when
  the module has no text.
  '''
  chain = chain_digest(curryfile, currypath)
  if chain is None:
    return None
  modulename = os.path.basename(curryfile)[:-len('.curry')]
  hasher = hashlib.sha256()
  parts = ['sprite products %d' % KEY_FORMAT, modulename] + list(facts) + [chain]
  for part in parts:
    hasher.update(str(part).encode('utf-8'))
    hasher.update(b'\0')
  return hasher.hexdigest()

def entry_dir(digest, key, cache_root=None):
  '''The directory of an entry.  ``cache_root`` defaults to ``root()``.'''
  if cache_root is None:
    cache_root = root()
  return os.path.join(cache_root, digest, key)

def lookup(digest, key, names, cache_root=None):
  '''
  The files of the entry under ``digest`` and ``key``, by name, when every
  file of ``names`` is there; else None.
  '''
  if cache_root is None:
    cache_root = root()
  if cache_root is None:
    return None
  directory = entry_dir(digest, key, cache_root)
  found = {}
  for name in names:
    path = os.path.join(directory, name)
    if not os.path.isfile(path):
      return None
    found[name] = path
  return found

def _same_device(a, b):
  try:
    return os.stat(a).st_dev == os.stat(b).st_dev
  except OSError:
    return False

def _place(source, target, link):
  '''
  Puts a copy of ``source`` at ``target`` through a temporary name in the
  directory of the target and a rename.  With ``link``, the copy is a hard
  link when the two lie on one file system.  The target may exist; it is
  replaced, never written into.
  '''
  directory = os.path.dirname(target)
  fd, tmp = tempfile.mkstemp(dir=directory, prefix='.product-', suffix='.tmp')
  os.close(fd)
  with filesys.remove_file_on_error(tmp):
    linked = False
    if link and _same_device(source, directory):
      os.unlink(tmp)
      try:
        os.link(source, tmp)
      except OSError as exc:
        # A file system that refuses the link (a link limit, a policy): a
        # copy serves as well.
        logger.debug('cannot link %r to %r (%s); copied', source, tmp, exc)
      else:
        linked = True
    if not linked:
      shutil.copyfile(source, tmp)
      shutil.copymode(source, tmp)
    os.replace(tmp, target)

def store(digest, key, files, cache_root=None):
  '''
  Stores ``files`` (paths; their base names name them in the entry) under
  ``digest`` and ``key``.  An entry that exists is replaced.  Two writers of
  one key at once both end well: the directory is renamed into place, and
  the writer that finds it there removes its own files.  Returns the
  directory of the entry.  Raises OSError when the cache cannot be written.
  '''
  if cache_root is None:
    cache_root = root()
  directory = entry_dir(digest, key, cache_root)
  parent = os.path.dirname(directory)
  os.makedirs(parent, exist_ok=True)
  tmpdir = tempfile.mkdtemp(dir=parent, prefix='.%s-' % key[:8], suffix='.tmp')
  try:
    for path in files:
      _place(
          path, os.path.join(tmpdir, os.path.basename(path))
        , link=path.endswith(LINK_SUFFIXES)
        )
    os.chmod(tmpdir, 0o777 & ~_umask())
    if os.path.isdir(directory):
      # Replace the entry: move the old one away, then rename ours in.  A
      # second writer may do the same in between; then ours is the one
      # moved away, and the other's content, of the same key, stays.
      old = tempfile.mkdtemp(dir=parent, prefix='.%s-' % key[:8], suffix='.old')
      os.rmdir(old)
      try:
        os.rename(directory, old)
      except FileNotFoundError:
        pass
      else:
        shutil.rmtree(old, ignore_errors=True)
    try:
      os.rename(tmpdir, directory)
    except OSError as exc:
      if not os.path.isdir(directory):
        raise
      # The other writer won; its entry has the same key.
      logger.debug('The product cache entry %r was stored by another process (%s)', directory, exc)
      shutil.rmtree(tmpdir, ignore_errors=True)
  except BaseException:
    shutil.rmtree(tmpdir, ignore_errors=True)
    raise
  counts['stored'] += 1
  return directory

def _umask():
  mask = os.umask(0)
  os.umask(mask)
  return mask

def restore(digest, key, directory, names, cache_root=None):
  '''
  Places the files ``names`` of the entry under ``digest`` and ``key`` into
  ``directory``, in that order, each newer than the one before it and all
  newer than any file in the directory with the same stem and another
  suffix, so the last one is the newest file of its module.  Returns the
  paths placed, by name, or None when the entry is missing.  Raises OSError
  when a file cannot be placed.
  '''
  found = lookup(digest, key, names, cache_root)
  if found is None:
    return None
  placed = {}
  for name in names:
    _place(found[name], os.path.join(directory, name), link=name.endswith(LINK_SUFFIXES))
    placed[name] = os.path.join(directory, name)
  _order(directory, [placed[name] for name in names])
  counts['restored'] += 1
  return placed

def _order(directory, files):
  '''
  Sets the modification times of ``files``, in order, later than now and
  than every other file of the directory that shares a stem with the first
  of them (the JSON and the ICurry of the module), one millisecond apart.
  '''
  stem = os.path.basename(files[0]).split('.')[0]
  latest = time.time_ns()
  for name in os.listdir(directory):
    if name.split('.')[0] == stem:
      try:
        latest = max(latest, os.stat(os.path.join(directory, name)).st_mtime_ns)
      except OSError:
        pass
  for path in files:
    latest += 1000000
    os.utime(path, ns=(latest, latest))

def prune(keep, cache_root=None, max_age=3600):
  '''
  Removes from the cache the digest directories whose name is not in
  ``keep`` (the digests of the runtime at hand: ``Cpp2So.accepted_digests``
  of the C++ backend), and the temporary directories of a store that was
  interrupted (``.<key>-XXXX.tmp`` and ``.old``) older than ``max_age``
  seconds.  Returns the pair of the counts: digest directories removed,
  temporary directories removed.  Nothing when the cache is off, when the
  root does not exist, or when ``keep`` is empty: a runtime without a
  digest (no headers) knows nothing of the entries, and none goes.  A
  directory that cannot be removed is left and logged.
  '''
  if cache_root is None:
    cache_root = root()
  if cache_root is None or not os.path.isdir(cache_root):
    return 0, 0
  keep = set(keep) - {None}
  if not keep:
    return 0, 0
  digests = temporaries = 0
  now = time.time()
  for name in os.listdir(cache_root):
    path = os.path.join(cache_root, name)
    if not os.path.isdir(path) or name.startswith('.'):
      continue
    if name in keep:
      for entry in os.listdir(path):
        subpath = os.path.join(path, entry)
        if entry.startswith('.') and entry.endswith(('.tmp', '.old')) \
            and os.path.isdir(subpath):
          try:
            if now - os.stat(subpath).st_mtime < max_age:
              continue
            shutil.rmtree(subpath)
          except OSError as exc:
            logger.warning('cannot remove %r from the product cache (%s)', subpath, exc)
          else:
            temporaries += 1
      continue
    try:
      shutil.rmtree(path)
    except OSError as exc:
      logger.warning('cannot remove %r from the product cache (%s)', path, exc)
    else:
      digests += 1
  return digests, temporaries
