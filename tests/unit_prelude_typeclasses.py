import cytest
import curry

class TestTypeClassCompare(cytest.TestCase):
  def test_eqInt(self):
    e = curry.compile("1 == 1", mode='expr')
    self.assertEqual(list(curry.eval(e)), [True])
    e = curry.compile("1 == 2", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])

  def test_eqChar(self):
    e = curry.compile("'a' == 'a'", mode='expr')
    self.assertEqual(list(curry.eval(e)), [True])
    e = curry.compile("'a' == 'b'", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])

  def test_eqFloat(self):
    e = curry.compile("1.0 == 1.0", mode='expr')
    self.assertEqual(list(curry.eval(e)), [True])
    e = curry.compile("1.0 == 2.0", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])

  def test_ltEqInt(self):
    e = curry.compile("1 <= 1", mode='expr')
    self.assertEqual(list(curry.eval(e)), [True])
    e = curry.compile("2 == 1", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])
    e = curry.compile("1 == 2", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])

  def test_ltEqChar(self):
    e = curry.compile("'a' == 'a'", mode='expr')
    self.assertEqual(list(curry.eval(e)), [True])
    e = curry.compile("'a' == 'b'", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])

  def test_ltEqFloat(self):
    e = curry.compile("1.0 == 1.0", mode='expr')
    self.assertEqual(list(curry.eval(e)), [True])
    e = curry.compile("1.0 == 2.0", mode='expr')
    self.assertEqual(list(curry.eval(e)), [False])
