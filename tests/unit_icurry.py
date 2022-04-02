import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import icurry
from curry.utility.binding import binding
import curry
import sys

class ICurryTestCase(cytest.TestCase):
  # def testICurryCoverage1(self):
  #   from curry.lib import mynot
  #   imodule = getattr(mynot, '.icurry')
  #   ifun_main = imodule.functions['main']
  #   ifun_mynot = imodule.functions['mynot']
  #   self.assertFalse(imodule == ifun_mynot)
  #   self.assertFalse(ifun_main == ifun_mynot)
  #   self.assertTrue(ifun_main != ifun_mynot)
  #   self.assertFalse(ifun_main == ifun_mynot)
  #   self.assertFalse(ifun_main == None)

  # def testICurryGetMDFromType(self):
  #   from curry.lib import atableFlex, hello
  #   imodule1 = getattr(atableFlex, '.icurry')
  #   imodule2 = getattr(hello, '.icurry')
  #   AB = imodule1.types['AB']
  #   self.assertEqual(AB.metadata, {})
  #   self.assertEqual(imodule1.types['AB'].metadata, {})
  #   self.assertNotIn('AB', imodule2.types)

  #   # self.assertEqual(icurry.metadata.getmd(AB, imodule1), {})
  #   # self.assertEqual(icurry.metadata.getmd(AB, imodule2), {})

  # def testICurryCoverage4(self):
  #   try:
  #     del sys.modules['curry.lib.helloExternal']
  #   except KeyError:
  #     pass
  #   with capture_log('curry.backends.generic.compiler') as log \
  #      , binding(curry.flags, 'lazycompile', False):
  #     from curry.lib import helloExternal
  #   log.checkMessages(
  #       self, warning="external function 'helloExternal.undef' is not defined"
  #     )

  def testIModuleMerge(self):
    from curry.lib import hello, helloExternal
    imodule1 = getattr(helloExternal, '.icurry')
    imodule2 = getattr(hello, '.icurry')
    self.assertRaisesRegex(
        TypeError
      , "cannot import 'undef' from module 'hello'"
      , lambda: imodule1.merge(imodule2, ['undef'])
      )

  def testSymbolNames1(self):
    # Programmatic testing of ICurry names.
    def _gensymbols(modulename, imodule):
      for fname, ifun in imodule.functions.items():
        yield fname, ifun
      for typename, itype in imodule.types.items():
        yield typename, itype
        for ictor in itype.constructors:
          yield ictor.name, ictor

    for modulename in ['Prelude', 'Data.Either', 'Control.SetFunctions']:
      module = curry.import_(modulename)
      imodule = getattr(module, '.icurry')
      packagename = modulename.rpartition('.')[0]

      self.assertEqual(imodule.name, modulename.rpartition('.')[-1])
      self.assertEqual(imodule.modulename, modulename)
      self.assertEqual(imodule.packagename, packagename)
      self.assertEqual(imodule.splitname(), modulename.split('.'))

      for symbolname, isym in _gensymbols(modulename, imodule):
        self.assertEqual(isym.name, symbolname)
        self.assertEqual(isym.modulename, modulename)
        self.assertEqual(isym.packagename, packagename)
        self.assertEqual(isym.splitname(), modulename.split('.') + [symbolname])


  def testSymbolNames2(self):
    # Spot-checking some funny ICurry names.
    iobj = curry.symbol('Prelude..').icurry
    self.assertEqual(iobj.name, '.')
    self.assertEqual(iobj.modulename, 'Prelude')
    self.assertEqual(iobj.splitname(), ['Prelude', '.'])

    iobj = curry.symbol('Prelude.pi._#lambda').icurry
    self.assertEqual(iobj.name, 'pi._#lambda')
    self.assertEqual(iobj.modulename, 'Prelude')
    self.assertEqual(iobj.splitname(), ['Prelude', 'pi._#lambda'])

    iobj = curry.symbol('Data.Either.partitionEithers.left.24').icurry
    self.assertEqual(iobj.name, 'partitionEithers.left.24')
    self.assertEqual(iobj.modulename, 'Data.Either')
    self.assertEqual(iobj.splitname(), ['Data', 'Either', 'partitionEithers.left.24'])
