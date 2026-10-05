'''
The module registry behind curry.compile: an expression module lives while
its goal can run, anonymous names are unique for the process, and a reused
name is refused.  See unit_compile.py for the split of these tests.
'''
import cytest # from ./lib; must be first
import curry, gc, unittest

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
  def testReusedModuleNameIsAnError(self):
    '''
    A second library under a live module name is refused.  The runtime would
    otherwise resolve the new module to the code of the first one.
    '''
    first = curry.compile('f :: Int\nf = 1', modulename='Dup')
    curry.reset()
    with self.assertRaisesRegex(curry.exceptions.DynloadError, "'Dup'"):
      curry.compile('f :: Int\nf = 2', modulename='Dup')
    del first
