import cytest # from ./lib; must be first
import curry

class ICurryTestCase(cytest.TestCase):
  '''Tests for the API found in module ``curry``.'''

  def test_reload(self):
    curry.reload()
    curry.path.insert(0, 'data/curry/kiel')
    self.assertIn('data/curry/kiel', curry.path)
    curry.import_('rev')
    self.assertIn('rev', curry.modules)

    curry.reload()
    self.assertNotIn('data/curry/kiel', curry.path)
    self.assertNotIn('rev', curry.modules)


