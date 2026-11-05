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
C++ backend): the runtime headers the generated code includes, the flags of
the flavor and of the collector, so an entry serves one runtime.  The key
is a digest of the facts that decide the generated code and the object (see
``product_key``): the
module's name and its own texts (its Curry source, its ICurry file and its
image, each one that exists; image summaries shape generated code,
and a new image from the same source, after a change to the ICurry reader or
to a pinned ICurry file, must miss), the sources of the modules it imports,
and the facts the backend names (the format of the generated code, the
sources of the code generator, the flags of the optimizer and the route
from Curry to ICurry; see ``Cpp2So.product_facts`` of the C++ backend for
the list and the reasons).  No part of the key names a tree, and the
products name no path (the objects name their imports by SONAME and the
record of a module names its source relative to the installation or to
the object, since format 13 of the generated code), so an entry serves
every tree of one runtime: the same tree after its products were removed
or after an edit and its revert, and a second worktree, which compiles
nothing the first compiled.  The names of the files in an entry are the
names of the products beside the source.  The stamp stored in an entry is
the one the compile wrote; a restore writes a stamp of its own for the
installation that restores.

Concurrency.  Two processes may store the same key at once: a store writes
its files into a temporary directory beside the entry and renames the
directory into place, so an entry is whole or absent; the second writer
finds the entry and removes its own files.  A restore places a file through
a temporary name in the product directory and a rename, so a reader never
sees a partial file.  The shared object is hard-linked, in both directions,
when the cache and the product directory lie on one file system (the linker
and the compile step write a new file, never into the old one), else
copied; the generated C++ and the stamp are copied. Published cache entries
are immutable. Store, restore and prune share an advisory lock beside the
cache root and a thread-owned lock in this process. Lookup is a snapshot;
restore rechecks it while holding that lock, so pruning cannot unpin its
source files during placement.

Restoration leaves cached modification times unchanged. The C++ plan
selects by pipeline order after validating source,
route and budget receipts (``_findcurry.currentfile``). Images are derived
separately from their own content receipts.

