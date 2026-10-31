'''Facade corpus, compared with PAKCS 3.10.0 (base 3.4.0).

PAKCS 3.4.1 has no Control.Search.SetFunctions. Record that refusal and
skip its oracle comparisons. Existing goldens are never rewritten.
'''
import cytest # from ./lib; must be first
from cytest import oracle
from curry import config
from func_community import oracle_source, sprite_results
import curry, pathlib
from curry.utility.readcurry import parse, show

ROOT = pathlib.Path('data/curry')
# PAKCS captures a nullary function-valued choice inside its set; Sprite
# chooses that function outside. These programs also exist in the native
# legacy corpus, whose committed values pin Sprite's weak grouping.
FUNCTION_CHOICES = {'basic03'} | {'basic%02d' % n for n in range(10, 18)}


def elements(text):
  return [show(value) for line in text.splitlines() if line
          for value in parse(line)]


class TestSearchSetFunctions(cytest.TestCase):
  @cytest.with_flags(interpret='off')
  def check(self, source, goals):
    if config.frontend_subdir() == 'pakcs-3.4.1':
      self.skipTest('PAKCS 3.4.1 refuses Control.Search.SetFunctions; '
                    'goldens are from PAKCS 3.10.0')
    # The installed Test.Prop hierarchy loads; the corpus's namesake under
    # community/support is refused since #168.
    curry.path[:0] = [str(source.parent)]
    curry.import_(source.stem)
    with oracle_source(source) as (oracle_module, work):
      for goal in goals:
        with self.subTest(goal=goal):
          golden = source.with_name(source.stem + '.' + goal + '.au-gen')
          if not golden.exists():
            oracle.divine(oracle_module, source.stem + '.' + goal, [work],
                          timeout=60, goldenfile=str(golden), record_errors=True)
          expected = golden.read_text()
          if expected.startswith('!error\n') or 'Evaluation suspended!' in expected:
            self.skipTest('PAKCS 3.10.0 refusal: ' + expected.partition('\n')[2])
          proc, actual = sprite_results(source, goal, timeout=60)
          self.assertEqual(proc.returncode, 0, proc.stderr)
          if source.stem == 'TestSearchSetFunctionsGoals' and goal == 'goal0':
            # Issue #171: one shortest itinerary, including its multiplicity.
            self.assertEqual(len(actual.splitlines()), 1)
            self.assertSameResultMultiset(actual, '[LH469,LH10]')
          if source.parent.name == 'search_setfunctions' and (
              source.stem in FUNCTION_CHOICES or source.stem.startswith('free')):
            native = ROOT / 'setfunctions' / golden.name
            self.assertSameResultMultiset(actual, native.read_text())
            if source.stem in FUNCTION_CHOICES:
              # Keep PAKCS's exact golden; compare the same elements while
              # the native legacy golden pins Sprite's different grouping.
              self.assertCountEqual(elements(actual), elements(expected))
            else:
              # PAKCS 3.10.0 suspends on these outside free arguments. The
              # oracle shell returns no value lines; Sprite narrows outside.
              self.assertEqual(expected.strip(), '')
          else:
            self.assertSameResultMultiset(actual, expected)

  @oracle.require
  def test_old_oracle_refusal(self):
    if config.frontend_subdir() != 'pakcs-3.4.1':
      self.skipTest('refusal is specific to PAKCS 3.4.1')
    source = ROOT / 'search_setfunctions/basic00.curry'
    with oracle_source(source) as (module, work):
      result = oracle.divine(module, 'basic00.main', [work], timeout=30,
                             record_errors=True)
    if isinstance(result, bytes):
      result = result.decode()
    self.assertTrue(result.startswith('!error\n'), result)
    self.assertIn('Control.Search.SetFunctions', result)


programs = [(p, ['main']) for p in sorted((ROOT / 'search_setfunctions').glob('[bf]*.curry'))]
programs += [
    (ROOT / 'community/tutorial/chapter4/AllSubsets.curry', ['main'])
  , (ROOT / 'community/tutorial/chapter4/CSIS.curry', ['main', 'test1'])
  , (ROOT / 'community/tutorial/chapter6/expr.curry', ['main'])
  , (ROOT / 'community/base-3.4.0-test/TestSearchSetFunctionsGoals.curry',
     ['main', 'goal0', 'goal1', 'goal2', 'goal3'])
  ]
for source, goals in programs:
  for goal in goals:
    def test(self, source=source, goal=goal):
      self.check(source, [goal])
    setattr(TestSearchSetFunctions, 'test_' + source.stem + '_' + goal,
            oracle.require(test))
