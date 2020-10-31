import cytest # from ./lib; must be first
from import_blocker import with_import_blocked
from cytest.logging import capture_log

class TestPrelude(cytest.TestCase):
  def test_nosqlite3(self):
    '''Checks the warning issued when sqlite3 is not available.'''
    import curry.cache
    @with_import_blocked('sqlite3')
    def check():
      with capture_log('curry.cache') as log:
        reload(curry.cache)
      log.checkMessages(self, warning='Cannot import sqlite3.  Caching is disabled')
      return True
    self.assertTrue(check())
    reload(curry.cache)


