"""Rigid waits must not borrow a sibling's narrowing decision (#252, #253)."""
import cytest # from ./lib; must be first
import curry


SOURCE = '''module BoundWait where
import Control.SetFunctions
narrow :: Bool -> Int
narrow True = 1
narrow False = 2
gnf :: Bool -> Int
gnf x = (const 0 $## (x,0)) ? narrow x
root :: Bool -> Int
root x = (const 0 $## x) ? narrow x
hnf :: Bool -> Int
hnf x = (const 0 $! ensureNotFree x) ? narrow x
strict :: Bool -> Int
strict x = (const 0 $# x) ? narrow x
ground :: Bool -> (Bool,Int)
ground x = (id $## (x,0)) ? (if x then (True,1) else (False,2))
alias :: Bool -> (Bool,Int)
alias x = groundNormalForm (x,0) ? (if x then (True,1) else (False,2))
spine :: [Bool] -> [Bool]
spine x = ensureSpine x ? narrowList x
narrowList :: [Bool] -> [Bool]
narrowList [] = []
narrowList (_:_) = [True]
pair :: Bool -> Bool -> Int
pair x y = (const 0 $## (x,y)) ? (narrow x + narrow y)
equivalent :: Bool -> Bool -> Int
equivalent x y = (x =:= y) &> gnf x
inside :: Bool -> Int
inside x = const 0 $## (x,0)
capsule :: Bool -> Int
capsule x = head (sortValues (set1 inside x)) ? narrow x
nested :: Bool -> Int
nested x = head (sortValues (set1 inner x)) ? narrow x
inner :: Bool -> Int
inner x = head (sortValues (set1 inside x))
newvars :: [Bool] -> Bool -> Int
newvars x y = (const 0 $## x) ? narrow y
forkWait :: Bool -> Int
forkWait x = (((ensureNotFree x == True) & (True ? failed)) &> 0) ? narrow x
demand :: Bool -> Bool
demand external
mixed :: Bool -> Int
mixed x = (((const True $## x) & demand x) &> 0) ? narrow x
ordinaryDemand :: Bool -> Int
ordinaryDemand x = (if demand x then 3 else 4) ? narrow x
conjunction :: Bool -> Int
conjunction x = ((ensureNotFree x == True) & (x == True)) &> 0
ordinary :: Bool -> Int
ordinary x = (if (id $! x) then 3 else 4) ? narrow x
'''


def check_wait(goal, types=('Bool',), siblings=('2', '1'),
               bindings=((0, True),), result=('0',), collect=False):
  from curry import inspect
  from curry.backends.cxx import curryrtbindings as native
  curry.reset(interpret='all', jit='off', rotation='steps:65536', checker=True)
  native.register_primitive('BoundWait.demand', 1, lambda x: x)
  module = curry.compile(SOURCE)
  variables = [curry.term(curry.free('v%d' % i, type=t))._node
               for i, t in enumerate(types)]
  rts = native.RuntimeState(cytest.raw.interp(),
                           cytest.raw.expr(getattr(module, goal), *variables))
  try:
    answers = []
    try:
      for value in rts.generate_values():
        answers.append(str(value))
    except curry.SuspensionError:
      suspended = True
    else:
      suspended = False
    assert sorted(answers) == sorted(siblings), (answers, siblings)
    assert suspended, 'search exhausted instead of suspending'
    assert rts.queue_size == 1, rts.queue_size
    vids = [inspect.fwd_chain_target(v).successors[0] for v in variables]
    if collect:
      # Only the graph and residual IDs retain the variables across collection.
      variables.clear()
      native.gc_collect()
      native.gc_collect()
      native.gc_verify()
    for position, (index, value) in enumerate(bindings):
      if isinstance(value, tuple) and value[0] == 'list':
        value = [variables[value[1]]]
      native.checker_debug_bind(rts, vids[index], cytest.raw.expr(value))
      native.checker_debug_update_binding(rts, vids[index])
      if position + 1 < len(bindings):
        try:
          next(rts.generate_values())
        except curry.SuspensionError:
          pass
        else:
          raise AssertionError('partial binding released the application')
    answers = [str(value) for value in rts.generate_values()]
    assert answers == list(result), answers
    assert rts.queue_size == 0, rts.queue_size
  finally:
    rts.close()


class TestBoundWait(cytest.TestCase):
  def child(self, code):
    # Native evaluation cannot be interrupted by SIGALRM. A timeout is a
    # failure, never evidence of suspension; the helper reaps the child.
    proc = cytest.run_in_subprocess(
        'from unit_issue252 import check_wait\n' + code, timeout=60)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

  def test_ground_wait_and_resume(self):
    self.child("check_wait('gnf')")

  def test_ground_root_wait(self):
    self.child("check_wait('root')")

  def test_nonfree_wait_and_resume(self):
    self.child("check_wait('hnf')")

  def test_no_nonground_answer(self):
    self.child("check_wait('ground', siblings=('(False, 2)', '(True, 1)'), "
               "result=('(True, 0)',))")

  def test_strict_wrapper(self):
    self.child("check_wait('strict')")

  def test_ground_wrapper(self):
    self.child("check_wait('alias', siblings=('(False, 2)', '(True, 1)'), "
               "result=('(True, 0)',))")

  def test_spine_wrapper(self):
    self.child("check_wait('spine', types=('[Bool]',), "
               "siblings=('[]', '[True]'), bindings=((0, []),), result=('[]',))")

  def test_several_bindings_x_first(self):
    self.child("check_wait('pair', types=('Bool', 'Bool'), "
               "siblings=('2','3','3','4'), bindings=((0, True),(1, False)))")

  def test_several_bindings_y_first(self):
    self.child("check_wait('pair', types=('Bool', 'Bool'), "
               "siblings=('2','3','3','4'), bindings=((1, False),(0, True)))")

  def test_equivalent_class(self):
    self.child("check_wait('equivalent', types=('Bool','Bool'), bindings=((1, True),))")

  def test_capsule_outside_wait(self):
    self.child("check_wait('capsule')")

  def test_nested_capsule_wait(self):
    self.child("check_wait('nested')")

  def test_binding_introduces_free_variables(self):
    self.child("check_wait('newvars', types=('[Bool]', 'Bool'), "
               "bindings=((0, ('list', 1)), (1, True)))")

  def test_wait_survives_fork(self):
    self.child("check_wait('forkWait')")

  def test_no_spin(self):
    self.child("check_wait('gnf')\nprint('suspended and resumed')")

  @cytest.skipUnlessGcBackend('wdgc', 'requires the default collector build')
  def test_default_collector_wait(self):
    self.child("check_wait('capsule', collect=True)")

  @cytest.skipUnlessGcBackend('mps', 'requires an MPS build')
  def test_mps_collector_wait(self):
    self.child("check_wait('capsule', collect=True)")

  def test_ordinary_narrowing_and_conjunction(self):
    self.child('''
import curry
from unit_issue252 import SOURCE
curry.reset(interpret='all', jit='off', rotation='steps:65536', checker=True)
from curry.backends.cxx import curryrtbindings as native
native.register_primitive('BoundWait.demand', 1, lambda x: x)
m = curry.compile(SOURCE)
for goal, typ, expected in [('ordinary', 'Bool', [1,2,3,4]),
                            ('conjunction', 'Bool', [0]),
                            ('ordinaryDemand', 'Bool', [1,2,3,4]),
                            ('mixed', 'Bool', [0,1,2])]:
  x = curry.term(curry.free('x', type=typ))
  answers = sorted(curry.eval(getattr(m, goal)(x)))
  assert answers == expected, (goal, answers, expected)
''')
