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
    curry.flags['interpret'] == 'off'
  , 'under interpret:off a second library of a live module name is refused'
  )


class TestCompileModules(cytest.TestCase):
  def test_dotted_header_and_reload(self):
    module = curry.compile('module TextPackage.Child where\nf :: Int\nf = 7')
    self.assertEqual(curry.info(module).name, 'TextPackage.Child')
    self.assertIs(curry.modules['TextPackage.Child'], module)
    self.assertNotIn('TextPackage', curry.modules)
    from curry.lib import TextPackage
    self.assertIs(TextPackage.Child, module)
    old = module.f
    self.assertEqual(curry.eval(old).one(), 7)
    self.assertIs(curry.reload(module, text='f :: Int\nf = 8'), module)
    self.assertEqual(curry.eval(module.f).one(), 8)
    self.assertIs(TextPackage.Child, module)
    with self.assertRaises(curry.StaleError):
      curry.eval(old).one()

  def test_generated_name_skips_a_loaded_name(self):
    from curry.interpreter import compile as compilemod
    from unittest import mock
    import itertools
    with mock.patch.object(compilemod, '_module_counter', itertools.count(9000)):
      occupied = curry.compile('f :: Int\nf = 1', name='Interactive_9000')
      generated = curry.compile('f :: Int\nf = 2')
    self.assertEqual(curry.info(generated).name, 'Interactive_9001')
    self.assertEqual(curry.eval(occupied.f).one(), 1)
    self.assertEqual(curry.eval(generated.f).one(), 2)

  def testExprModuleOutlivesNextCompile(self):
    '''
    An expression module stays loaded while its goal can still be evaluated.
    An audit finding: compiling a second expression unloaded the first one's
    module, and the C++ backend then read freed memory through the goal.
    '''
    a = curry.parse('"hello" ++ " world"')
    b = curry.parse('"other"')
    gc.collect()
    self.assertEqual(list(curry.eval(a)), ['hello world'])
    self.assertEqual(list(curry.eval(b)), ['other'])

  def testAnonymousModuleNamesNotReused(self):
    '''
    The names of anonymous modules are unique for the process.  An audit
    finding: the counter restarted with each reset, so a module compiled after
    a reset took the name of one compiled before it.  On the C++ backend the
    second module then resolved to the first one's code.
    '''
    first = curry.compile('f :: Int\nf = 1')
    goal = curry.parse('"first"')
    # Keep the first expression module loaded across the reset.
    held = list(cytest.raw.interp()._expression_modules)
    curry.reset()
    second = curry.compile('f :: Int\nf = 2')
    self.assertNotEqual(first.__name__, second.__name__)
    self.assertEqual(list(curry.eval(second.f)), [2])
    self.assertEqual(list(curry.eval(curry.parse('"second"'))), ['second'])
    del held, goal

  @cytest.with_flags(interpret='off')
  def testReusedModuleNameIsAnError(self):
    '''
    A second library under a live module name is refused.  The runtime would
    otherwise resolve the new module to the code of the first one.  Under
    the default of the flag ``interpret`` (tiered) a module compiled from a
    string is interpreted and makes no library; a module of the same name
    made again takes the tables of the first back (unit_cxx_tiered.py).
    '''
    first = curry.compile('f :: Int\nf = 1', name='Dup')
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', name='Dup')
    self.assertEqual(curry.eval(second.f).one(), 2)
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
    first = curry.compile('f :: Int\nf = 1', name='SameNameAlive')
    self.assertEqual(list(curry.eval(first.f)), [1])
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', name='SameNameAlive')
    with self.assertRaises(curry.StaleError):
      first.f
    self.assertEqual(list(curry.eval(second.f)), [2])
    curry.reset()
    third = curry.compile('f :: Int\nf = 3', name='SameNameAlive')
    self.assertEqual(list(curry.eval(third.f)), [3])
    del first, second, third

  @REFUSED_UNDER_OFF
  @cytest.hardreset
  def testSameNameAfterReloadWhileFirstAlive(self):
    '''
    The hard reset of curry.reload unlinks the modules of the interpreter
    it replaces, so the same holds across a reload (issue #114).
    '''
    first = curry.compile('f :: Int\nf = 1', name='SameNameReload')
    self.assertEqual(list(curry.eval(first.f)), [1])
    curry.reset()
    second = curry.compile('f :: Int\nf = 2', name='SameNameReload')
    with self.assertRaises(curry.StaleError):
      first.f
    self.assertEqual(list(curry.eval(second.f)), [2])
    del first, second

  def testStaleSymbolIsRefused(self):
    '''
    The second symptom of issue #114, the owner's decision: a symbol of a
    module that left the interpreter refuses to evaluate.  Previously it
    evaluated its old code, or the code of the current incarnation
    of its name when the shape agrees.  The proposed refusal is an error at
    evaluation and at expression building (see the TODO entry of
    2026-10-10).
    '''
    first = curry.compile('f :: Int\nf = 1', name='StaleSymbol')
    self.assertEqual(list(curry.eval(first.f)), [1])
    curry.reset()
    with self.assertRaises(curry.StaleError):
      list(curry.eval(first.f))
    del first
