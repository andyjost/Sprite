'''
F06: acceptance of the recommended Python API.

Trace: alt.py and alt.{cxx,py}.out.2; line numbers include the
recorded command header when present. Each row names its flip lane.
  test_finite_prefixes: alt.py 16-17; output 1-2; lane 3.
  test_whole_primes_demands_normal_form: alt.py 12-15 (primes mode); output 17-18; lane 3.
  test_whole_fibs_beyond_the_word: alt.py 18; output 3; lane 1 (amended 2026-10-25: Int unbounded).
  test_close_before_demand: alt.py 19-21; output 4-5; lane 3.
  test_large_finite_list: alt.py 23-25; output 6-8; lane 3.
  test_term_survives_evaluation: alt.py 27-30; output 9-11; lane 4.
  test_term_inspection: alt.py 31-33; output 12-14; lane 4.
  test_stream_ten_primes: alt.py A25; appendix 6361-6386; output decision (e); lane 7.

Left out: Only the timing measurements in harness lines 7-10. The primes mode at 12-15
is run in a child with a timeout, as in the recorded output; its readiness line proves
the child reached the demand.

Departures and rules: Decision (e), Appendix A 6361-6386 adds the A25 stream prefix. The
Primes fixture is copied unchanged from the A25 oracle module; the Sprite.Stream
implementation belongs to lane 7, not this fixture set.

Lanes refer to the Python API implementation plan. Tests import curry,
the package. Missing proposed names are only used inside test methods.
'''
import cytest # from ./lib; must be first
import curry
import unittest
import os
import itertools

FLOW_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'curry', 'flows')


def setUpModule():
  curry.path.insert(0, FLOW_PATH)


class TestFlowF06(cytest.TestCase):

  def setUp(self):
    if FLOW_PATH not in curry.path:
      curry.path.insert(0, FLOW_PATH)

  def test_finite_prefixes(self):
    P = curry.import_('Prelude'); L = curry.import_('inflists')
    self.assertEqual(curry.eval(P.take(10, L.primes)).one(), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])
    self.assertEqual(curry.eval(P.take(8, L.fibs)).one(), [1, 1, 2, 3, 5, 8, 13, 21])

  def test_whole_fibs_beyond_the_word(self):
    # Amended 2026-10-25: Int is unbounded since the big integers, so the
    # whole list never overflows; the row pins the hundredth number, past
    # the machine word, from the same list.
    P = curry.import_('Prelude'); L = curry.import_('inflists')
    self.assertEqual(curry.eval(P.take(100, L.fibs)).one()[-1], 354224848179261915075)

  def test_close_before_demand(self):
    L = curry.import_('inflists'); r = curry.eval(L.primes)
    self.assertIsNone(r.close())
    self.assertEqual(list(r), [])

  @cytest.skipIfGcStress('a live list of 100,000 cells is marked at every step')
  def test_large_finite_list(self):
    P = curry.import_('Prelude')
    self.assertEqual(len(curry.eval(P.enumFromTo(1, 100000)).one()), 100000)
    self.assertEqual(curry.eval(P.head(P.enumFromTo(1, 100000))).one(), 1)
    self.assertEqual(curry.eval(P.enumFromTo(1, 100000)).one()[:3], [1, 2, 3])

  def test_term_survives_evaluation(self):
    P = curry.import_('Prelude'); L = curry.import_('inflists'); t = P.take(3, L.fibs)
    self.assertEqual((str(t), curry.typeof(t), repr(t)),
        ('take 3 fibs', 'Num a => [a]', '<Term take 3 fibs :: Num a => [a]>'))
    self.assertEqual(curry.eval(t).one(), [1, 1, 2])
    self.assertEqual(str(t), 'take 3 fibs')
    self.assertEqual((curry.typeof(L.fibs), curry.typeof(L.goal1)), ('Num a => [a]', '[Int]'))

  def test_term_inspection(self):
    P = curry.import_('Prelude'); L = curry.import_('inflists'); t = P.take(3, L.fibs)
    with self.assertRaises(TypeError):
      bool(t)
    with self.assertRaises(TypeError):
      t[0]
    self.assertEqual(t.symbol.name, 'take')
    self.assertEqual([str(a) for a in t.args], ['3', 'fibs'])

  def test_stream_ten_primes(self):
    stream = curry.stream
    M = curry.import_('Primes')
    r = stream(M.primesOut)
    self.addCleanup(r.close)
    self.assertIsInstance(r, curry.Stream)
    self.assertEqual(list(itertools.islice(r, 10)), [2, 3, 5, 7, 11, 13, 17, 19, 23, 29])

  def test_whole_primes_demands_normal_form(self):
    code = """
import curry
curry.path.insert(0, %r)
L = curry.import_('inflists')
r = curry.eval(L.primes)
print('demand', flush=True)
next(r)
""" % FLOW_PATH
    proc = cytest.run_in_subprocess(code, timeout=10, address_space=2 * 1024**3)
    self.assertEqual(proc.returncode, cytest.TIMEOUT_STATUS, proc.stderr)
    self.assertEqual(proc.stdout, 'demand\n')


if __name__ == '__main__':
  unittest.main()
