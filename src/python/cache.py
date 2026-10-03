'''
Implements a cache for Curry-to-ICurry and JSON-to-Python conversions.

This cache supplements the filesystem caching in .curry files so that
interactive statements can also be cached.  This exists because the conversions
can be extremely slow depending on the Curry system used and its configuration.

The Curry-to-ICurry cache is keyed by content, not by file name: an entry is
found again from any directory and, for an anonymous module, under any module
name.  An error the front end reports about the program is cached as well.
See ``Curry2ICurryCache`` and ``icurry_cache_key``.

Environment Variables:
----------------------

    SPRITE_CACHE_FILE
      Specifies the cache file.  A file name turns the Curry-to-ICurry cache
      on.  The empty string disables caching.  When the variable is not set,
      the settings of the installation apply (see Make.config).

    SPRITE_CACHE_UPDATE
      Specifies a glob or regex pattern.  Matching files are considered
      out-of-date by the cache, so are updated.  The pattern is considered a
      regex if it begins and ends with slashes.  For the Curry-to-ICurry cache
      the pattern is compared with the name of the Curry source file.

'''

from . import config
from .utility import filesys, strings
import glob, hashlib, logging, os, re, tempfile, time
import pickle

logger = logging.getLogger(__name__)

__all__ = [
    'enabled', 'filename', 'icurry_cache_enabled', 'icurry_cache_key'
  , 'import_closure', 'is_program_error', 'rename_in_message', 'rename_module'
  , 'reset', 'Curry2ICurryCache', 'ParsedJsonCache'
  ]

try:
  import sqlite3
except ImportError:
  sqlite3 = None
  logger.warning("Cannot import sqlite3.  Caching is disabled")

# The state of this module for one process: the cache file name, the update
# matcher, the database connection, and the digest of each route from Curry
# to ICurry.
# ``reset`` clears it, so a test can change the environment.
_memo = {}

def reset():
  '''
  Forgets the cache file, the update pattern, the database connection, and
  the digests of the routes.  The next use reads the environment again.
  '''
  db = _memo.get('db')
  if db is not None:
    db.close()
  _memo.clear()

def enabled():
  '''Whether a cache file is in use.'''
  return sqlite3 is not None and filename() is not None

def filename():
  '''Returns the name of the cache file or None.'''
  if 'filename' not in _memo:
    name = os.environ.get('SPRITE_CACHE_FILE', None)
    if name == '':
      logger.info(
          'Caching is disabled because SPRITE_CACHE_FILE is set to the '
          'empty string'
        )
      name = None
    elif name is None:
      default = config.default_sprite_cache_file()
      if default:
        name = default.format(**os.environ)
      else:
        logger.info(
            'Caching is disabled because no default cache file was specified'
          )
    if name is not None:
      name = os.path.abspath(name)
      logger.info('Using cache file %s', name)
    _memo['filename'] = name
  return _memo['filename']

def icurry_cache_enabled():
  '''
  Whether the Curry-to-ICurry cache is on.  A file named by SPRITE_CACHE_FILE
  turns it on.  The empty string turns it off.  Otherwise the installation
  decides (ENABLE_ICURRY_CACHE in Make.config).
  '''
  if sqlite3 is None:
    return False
  name = os.environ.get('SPRITE_CACHE_FILE', None)
  if name is None:
    return bool(config.enable_icurry_cache()) and filename() is not None
  return bool(name)

def must_force_update(filename):
  '''Tells whether SPRITE_CACHE_UPDATE selects ``filename`` for an update.'''
  if 'matcher' not in _memo:
    pattern = os.environ.get('SPRITE_CACHE_UPDATE', None)
    if pattern is None or pattern == '':
      matcher = lambda s: False
    elif pattern.startswith('/') and pattern.endswith('/'):
      logger.info('Using regex %r to force-update cache files' % pattern)
      regex = re.compile(pattern[1:-1])
      matcher = lambda s: bool(re.search(regex, s))
    else:
      logger.info('Using glob %r to force-update cache files' % pattern)
      matcher = lambda s: bool(glob.fnmatch.fnmatch(s, pattern))
    _memo['matcher'] = matcher
  return _memo['matcher'](filename)