Growth.  Nothing in the toolchain removes an entry: each change to a
runtime header the generated code includes, to the compiler or to the flags
starts a new digest directory, and the old one stays.  ``prune`` removes
the digest directories other than the ones given, and the temporary
directories of a store that
was interrupted; the test runner calls it on its own cache after the
prepare pass (tests/README, section 10).  The directory may be deleted at
any time.
'''

from .. import cache, config
from . import _productlock
from ..utility import filesys
import functools, hashlib, json, logging, os, shutil, tempfile, time, threading, uuid

logger = logging.getLogger(__name__)

__all__ = [
    'KEY_FORMAT', 'chain_digest', 'counts', 'enabled', 'entry_dir', 'excluded'
  , 'import_closure', 'lookup', 'product_key', 'prune', 'reset_counts'
  , 'restore', 'root', 'store'
  ]

# The format of the key.  Raise it when the layout of an entry or the parts
# of the key change; the entries of the old format are then never found.
# Format 4 replaces the module JSON in the chain with its image.
# Format 3 dropped the real paths of the installation and of the source
# directory from the facts (the products name no path since format 13 of
# the generated code), so two trees share an entry.
KEY_FORMAT = 5

MANIFEST = 'manifest.json'

def _receipt(path):
  with open(path, 'rb') as stream:
    data = stream.read()
  return [len(data), hashlib.sha256(data).hexdigest()]

# The suffixes of the files a store and a restore may hard-link.  The others
# are copied: the emitter writes a generated file in place, and a link would
# carry the next generation into the entry.
LINK_SUFFIXES = (config.module_object_suffix(),)

# The counts of this process: the products restored from the cache and the
# products stored in it.  sprite-make reports them.
counts = {'restored': 0, 'stored': 0}
_counts_lock = threading.Lock()

def reset_counts():
  with _counts_lock:
    counts.update(restored=0, stored=0)

def root():
  '''The root directory of the cache, or None when the cache is off.'''
  return config.product_cache_dir()

def enabled():
  '''Tells whether the cache is on (SPRITE_PRODUCT_CACHE is not the empty string).'''
  return root() is not None

def _module_texts(curryfile):
  '''
  The module's own digests, as pairs of a label and a digest: its Curry
  source, its ICurry file and its image, each one that exists, in that
  order. Empty when none of them exists. Images carry optimizer summaries,
  so an image written again from the same source by another
  ICurry reader, or from a pinned ICurry file that was replaced, changes
  the key; the source alone would not see it.
  '''
  from . import _filenames, _findcurry
  generation = _findcurry.generation_for_source(curryfile)
  if generation is None:
    candidates = [('curry', curryfile), ('icy', _filenames.icurryfilename(curryfile)),
                  ('image', _filenames.replacesuffix(curryfile, '.img'))]
  else:
    values = [('curry', generation.source_info.digest if generation.source_info else None),
              ('icy', generation.product_digest('.icy')),
              ('image', generation.product_digest('image'))]
    return [(label, value) for label, value in values if value is not None]
  texts = []
  for label, filename in candidates:
    if filename is None:
      continue
    try:
      with open(filename, 'rb') as stream:
        texts.append((label, hashlib.sha256(stream.read()).hexdigest()))
    except FileNotFoundError:
      continue
  return texts

def _imports(curryfile):
  '''
  The names of the modules the module of ``curryfile`` imports: a scan of
  the source when it exists (``cache.SourceInfo``), else the imports of the
  image beside the products; nothing when neither exists.
  '''
  from . import _filenames, _loadcurry, _findcurry
  generation = _findcurry.generation_for_source(curryfile)
  if generation is not None:
    return [name for name, _ in generation.imports]
  if os.path.isfile(curryfile):
    return cache._sourceinfo(curryfile).imports
  imagefile = _filenames.replacesuffix(curryfile, '.img')
  if os.path.isfile(imagefile):
    try:
      from ..backends.cxx import image
      return list(image.read(imagefile)['imports'])
    except (OSError, ValueError):
      return []
  icyfile = _filenames.icurryfilename(curryfile)
  if os.path.isfile(icyfile):
    return list(_loadcurry.loadicurry(icyfile).imports)
  return []

def import_closure(curryfile, currypath=()):
  '''
  The modules that the module of ``curryfile`` imports, transitively, as
  Curry source files in the Curry path and in the library of the
  installation, by name: ``cache.import_closure`` for a module that may
  lack a source (its imports then come from its image).  The Prelude is
  implicit.  A module without a source in either place is left out.
  '''
  curryfile = os.path.abspath(curryfile)
  from . import _frontend
  searchpaths = _frontend.searchdirs(curryfile, currypath)
  closure = {}
  pending = ['Prelude'] + list(_imports(curryfile))
  seen = set()
  while pending:
    name = pending.pop()
    if name in seen:
      continue
    seen.add(name)
    from ._findcurry import loaded_generation
    generation = loaded_generation(name)
    if generation is not None:
      info = generation.source_info
      if info is None:
        from ..backends.cxx.image import generation_digest
        info = cache.SourceInfo(generation.object or generation.image, b'')
        info.digest = generation_digest(generation)
      closure[name] = info
      pending.extend(dep for dep, _ in generation.imports)
      continue
    relpath = name.replace('.', os.sep) + '.curry'
    from ._findcurry import module_path
    for found in filesys.findfiles(module_path(name, searchpaths), relpath):
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
  ``_module_texts``: the source, the ICurry file and the image, each one
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
    hasher.update(text.encode('ascii'))
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
  try:
    with open(os.path.join(directory, MANIFEST), encoding='ascii') as stream:
      manifest = json.load(stream)
    if manifest['version'] != 1:
      return None
    for name in names:
      if manifest['files'][name] != _receipt(os.path.join(directory, name)):
        return None
  except (OSError, ValueError, KeyError, TypeError):
    return None
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

def _place(source, target, link, publish=False):
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
      shutil.copy2(source, tmp)
    if publish and (target.endswith(config.module_object_suffix()) or
        source.endswith(config.module_object_suffix())):
      from ..backends.cxx import curryrtbindings
      try:
        curryrtbindings.publish_object(tmp, target)
      except RuntimeError as error:
        raise OSError(str(error)) from error
    else:
      os.replace(tmp, target)

def _cache_locked(function):
  @functools.wraps(function)
  def call(*args, **kwds):
    import inspect
    bound = inspect.signature(function).bind(*args, **kwds)
    cache_root = bound.arguments.get('cache_root') or root()
    if cache_root is None:
      return function(*args, **kwds)
    # No imports through an interpreter in this region.
    with _productlock.locked(cache_root.rstrip(os.sep) + '.py'):
      return function(*args, **kwds)
  return call

@_cache_locked
def store(digest, key, files, cache_root=None):
  '''
  Stores ``files`` (paths; their base names name them in the entry) under
  ``digest`` and ``key``.  A published entry is immutable; the first producer wins.  Two writers of
  one key at once both end well: the directory is renamed into place, and
  the writer that finds it there removes its own files.  Returns the
  directory of the entry.  Raises OSError when the cache cannot be written.
  '''
  if cache_root is None:
    cache_root = root()
  directory = entry_dir(digest, key, cache_root)
  parent = os.path.dirname(directory)
  os.makedirs(parent, exist_ok=True)
  tmpdir = os.path.join(parent, '.%s-%s.tmp' % (key[:8], uuid.uuid4().hex))
  os.mkdir(tmpdir, 0o777)
  try:
    for path in files:
      from ._findcurry import verify_loaded_product
      verify_loaded_product(path)
      _place(
          path, os.path.join(tmpdir, os.path.basename(path))
        , link=path.endswith(LINK_SUFFIXES)
        )
    manifest = dict(version=1, files={name: _receipt(os.path.join(tmpdir, name))
        for name in os.listdir(tmpdir)})
    cache.write_file(os.path.join(tmpdir, MANIFEST), json.dumps(manifest, sort_keys=True))
    if os.path.isdir(directory) and lookup(digest, key,
        list(manifest['files']), cache_root) is None:
      shutil.rmtree(directory)
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
  with _counts_lock:
    counts['stored'] += 1
  return directory

@_cache_locked
def restore(digest, key, directory, names, cache_root=None):
  '''
  Places the files ``names`` of the entry under ``digest`` and ``key`` into
  ``directory``, in pipeline order, without changing cached timestamps. Returns the
  paths placed, by name, or None when the entry is missing.  Raises OSError
  when a file cannot be placed.
  '''
  cache_root = cache_root or root()
  if cache_root is None:
    return None
  entry = entry_dir(digest, key, cache_root)
  for name in names:
    from ._findcurry import verify_loaded_product
    verify_loaded_product(os.path.join(directory, name))
    candidate = os.path.join(entry, name)
    if os.path.isfile(candidate):
      verify_loaded_product(candidate, identity=os.path.join(directory, name))
  found = lookup(digest, key, names, cache_root)
  if found is None:
    return None
  placed = {}
  for name in names:
    if name.endswith(config.module_object_suffix()):
      try:
        os.unlink(os.path.join(directory, name) + '.abi')
      except FileNotFoundError:
        pass
  for name in names:
    _place(found[name], os.path.join(directory, name),
           link=name.endswith(LINK_SUFFIXES), publish=True)
    placed[name] = os.path.join(directory, name)
  with _counts_lock:
    counts['restored'] += 1
  return placed

@_cache_locked
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
