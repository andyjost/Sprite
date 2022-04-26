import cytest
from curry.interpreter import Interpreter
from curry.toolchain import plans
from curry.utility.strings import PY3
import string

REMOVE_CHARS = string.whitespace + '-'
if PY3:
  _MAPPING = {ord(c): None for c in REMOVE_CHARS}
  clean = lambda s: s.translate(_MAPPING)
else:
  clean = lambda s: s.translate(None, REMOVE_CHARS)

class TestPlan(cytest.TestCase):
  '''Tests the compilation plan.'''
  def checkStr(self, plan, expected):
    a = clean(str(plan))
    b = clean(expected)
    try:
      self.assertEqual(a, b)
    except:
      print('\n****** A ******')
      print(plan)
      print('\n****** B ******')
      print(expected)
      raise

  def test_00_empty(self):
    plan = plans.makeplan()
    self.checkStr(plan,
        '''
        Build plan with 0 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               None
        '''
      )

  def test_01_icurry(self):
    plan = plans.makeplan(flags=plans.MAKE_ICURRY)
    self.checkStr(plan,
        '''
        Build plan with 1 step:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 None
        '''
      )

  def test_02_json(self):
    plan = plans.makeplan(flags=plans.MAKE_ICURRY | plans.MAKE_JSON)
    self.checkStr(plan,
        '''
        Build plan with 2 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                None
        '''
      )
    plan = plans.makeplan(flags=plans.MAKE_ICURRY | plans.MAKE_JSON | plans.ZIP_JSON)
    self.checkStr(plan,
        '''
        Build plan with 2 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json.z']              None
        '''
      )

  def test_03_py(self):
    interp = Interpreter(flags={'backend':'py'})
    plan = plans.makeplan(
        interp
      , flags=plans.MAKE_ICURRY | plans.MAKE_JSON | plans.MAKE_TARGET_SOURCE
      )
    self.checkStr(plan,
        '''
        Build plan with 3 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                json2py
            3     ['.py']                  None
        '''
      )
    plan = plans.makeplan(interp, flags=plans.MAKE_ALL)
    self.checkStr(plan,
        '''
        Build plan with 3 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                json2py
            3     ['.py']                  None
        '''
      )
    plan = plans.makeplan(interp, flags=plans.MAKE_ALL | plans.ZIP_JSON)
    self.checkStr(plan,
        '''
        Build plan with 3 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json.z']              json2py
            3     ['.py']                  None
        '''
      )

  def test_04_cxx(self):
    interp = Interpreter(flags={'backend':'cxx'})
    plan = plans.makeplan(
        interp
      , flags=plans.MAKE_ICURRY | plans.MAKE_JSON | plans.MAKE_TARGET_SOURCE
      )
    self.checkStr(plan,
        '''
        Build plan with 3 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                json2cpp
            3     ['.cpp']                 None
        '''
      )
    plan = plans.makeplan(
        interp
      , flags=plans.MAKE_ICURRY | plans.MAKE_JSON | plans.MAKE_TARGET_SOURCE
            | plans.MAKE_TARGET_OBJECT
      )
    self.checkStr(plan,
        '''
        Build plan with 4 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                json2cpp
            3     ['.cpp']                 cpp2so
            4     ['.so']                  None
        '''
      )
    plan = plans.makeplan(interp, flags=plans.MAKE_ALL)
    self.checkStr(plan,
        '''
        Build plan with 4 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                json2cpp
            3     ['.cpp']                 cpp2so
            4     ['.so']                  None
        '''
      )
    plan = plans.makeplan(interp, flags=plans.MAKE_ALL | plans.ZIP_JSON)
    self.checkStr(plan,
        '''
        Build plan with 4 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json.z']              json2cpp
            3     ['.cpp']                 cpp2so
            4     ['.so']                  None
        '''
      )

  def test_05_truncated(self):
    plan = plans.makeplan(flags=plans.MAKE_JSON)
    self.checkStr(plan,
        '''
        Build plan with 0 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               None
        '''
      )

  def test_06_nointerp(self):
    plan = plans.makeplan(flags=plans.MAKE_ALL)
    self.checkStr(plan,
        '''
        Build plan with 2 steps:
            Stage Suffixes                 Step
            ----- ------------------------ ----------------------------------------
            0     ['.curry']               curry2icurry
            1     ['.icy']                 icurry2json
            2     ['.json']                None
        '''
      )


