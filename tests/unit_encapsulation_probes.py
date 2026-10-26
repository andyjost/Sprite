'''Pin declarative answers, independently in compiled and interpreted code.

Process/compilation failures are checked separately in setUp.
After D45 both mixed-failure orderings require no value, and sharedLookup
requires exactly Short. All three now pass without expectedFailure.
D54 specifies the four former reading goals on both routes.
'''
import cytest # from ./lib; must be first
from func_encapsulation_probes import (
    GOALS, SOURCE, TIMEOUT, VALUES, normalized
  )
from func_community import sprite_results
import json, os, unittest

class ProbeCase(cytest.TestCase):
  def setUp(self):
    super().setUp()
    goal = self._testMethodName[len('test_'):]
    proc, actual = sprite_results(SOURCE, goal, timeout=TIMEOUT,
                                   interpret=self.MODE)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.actual = normalized(actual.splitlines())
    evidence = os.environ.get('SPRITE_PROBES_EVIDENCE')
    if evidence:
      with open(evidence, 'a') as stream:
        stream.write(json.dumps(dict(goal=goal, system=self.MODE,
                                     values=self.actual)) + '\n')

  def check(self, goal):
    self.assertEqual(self.actual, normalized(VALUES[goal]))


class TestCompiled(ProbeCase):
  MODE = 'off'


class TestInterpreted(ProbeCase):
  MODE = 'all'


for cls in (TestCompiled, TestInterpreted):
  for goal in GOALS:
    def test(self, goal=goal):
      self.check(goal)
    setattr(cls, 'test_' + goal, test)


del cls # Do not let unittest discover the last class a second time.


if __name__ == '__main__':
  unittest.main()