def _getdb():
  '''
  Returns an sqlite3.Connection to the cache file, or None.  The directory of
  the file is created.  A file that cannot be opened disables the cache for
  this process, with a warning.
  '''
  if 'db' not in _memo:
    db = None
    if enabled():
      name = filename()
      try:
        os.makedirs(os.path.dirname(name), exist_ok=True)
        db = sqlite3.connect(name, timeout=30)
      except (OSError, sqlite3.Error) as err:
        logger.warning('cannot open the cache file %s: %s', name, err)
        db = None
    _memo['db'] = db
  return _memo['db']

# ---------------------------------------------------------------------------
# The cache key of the Curry-to-ICurry conversion.

# The format of the key and of the stored text.  Raise it when either changes;
# the entries of the old format are then left alone in their own table.
KEY_FORMAT = 2

# An import declaration.  The scan is lenient: a match inside a comment or a
# string adds a module to the closure, which can only make the key more
# sensitive.  Every import declaration matches, so no module the Curry front
# end reads is left out.  A module name may begin with a lowercase letter: a
# module compiled from a string (sprite__interactive_N), which curry.compile
# prepends as an import, does.
_IMPORT = re.compile(
    r"\bimport\s+(?:qualified\s+)?([A-Za-z_][\w']*(?:\.[A-Za-z_][\w']*)*)"
  )

class SourceInfo(object):
  '''The digest and the import names of one Curry source file.'''
  def __init__(self, path, data):
    self.path = path
    self.digest = hashlib.sha256(data).hexdigest()
    text = data.decode('utf-8', errors='replace')
    self.imports = list(dict.fromkeys(_IMPORT.findall(text)))

def _sourceinfo(path):
  '''
  Reads ``path`` and returns its ``SourceInfo``.  The file is read every time:
  a digest costs well under a millisecond, and file time stamps are too coarse
  to tell a rewrite of the same size apart.
  '''
  with open(path, 'rb') as stream:
    data = stream.read()
  return SourceInfo(path, data)

# The sources of the built-in translation from FlatCurry to ICurry
# (curry.toolchain.flat2icurry).  They are part of the digest of the
# front-end route: a change to the translation changes the ICurry as a new
# front end would.
PORT_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), 'toolchain', 'flat2icurry'
  )

def _digest_file(hasher, path):
  with open(path, 'rb') as stream:
    hasher.update(stream.read())
  hasher.update(b'\0')

def frontend_digest(tool=None):
  '''
  A digest of the route from Curry to ICurry named by ``tool`` (see
  ``config.curry2icurry_tool``; the configured route by default).  For
  ``icurry`` it covers the name of the route and the content of the
  ``icurry`` program.  For ``frontend`` it covers the name, the content of
  the Curry front end, the front-end flags, and the sources of the built-in
  translation.  So a new front end, new flags, or a change to the translation
  makes a new key, and an entry written by one route is never served to the
  other.  The empty string when the program of the route is missing.
  '''
  if tool is None:
    tool = config.curry2icurry_tool()
  memokey = 'frontend:' + tool
  if memokey not in _memo:
    hasher = hashlib.sha256()
    hasher.update(tool.encode('utf-8') + b'\0')
    try:
      if tool == 'icurry':
        program = config.icurry_tool()
      else:
        program = config.curry_frontend()
      if program is None:
        raise OSError('the %s route is not configured' % tool)
      _digest_file(hasher, os.path.realpath(program))
      if tool == 'frontend':
        hasher.update(config.frontend_flags().encode('utf-8') + b'\0')
        for name in sorted(os.listdir(PORT_DIR)):
          if name.endswith('.py'):
            hasher.update(name.encode('utf-8') + b'\0')
            _digest_file(hasher, os.path.join(PORT_DIR, name))
      digest = hasher.hexdigest()
    except OSError as err:
      logger.debug('cannot read the Curry front end: %s', err)
      digest = ''
    _memo[memokey] = digest
  return _memo[memokey]

