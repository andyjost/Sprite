import cytest # from ./lib; must be first
from cytest.logging import capture_log
from import_blocker import with_import_blocked
import importlib

class TestPrelude(cytest.TestCase):
  def test_nosqlite3(self):
    '''Checks the warning issued when sqlite3 is not available.'''
    import curry.cache
    @with_import_blocked('sqlite3')
    def check():
      with capture_log('curry.cache') as log:
        importlib.reload(curry.cache)
      log.checkMessages(self, warning='Cannot import sqlite3.  Caching is disabled')
      return True
    self.assertTrue(check())
    importlib.reload(curry.cache)


