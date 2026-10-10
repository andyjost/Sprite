'''
The module registry behind curry.compile: an expression module lives while
its goal can run, anonymous names are unique for the process, a reused
name is refused, and a name reused after a reset runs its own code while
the earlier module object is alive (issue #114).  See unit_compile.py for
the split of these tests.
'''
import cytest # from ./lib; must be first
import curry, gc, unittest

# Under interpret:off the C++ backend compiles a module from a string into a
# library, and a second library under a live module name is refused
# (testReusedModuleNameIsAnError); the other settings interpret it.
REFUSED_UNDER_OFF = unittest.skipIf(
    curry.flags['backend'] == 'cxx' and curry.flags['interpret'] == 'off'
  , 'under interpret:off a second library of a live module name is refused'
  )


class TestCompileModules(cytest.TestCase):
  @cytest.with_flags(defaultconverter='topython')
  def testExprModuleOutlivesNextCompile(self):
    '''
    An expression module stays loaded while its goal can still be evaluated.
    An audit finding: compiling a second expression unloaded the first one's
    module, and the C++ backend then read freed memory through the goal.
    '''
    a = curry.compile('"hello" ++ " world"', 'expr')
    b = curry.compile('"other"', 'expr')
    gc.collect()
    self.assertEqual(list(curry.eval(a)), ['hello world'])
    self.assertEqual(list(curry.eval(b)), ['other'])

  @cytest.with_flags(defaultconverter='topython')
  def testAnonymousModuleNamesNotReused(self):
    '''
    The names of anonymous modules are unique for the process.  An audit
    finding: the counter restarted with each reset, so a module compiled after
    a reset took the name of one compiled before it.  On the C++ backend the
    second module then resolved to the first one's code.
    '''
    first = curry.compile('f :: Int\nf = 1')
    goal = curry.compile('"first"', 'expr')
    # Keep the first expression module loaded across the reset.
    held = list(curry.getInterpreter()._expression_modules)
    curry.reset()
    second = curry.compile('f :: Int\nf = 2')
    self.assertNotEqual(first.__name__, second.__name__)
    self.assertEqual(list(curry.eval(second.f)), [2])
    self.assertEqual(list(curry.eval(curry.compile('"second"', 'expr'))), ['second'])
    del held, goal

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the module registry belongs to the C++ backend'
    )
  @cytest.with_flags(interpret='off')
  def testReusedModuleNameIsAnError(self):
    '''
    A second library under a live module name is refused.  The runtime would
    otherwise resolve the new module to the code of the first one.  Under
    the default of the flag ``interpret`` (tiered) a module compiled from a
    string is interpreted and makes no library; a module of the same name
    made again takes the tables of the first back (unit_cxx_tiered.py).
    '''
    first = curry.compile('f :: Int\nf = 1', modulename='Dup')
    curry.reset()
    with self.assertRaisesRegex(curry.exceptions.DynloadError, "'Dup'"):
      curry.compile('f :: Int\nf = 2', modulename='Dup')
    del first

  @REFUSED_UNDER_OFF
  def testSameNameAfterResetWhileFirstAlive(self):
    '''
    After a reset, a module compiled under the name of an earlier module
    runs its own code while the earlier module object is alive (issue
    #114).  On the C++ backend the registry of the runtime gave the second
    module the info tables of the first, with their steps, as long as the
    first module object held them: second.f gave 1, and so did third.f.
    The reset hands the tables over now (IBackend.module_unlinked), whether
    or not the module object is alive.
    '''
    first = curry.compile('f :: Int\nf = 1', modulename='SameNameAlive')
    self.assertEqual(list(curry.eval(first.f, converter='topython')), [1])
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', modulename='SameNameAlive')
    self.assertIsNot(first.f, second.f)
    self.assertEqual(list(curry.eval(second.f, converter='topython')), [2])
    curry.reset()
    third = curry.compile('f :: Int\nf = 3', modulename='SameNameAlive')
    self.assertEqual(list(curry.eval(third.f, converter='topython')), [3])
    del first, second, third

  @REFUSED_UNDER_OFF
  @cytest.hardreset
  def testSameNameAfterReloadWhileFirstAlive(self):
    '''
    The hard reset of curry.reload unlinks the modules of the interpreter
    it replaces, so the same holds across a reload (issue #114).
    '''
    first = curry.compile('f :: Int\nf = 1', modulename='SameNameReload')
    self.assertEqual(list(curry.eval(first.f, converter='topython')), [1])
    curry.reload()
    second = curry.compile('f :: Int\nf = 2', modulename='SameNameReload')
    self.assertIsNot(first.f, second.f)
    self.assertEqual(list(curry.eval(second.f, converter='topython')), [2])
    del first, second

  @unittest.skipIf(
      curry.flags['backend'] != 'cxx'
    , 'the second symptom of issue #114 is reported on the C++ backend'
    )
  @unittest.expectedFailure
  def testStaleSymbolIsRefused(self):
    '''
    The second symptom of issue #114, the owner's decision: a symbol of a
    module that left the interpreter should refuse to evaluate.  Today it
    evaluates: it runs its old code, or the code of the current incarnation
    of its name when the shape agrees.  The proposed refusal is an error at
    evaluation and at expression building (see the TODO entry of
    2026-10-10).
    '''
    first = curry.compile('f :: Int\nf = 1', modulename='StaleSymbol')
    self.assertEqual(list(curry.eval(first.f, converter='topython')), [1])
    curry.reset()
    with self.assertRaises(Exception):
      list(curry.eval(first.f, converter='topython'))
    del first