def import_closure(curryfile, currypath=()):
  '''
  Finds the modules that ``curryfile`` imports, transitively, as Curry source
  files in the Curry path.  The Prelude is implicit.  A module without a source
  file in the path (a library of the Curry system) is left out.  The directory
  of ``curryfile`` is searched first.

  Returns:
    A dict from module name to ``SourceInfo``.
  '''
  curryfile = os.path.abspath(curryfile)
  searchpaths = [os.path.dirname(curryfile)]
  searchpaths += [os.path.abspath(p) for p in currypath if p]
  closure = {}
  pending = ['Prelude'] + _sourceinfo(curryfile).imports
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
        info = _sourceinfo(found)
        closure[name] = info
        pending.extend(info.imports)
      break
  return closure

def icurry_cache_key(curryfile, currypath=(), options=(), tool=None):
  '''
  The key under which the ICurry of ``curryfile`` is cached.

  The key is a digest of the source text of the module, the source texts of
  the modules it imports (see ``import_closure``), the front-end options, the
  route from Curry to ICurry with its program and flags (see
  ``frontend_digest``), and the intermediate subdirectory, which names the
  version of the Curry library.  The directory of the file is not part of the
  key.
  The module name is part of the key for a named module, because the front
  end writes it into the ICurry.  For an anonymous module (see
  ``config.is_anonymous_modname``) the name is left out, and the cached text
  is renamed on a hit.

  Args:
    curryfile:
        The Curry source file.
    currypath:
        The Curry search path used for the conversion.
    options:
        The front-end options that change its output.
    tool:
        The route from Curry to ICurry, ``frontend`` or ``icurry``.  The
        configured route by default.

  Returns:
    A hex digest.
  '''
  hasher = hashlib.sha256()
  def put(part):
    hasher.update(strings.ensure_binary(part))
    hasher.update(b'\0')
  put('sprite curry2icurry %d' % KEY_FORMAT)
  put(config.intermediate_subdir())
  put(frontend_digest(tool))
  put(' '.join(options))
  modulename = os.path.basename(curryfile)[:-len('.curry')]
  put('' if config.is_anonymous_modname(modulename) else modulename)
  put(_sourceinfo(curryfile).digest)
  for name, info in sorted(import_closure(curryfile, currypath).items()):
    put(name)
    put(info.digest)
  return hasher.hexdigest()

# ---------------------------------------------------------------------------
# The module name in an ICurry text.

# The module name of an ICurry text, from its header: (IProg "name" ...
_IPROG_NAME = re.compile(r'\A\s*\(IProg\s+"([^"]*)"')

# An error the Curry front end reports at a position of the source, such as
# "sprite__interactive_0.curry:2:3 Error:" or, for a span,
# "M.curry:2:8-2:10 Error:".  Only such an error is cached: a failure of the
# environment (a missing tool, an unwritable directory) has no position and
# runs again next time.
_PROGRAM_ERROR = re.compile(
    r'^\s*\S+\.curry:\d+:\d+(?:-\d+:\d+)? Error:', re.MULTILINE
  )

# A missing import has a position, but it is not cached either: whether a
# module exists is a property of the Curry path, and the key sees the path
# only through the source files found in it.  A module that appears later as
# a compiled interface alone would replay the error.
_MISSING_MODULE = re.compile(r'Interface for module \S+ not found')

def is_program_error(stderr):
  '''
  Tells whether the standard error of the front end reports an error of the
  program: an error at a source position, other than a missing import.
  '''
  return stderr is not None \
     and _PROGRAM_ERROR.search(stderr) is not None \
     and _MISSING_MODULE.search(stderr) is None

def rename_in_message(text, old, new):
  '''Renames a module in a message of the front end, word by word.'''
  pattern = re.compile(r'(?<!\w)%s(?!\w)' % re.escape(old))
  return pattern.sub(lambda match: new, text)

def icurry_modulename(text):
  '''The module name an ICurry text declares, or None.'''
  match = _IPROG_NAME.match(text)
  return match.group(1) if match else None

