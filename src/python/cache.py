'''
Implements a cache for Curry-to-ICurry and JSON-to-Python conversions.

This cache supplements the filesystem caching in .curry files so that
interactive statements can also be cached.  This exists because the conversions
can be extremely slow depending on the Curry system used and its configuration.

Caching can be disabled when installing Sprite, or by setting SPRITE_CACHE_FILE
to the empty string.  The default cache file can be configured at build time.

Environment Variables:
----------------------

    SPRITE_CACHE_FILE
      Specifies the cache file.  Setting this to the empty string disables
      caching.

    SPRITE_CACHE_UPDATE
      Specifies a glob or regex pattern.  Matching files are considered
      out-of-date by the cache, so are updated.  The pattern is considered a
      regex if it begins and ends with slashes.

'''

from . import config
from .utility import filesys
import cPickle as pickle, cStringIO, glob, hashlib, logging, os, re

logger = logging.getLogger(__name__)

try:
  import sqlite3
except ImportError:
  sqlite3 = None
  logger.warn("Cannot import sqlite3.  Caching is disabled")

def enabled():
  return filename() is not None and sqlite3 is not None

def filename(cache=[]):
  '''Returns the name of the cache file or None.'''
  if not cache:
    filename = os.environ.get('SPRITE_CACHE_FILE', None)
    if filename == '':
      logger.info(
          'Caching is disabled because SPRITE_CACHE_FILE is set to the '
          'empty string'
        )
      cache.append(None)
    else:
      default = config.default_sprite_cache_file()
      if filename is None and not default:
        logger.info(
            'Caching is disabled because no default cache file was specified'
          )
        cache.append(None)
      else:
        if filename is None:
          filename = default.format(**os.environ)
          cachedir = os.path.dirname(filename)
          filesys.getdir(cachedir)
        logger.info('Using cache file %s', filename)
        cache.append(filename)
  assert len(cache) == 1
  return cache[0]

def must_force_update(filename, cache=[]):
  if not cache:
    pattern = os.environ.get('SPRITE_CACHE_UPDATE', None)
    if pattern is None or pattern == '':
      cache.append(lambda s: False)
    elif pattern.startswith('/') and pattern.endswith('/'):
      logger.info('Using regex %r to force-update cache files' % pattern)
      pattern = re.compile(pattern[1:-1])
      matcher = lambda s: bool(re.match(pattern, s))
      cache.append(matcher)
    else:
      logger.info('Using glob %r to force-update cache files' % pattern)
      matcher = lambda s: bool(glob.fnmatch.fnmatch(s, pattern))
      cache.append(matcher)
  assert len(cache) == 1
  matcher = cache[0]
  return matcher(filename)

def _getdb(cache=[]):
  '''
  Returns an sqlite3.Connection to the cache file, or None.
  '''
  if not cache:
    if not enabled():
      cache.append(None)
    else:
      db = sqlite3.connect(filename())
      cache.append(db)
  assert len(cache) == 1
  return cache[0]


class Curry2ICurryCache(object):
  '''Coordinates caching for the Curry -> ICurry conversion.'''

  class Slot(object):
    '''
    Clients create an instance with a pair of file names indicating the input
    and output files.  The output file should be created or updated from the
    input.  If the conversion is cached, it will be written to the second file
    and this object will evaluate to True.  Otherwise, the contents of the
    second file should be generated by other means, and, afterwards, ``update``
    should be called to tell the cache to read that file and update its entry.
    '''
    def __init__(self, file_in, file_out):
      '''
      Gets the table storing file conversions for the current value of
      CURRYPATH.  If the entry exists in the cache, then the cached result is
      written to file_out and this object evaluates to True, otherwise False.
      '''
      self.file_in = file_in
      self.db = _getdb()
      self.found = False
      self.file_out = file_out
      if self.db:
        self.tablename = 'file2file %s' % os.environ['CURRYPATH']
        self.cur = self.db.cursor()
        self.cur.execute(
            'CREATE TABLE IF NOT EXISTS [%s](key TEXT PRIMARY KEY, value TEXT)'
          % self.tablename
          )
        self.db.commit()
        # The same Curry file contents can produce a slightly different JSON
        # output because the file name is embedded into JSON as the module name.
        modulename = os.path.splitext(os.path.basename(file_out))[0]
        hasher = hashlib.sha1()
        # The name of the subdirectory under .curry should uniquely identify the
        # Curry library version.
        hasher.update(config.intermediate_subdir())
        hasher.update('#')
        hasher.update(modulename)
        hasher.update('#')
        hasher.update(open(self.file_in).read())
        self.key = hasher.hexdigest()
        self.cur.execute(
            'SELECT value FROM [%s] WHERE key=?' % self.tablename, (self.key,)
          )
        result = self.cur.fetchone()
        if result:
          dirname = os.path.dirname(file_out)
          if not os.path.exists(dirname):
            os.makedirs(dirname)
          with open(file_out, 'w') as out:
            assert isinstance(result, tuple) and len(result) == 1
            out.write(result[0].encode('utf-8'))
          self.found = True

    def __nonzero__(self):
      return self.found

    def update(self):
      '''Updates the cache.'''
      assert not self.found
      if self.db:
        text = open(self.file_out).read()
        self.cur.execute(
            'INSERT INTO [%s](key, value) VALUES(?, ?)' % self.tablename
          , (self.key, text)
          )
        self.db.commit()


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
              self.icur = pickle.load(cStringIO.StringIO(buf))

    def __nonzero__(self):
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

