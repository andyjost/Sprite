import cytest # from ./lib; must be first
from cytest.logging import capture_log
from curry import icurry
from curry.utility.binding import binding
import curry, importlib, sys, unittest

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
    self.assertEqual(AB.metadata, {})
    self.assertEqual(imodule1.types['AB'].metadata, {})
    self.assertNotIn('AB', imodule2.types)

  def testICurryCoverage4(self):
    try:
      del sys.modules['curry.lib.helloExternal']
    except KeyError:
      pass
    self.assertRaisesRegex(
        curry.CompileError
      , "failed to resolve external function 'helloExternal.undef'"
      , lambda: importlib.import_module('curry.lib.helloExternal')
      )

  def testIModuleMerge(self):
    from curry.lib import hello
    from curry.toolchain._mergecurry import copyExportedNames
    helloM = getattr(hello, '.icurry')
    self.assertRaisesRegex(
        curry.CompileError
      , "cannot import 'undef' from module 'hello'"
      , lambda: copyExportedNames(helloM, helloM, ['undef'])
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


class TestVisit(cytest.TestCase):
  '''
  The walk of icurry.visit is iterative (the depth of a tree costs no frame
  of Python; issue #125) and calls the visitor in the order of the
  recursive walk it replaced: the parts of an object before the object, or
  after it under ``topdown``; a container (a mapping, a sequence) is
  iterated and not shown to the visitor.
  '''
  def function(self):
    T = icurry.types
    body = T.IFuncBody(T.IBlock(
        [T.IVarDecl(1), T.IFreeDecl(2)]
      , [T.IVarAssign(1, T.IVarAccess(0, [0]))]
      , T.ICaseCons(1, [
            T.IConsBranch('M.C', 2, T.IBlock([], [], T.IReturn(
                T.IOr(
                    T.IFCall('M.g', [T.IFCall('M.h', [T.IVar(1)]), T.ILit(T.IInt(1))])
                  , T.ILit(T.IInt(2))
                  )
              )))
          , T.IConsBranch('M.D', 0, T.IBlock([], [], T.IExempt()))
          ])
      ))
    return T.IFunction('M.f', 1, body=body)

  @staticmethod
  def reference(visitor, arg, topdown=False):
    '''The recursive walk, as icurry.visit was written before.'''
    import collections.abc
    T = icurry.types
    def walk(obj):
      if isinstance(obj, collections.abc.Mapping) and not isinstance(obj, str):
        for elem in obj.values():
          walk(elem)
        return
      elif isinstance(obj, collections.abc.Sequence) and not isinstance(obj, str):
        for item in obj:
          walk(item)
        return
      elif isinstance(obj, T.IBlock):
        parts = [obj.vardecls, obj.assigns, obj.stmt]
        node = True
      elif isinstance(obj, T.IModule):
        parts = [obj.types, obj.functions]
        node = True
      elif isinstance(obj, T.IDataType):
        parts = [obj.constructors]
        node = True
      elif isinstance(obj, T.IFunction):
        parts = [obj.body]
        node = True
      elif isinstance(obj, T.IObject):
        parts = list(obj.children)
        node = True
      else:
        return
      if topdown:
        visitor(obj)
      for part in parts:
        walk(part)
      if not topdown:
        visitor(obj)
    walk(arg)

  def test_order(self):
    for topdown in False, True:
      ifun = self.function()
      seen, expected = [], []
      icurry.visit.visit(seen.append, ifun, topdown=topdown)
      self.reference(expected.append, ifun, topdown=topdown)
      self.assertEqual(len(seen), 20, topdown)
      self.assertEqual([id(x) for x in seen], [id(x) for x in expected], topdown)
      self.assertIs(seen[-1 if not topdown else 0], ifun)

  def test_module(self):
    # A module visited through its mappings of types and functions.
    imodule = getattr(curry.import_('Prelude'), '.icurry')
    for topdown in False, True:
      seen, expected = [], []
      icurry.visit.visit(seen.append, imodule, topdown=topdown)
      self.reference(expected.append, imodule, topdown=topdown)
      self.assertEqual([id(x) for x in seen], [id(x) for x in expected], topdown)

  def test_curried(self):
    ifun = self.function()
    seen = []
    walk = icurry.visit.visit(seen.append)
    walk(ifun)
    self.assertEqual(len(seen), 20)

  def test_replace_follows_the_replacement(self):
    # A top-down replacement is walked into: the parts of the replacement
    # are replaced as well.
    T = icurry.types
    h = T.IFCall('M.h', [T.IVar(1)])
    ret = T.IReturn(T.IFCall('M.g', [h]))
    j = T.IFCall('M.j', [])
    k = T.IFCall('M.k', [j])
    icurry.visit.replace(ret, {id(h): k, id(j): T.IVar(9)})
    self.assertIs(ret.expr.exprs[0], k)
    self.assertEqual(k.exprs, [T.IVar(9)])

  def test_deep_tree(self):
    T = icurry.types
    expr = T.ILit(T.IInt(0))
    for i in range(20000):
      expr = T.IFCall('M.c', [T.ILit(T.IInt(i)), expr])
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(1000)
    try:
      calls = []
      icurry.visit.visit(
          lambda iobj: calls.append(iobj) if isinstance(iobj, T.ICall) else None
        , T.IReturn(expr)
        )
    finally:
      sys.setrecursionlimit(limit)
    self.assertEqual(len(calls), 20000)
    # Post-order: the innermost call first.
    self.assertEqual(calls[0].exprs[1], T.ILit(T.IInt(0)))
    self.assertIs(calls[-1], expr)


class TestDeepCopy(cytest.TestCase):
  '''
  copy.deepcopy of a call or a choice walks the nested calls and choices on
  a stack of its own (ICall.__deepcopy__, IOr.__deepcopy__): the copy of a
  function body in the inliner ran out of frames at about 2700 elements of
  a literal list (issue #125).  The copy is the one copy.deepcopy made: new
  objects throughout, the sharing within the expression kept, the metadata
  copied.
  '''
  def test_copy(self):
    import copy
    T = icurry.types
    shared = T.IVar(2)
    inner = T.IOr(T.ILit(T.IInt(1)), T.IString('s'), metadata={'k': [1]})
    expr = T.IFPCall('M.f', 1, [shared, shared, inner], metadata={'m': 'x'})
    dup = copy.deepcopy(expr)
    self.assertEqual(dup, expr)
    self.assertIsNot(dup, expr)
    self.assertIs(type(dup), T.IFPCall)
    self.assertEqual(dup.missing, 1)
    self.assertIsNot(dup.exprs, expr.exprs)
    self.assertIsNot(dup.exprs[0], shared)
    self.assertIs(dup.exprs[0], dup.exprs[1])
    self.assertIsNot(dup.exprs[2], inner)
    self.assertIs(type(dup.exprs[2]), T.IOr)
    self.assertIsNot(dup.exprs[2].lhs, inner.lhs)
    self.assertEqual(dup.metadata['m'], 'x')
    self.assertEqual(dup.exprs[2].metadata['k'], [1])
    self.assertIsNot(dup.exprs[2].metadata['k'], inner.metadata['k'])
    # A shared part under two roots of one copy is one object in the copy.
    pair = [expr, expr.exprs[2]]
    dup2 = copy.deepcopy(pair)
    self.assertIs(dup2[0].exprs[2], dup2[1])

  def test_deep_expression(self):
    import copy
    T = icurry.types
    expr = T.ILit(T.IInt(0))
    for i in range(20000):
      expr = T.IFCall('M.c', [T.ILit(T.IInt(i)), expr])
    body = T.IFuncBody(T.IBlock([], [], T.IReturn(expr)))
    limit = sys.getrecursionlimit()
    sys.setrecursionlimit(1000)
    try:
      dup = copy.deepcopy(body)
    finally:
      sys.setrecursionlimit(limit)
    depth = 0
    e, f = dup.block.stmt.expr, expr
    while isinstance(e, T.IFCall):
      self.assertIsNot(e, f)
      self.assertEqual(e.exprs[0], f.exprs[0])
      e, f = e.exprs[1], f.exprs[1]
      depth += 1
    self.assertEqual(depth, 20000)
    self.assertEqual(e, T.ILit(T.IInt(0)))
