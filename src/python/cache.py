'''
Implements a cache for Curry-to-ICurry and JSON-to-Python conversions.

This cache supplements the filesystem caching in .curry files so that
interactive statements can also be cached.  This exists because the conversions
can be extremely slow depending on the Curry system used and its configuration.
'''

from . import config
from .utility import filesys
import cPickle as pickle
import cStringIO
import hashlib
import logging
import os

logger = logging.getLogger(__name__)

_cachefile_ = 'uninit' # 'uninit', None (disabled), or sqlite3.Connection.
filename = None

try:
  import sqlite3
except ImportError:
  logger.warn("Cannot import sqlite3.  Caching is disabled")
  _cachefile_ = None

def _getdb():
  '''
  Returns an sqlite3.Connection object tied to the cache file, or None.

  The cache file stores the results of certain slow conversion steps in the
  build toolchain.  Caching can be disabled when installing Sprite, or by
  setting SPRITE_CACHE_FILE to the empty string.  The default cache file can be
  found in Make.config.
  '''
  global _cachefile_
  if _cachefile_ == 'uninit':
    name = os.environ.get('SPRITE_CACHE_FILE', None)
    if name == '':
      if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            'Caching is disabled because SPRITE_CACHE_FILE is set to the empty string'
          )
      _cachefile_ = None
      return
    elif name is None:
      default = config.default_sprite_cache_file()
      if default:
        name = default.format(**os.environ)
        cachedir = os.path.dirname(name)
        filesys.getdir(cachedir)
    _cachefile_ = sqlite3.connect(name)
    global filename
    filename = name
    if logger.isEnabledFor(logging.INFO):
      logger.info('Using cache file %s', name)
  return _cachefile_


class Curry2ICurryCache(object):
  '''
  Coordinates caching for the Curry -> ICurry conversion.

  Clients create an instance with a pair of file names indicating the input and
  output files.  The output file should be created or updated from the input.
  If the conversion is cached, it will be written to the second file and this
  object will evaluate to True.  Otherwise, the contents of the second file
  should be generated by other means, and, afterwards, ``update`` should be
  called to tell the cache to read that file and update its entry.
  '''
  def __init__(self, file_in, file_out):
    '''
    Gets the table storing file conversions for the current value of CURRYPATH.
    If the entry exists in the cache, then the cached result is written to
    file_out and this object evaluates to True, otherwise False.
    '''
    self.file_in = file_in
    self.db = _getdb()
    self.found = False
    self.file_out = file_out
    if self.db:
      self.tablename = 'file2file %s' % os.environ['CURRYPATH']
      self.cur = self.db.cursor()
      self.cur.execute(
          '''
          CREATE TABLE IF NOT EXISTS [%s](key TEXT PRIMARY KEY, value TEXT)
          ''' % self.tablename
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
          '''SELECT value FROM [%s] WHERE key=?''' % self.tablename, (self.key,)
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
          '''INSERT INTO [%s](key, value) VALUES(?, ?)''' % self.tablename
        , (self.key, text)
        )
      self.db.commit()

class ParsedJsonCache(object):
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
          self.icur = pickle.load(cStringIO.StringIO(buf))

  def __nonzero__(self):
    return self.icur is not None

  def update(self, icur):
    assert self.icur is None
    if self.db:
      pickled = pickle.dumps(icur, protocol=-1)
      st = os.stat(self.jsonfile)
      self.cur.execute(
          '''INSERT OR REPLACE INTO parsedjson(jsonfile, timestamp, pickled) VALUES(?, ?, ?)'''
        , (self.jsonfile, int(st.st_ctime), sqlite3.Binary(pickled))
        )
      self.db.commit()

