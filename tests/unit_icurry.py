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
    ifun_main = imodule.functions['main']
    ifun_mynot = imodule.functions['mynot']
    self.assertFalse(imodule == ifun_mynot)
    self.assertFalse(ifun_main == ifun_mynot)
    self.assertTrue(ifun_main != ifun_mynot)
    self.assertFalse(ifun_main == ifun_mynot)
    self.assertFalse(ifun_main == None)

  def testICurryGetMDFromType(self):
    from curry.lib import atableFlex, hello
    imodule1 = getattr(atableFlex, '.icurry')
    imodule2 = getattr(hello, '.icurry')
    AB = imodule1.types['AB']
    self.assertEqual(icurry.metadata.getmd(AB, imodule1), {})
    self.assertEqual(icurry.metadata.getmd(AB, imodule2), {})

  def testICurryCoverage4(self):
    try:
      del sys.modules['curry.lib.helloExternal']
    except KeyError:
      pass
    with capture_log('curry.backends.generic.compiler.function_compiler') as log \
       , binding(curry.flags, 'lazycompile', False):
      from curry.lib import helloExternal
    log.checkMessages(
        self, warning="external function 'helloExternal.undef' is not defined"
      )

  def testIModuleMerge(self):
    from curry.lib import hello, helloExternal
    imodule1 = getattr(helloExternal, '.icurry')
    imodule2 = getattr(hello, '.icurry')
    self.assertRaisesRegex(
        TypeError
      , "cannot import 'undef' from module 'hello'"
      , lambda: imodule1.merge(imodule2, ['undef'])
      )