def rename_module(text, old, new):
  '''
  Renames the module of an ICurry text from ``old`` to ``new``.

  The front end writes the module name into the ``IProg`` header, into
  qualified names ``("module","name",n)``, into the module part of a generated
  name such as ``_inst#Prelude.Show#module.T``, and into the name of an
  external function ``"module.f"``.  In every case the name follows a double
  quote or a hash sign, and a double quote or a dot follows it.  A string
  literal of the program cannot match: ICurry spells it as a list of
  characters.

  The caller must make sure that no other module named in the text has
  ``old`` plus a dot as a prefix.  Anonymous modules satisfy this.
  '''
  pattern = re.compile(r'(?<=["#])%s(?=["\.])' % re.escape(old))
  return pattern.sub(lambda match: new, text)

# ---------------------------------------------------------------------------

class Curry2ICurryCache(object):
  '''
  Coordinates caching for the Curry -> ICurry conversion.

  The table ``curry2icurry_<format>`` of the cache file stores one row per key
  (see ``icurry_cache_key``): the module name the front end wrote and the text
  of the ICurry file, or, for a program the front end rejected, the module
  name and the error text.  Counts of the hits and the misses of this process
  are kept in ``stats``; a replayed error counts as a hit.
  '''
  TABLE = 'curry2icurry_%d' % KEY_FORMAT
  stats = {'hit': 0, 'miss': 0}

  class Slot(object):
    '''
    Clients create an instance with a pair of file names indicating the input
    and output files.  The output file should be created or updated from the
    input.  If the conversion is cached, it will be written to the second file
    and this object will evaluate to True.  If a program error is cached, the
    object evaluates to False and ``error`` holds the error text.  Otherwise,
    the contents of the second file should be generated by other means, and,
    afterwards, ``update`` should be called to tell the cache to read that
    file and update its entry, or ``update_error`` with the exception of the
    front end.
    '''
    def __init__(self, file_in, file_out, currypath=(), options=(), tool=None):
      '''
      Looks the conversion up.  If the entry exists in the cache, then the
      cached result is written to file_out and this object evaluates to True,
      otherwise False.

      Args:
        file_in:
            The Curry source file.
        file_out:
            The ICurry file to write.
        currypath:
            The Curry search path of the conversion.
        options:
            The front-end options that change its output.
        tool:
            The route from Curry to ICurry; see ``frontend_digest``.
      '''
      self.file_in = file_in
      self.file_out = file_out
      self.found = False
      self.error = None
      self.key = None
      self.db = _getdb()
      if self.db is None:
        return
      self.modulename = os.path.splitext(os.path.basename(file_out))[0]
      self.anonymous = config.is_anonymous_modname(self.modulename)
      try:
        self.key = icurry_cache_key(file_in, currypath, options, tool)
        self.db.execute(
            'CREATE TABLE IF NOT EXISTS [%s]('
            'key TEXT PRIMARY KEY, name TEXT NOT NULL, text TEXT NOT NULL'
            ', error TEXT, created REAL)' % Curry2ICurryCache.TABLE
          )
        self.db.commit()
        if must_force_update(file_in):
          logger.info('file %s is being forced to update', file_in)
          return
        row = self.db.execute(
            'SELECT name, text, error FROM [%s] WHERE key=?'
                % Curry2ICurryCache.TABLE
          , (self.key,)
          ).fetchone()
      except (OSError, sqlite3.Error) as err:
        logger.warning('cannot read the cache: %s', err)
        return
      if row is None:
        Curry2ICurryCache.stats['miss'] += 1
        logger.info('ICurry cache miss for %s', self.modulename)
        return
      name, text, error = row
      if error is not None:
        if self.anonymous and name != self.modulename:
          error = rename_in_message(error, name, self.modulename)
        self.error = error
        Curry2ICurryCache.stats['hit'] += 1
        logger.info(
            'ICurry cache hit for %s (a program error)', self.modulename
          )
        return
      if self.anonymous:
        if not config.is_anonymous_modname(name):
          logger.warning(
              'ignoring a cache entry of module %r found under the key of %r'
            , name, self.modulename
            )
          return
        if name != self.modulename:
          text = rename_module(text, name, self.modulename)
      elif name.rpartition('.')[2] != self.modulename:
        logger.warning(
            'ignoring a cache entry of module %r found under the key of %r'
          , name, self.modulename
          )
        return
      self._write(text)
      self.found = True
      Curry2ICurryCache.stats['hit'] += 1
      logger.info('ICurry cache hit for %s', self.modulename)

    def __bool__(self):
      return self.found

    def _write(self, text):
      '''Writes the ICurry text to the output file, through a temporary file.'''
      dirname = os.path.dirname(self.file_out)
      os.makedirs(dirname, exist_ok=True)
      fd, tmpname = tempfile.mkstemp(
          dir=dirname, prefix='.icurry-', suffix='.tmp'
        )
      try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
          stream.write(text)
        os.replace(tmpname, self.file_out)
      except BaseException:
        if os.path.exists(tmpname):
          os.unlink(tmpname)
        raise

    def update(self):
      '''Reads the output file and stores it under the key.'''
      assert not self.found
      if self.db is None or self.key is None:
        return
      with open(self.file_out, encoding='utf-8') as stream:
        text = stream.read()
      name = icurry_modulename(text)
      if name is None:
        logger.warning('not caching %s: no module name found', self.file_out)
        return
      self._store(name, text, None)

    def update_error(self, err):
      '''
      Stores the failure of the front end, when ``err`` (the CompileError of
      ``_system.pexec``) reports an error of the program.  Another failure is
      not stored.
      '''
      assert not self.found
      if self.db is None or self.key is None:
        return
      stderr = getattr(err, 'stderr', None)
      if not is_program_error(stderr):
        logger.debug('not caching the failure of %s', self.file_in)
        return
      self._store(self.modulename, '', stderr)

    def _store(self, name, text, error):
      try:
        self.db.execute(
            'INSERT OR REPLACE INTO [%s](key, name, text, error, created) '
            'VALUES(?, ?, ?, ?, ?)' % Curry2ICurryCache.TABLE
          , (self.key, name, text, error, time.time())
          )
        self.db.commit()
      except sqlite3.Error as err:
        logger.warning('cannot update the cache: %s', err)


