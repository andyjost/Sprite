import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import icurry
from curry.utility.binding import binding
import curry
import sys

class ICurryTestCase(cytest.TestCase):
  def testICurryCoverage1(self):
    from curry.lib import mynot
    imodule = getattr(mynot, '.icurry')
    ifun_main = imodule.functions['mynot.main']
    ifun_mynot = imodule.functions['mynot.mynot']
    self.assertFalse(imodule == ifun_mynot)
    self.assertFalse(ifun_main == ifun_mynot)
    self.assertTrue(ifun_main != ifun_mynot)
    self.assertFalse(ifun_main == ifun_mynot)
    self.assertFalse(ifun_main == None)
    self.assertRaisesRegexp(
        ValueError
      , 'expected module name "mynot", got "Foo"'
      , lambda: mynot.mynot.ident.setmodule('Foo')
      )

  def testICurryUnboxFailure(self):
    from curry.lib import mynot
    imodule = getattr(mynot, '.icurry')

    not_applic = imodule.functions['mynot.mynot'].code[1] \
                    .switch['Prelude.True']
    applic = not_applic[0].expr
    self.assertNotIsInstance(not_applic, icurry.Applic)
    self.assertIsInstance(applic, icurry.Applic)
    self.assertRaisesRegexp(
        TypeError
      , 'expected an Applic'
      , lambda: icurry.unbox(not_applic)
      )
    self.assertRaisesRegexp(
        TypeError
      , 'expected an Int, Float, or Char'
      , lambda: icurry.unbox(applic)
      )

  def testICurryCoverage2(self):
    from curry.lib import atableFlex
    imodule = getattr(atableFlex, '.icurry')
    AB = imodule.types['atableFlex.AB']
    self.assertEqual(AB[0], AB.constructors[0])

  def testICurryGetMDFromType(self):
    # reload(curry)
    from curry.lib import atableFlex, hello
    imodule1 = getattr(atableFlex, '.icurry')
    imodule2 = getattr(hello, '.icurry')
    AB = imodule1.types['atableFlex.AB']
    self.assertEqual(icurry.getmd(AB, imodule1), [])
    self.assertEqual(icurry.getmd(AB, imodule2), [])

  def testICurryCoverage4(self):
    try:
      del sys.modules['curry.lib.helloExternal']
    except KeyError:
      pass
    with capture_log('curry.interpreter.function_compiler') as log \
       , binding(curry.flags, 'lazycompile', False):
      from curry.lib import helloExternal
    log.checkMessages(self, warning='external function "helloExternal.undef" is not defined')

  def testIModuleMerge(self):
    from curry.lib import hello, helloExternal
    imodule1 = getattr(helloExternal, '.icurry')
    imodule2 = getattr(hello, '.icurry')
    self.assertRaisesRegexp(
        TypeError
      , 'exported symbol "helloExternal.undef" not found'
      , lambda: imodule1.merge(imodule2, ['undef'])
      )