class ParsedJsonCache(object):
  @staticmethod
  def select(like=None):
    db = _getdb()
    cur = db.cursor()
    cmd = 'SELECT jsonfile, timestamp, LENGTH(pickled) FROM parsedjson'
    if like is None:
      cur.execute(cmd)
    else:
      cmd += ' WHERE jsonfile LIKE ?'
      cur.execute(cmd, (like,))
    return cur.fetchall()

  class Slot(object):
    '''
    Caches the parsing of ICurry-JSON into Python.  The pickled Python
    representation is stored.
    '''
    def __init__(self, jsonfile):
      self.db = _getdb()
      self.icur = None
      self.jsonfile = jsonfile
      if self.db:
        self.cur = self.db.cursor()
        self.cur.execute(
            '''
            CREATE TABLE IF NOT EXISTS parsedjson(
                jsonfile TEXT PRIMARY KEY, timestamp INTEGER, pickled BLOB
              )
            '''
          )
        self.db.commit()
        self.cur.execute(
            '''SELECT timestamp, pickled FROM parsedjson WHERE jsonfile=?'''
          , (self.jsonfile,)
          )
        result = self.cur.fetchone()
        if result:
          ts, buf = result
          st = os.stat(self.jsonfile)
          if int(st.st_ctime) == ts:
            if must_force_update(self.jsonfile):
              logger.info('file %s is being forced to update', self.jsonfile)
            else:
              try:
                self.icur = pickle.loads(bytes(buf))
              except Exception:
                logger.debug('cannot unpickle cached entry for %s; treating as a miss', self.jsonfile)
                self.icur = None

    def __bool__(self):
      return self.icur is not None

    def update(self, icur):
      assert self.icur is None
      if self.db:
        pickled = pickle.dumps(icur, protocol=-1)
        st = os.stat(self.jsonfile)
        self.cur.execute(
            '''
            INSERT OR REPLACE INTO parsedjson(
                jsonfile, timestamp, pickled
              ) VALUES(?, ?, ?)
            '''
          , (self.jsonfile, int(st.st_ctime), sqlite3.Binary(pickled))
          )
        self.db.commit()
