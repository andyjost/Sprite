'''Typed API checks for the first-ten community regression programs.'''
import cytest # from ./lib; must be first
from cytest import oracle
from cytest.clean import clean
from func_community import GOALS, oracle_source, record, sprite_results
from curry import config
from curry.typecheck.sigtable import InterfaceError
from curry.toolchain import _preprocessor
import pathlib, unittest
import curry

ROOT = pathlib.Path('data/curry/community')


class TestCommunityTypes(cytest.TestCase):
  def load_fixture(self, path, name):
    curry.path[:0] = [str(ROOT / path), str(ROOT / 'support')]
    return curry.import_(name)

  def assert_typed_value(self, expression, typename, value):
    self.assertEqual(curry.typeof(expression, defaulted=True), typename)
    self.assertEqual(list(curry.eval(expression)), [value])

  def test_recursive_let_arguments(self):
    module = self.load_fixture('pakcs-3.10.0-testsuite/LanguageTests', 'TestLetRec')
    self.assert_typed_value(module.onetwo(6), '[Int]', [1,2,1,2,1,2])

  def test_newtype_partial_constructor(self):
    module = self.load_fixture('pakcs-3.10.0-testsuite/LanguageTests', 'TestNewtype')
    self.assert_typed_value(module.runXD(True), '(Bool, Bool)', (True, True))

  def test_record_argument(self):
    module = self.load_fixture('pakcs-3.10.0-testsuite/LanguageTests', 'TestRecords')
    self.assert_typed_value(module.isJohn(module.john1), 'Bool', True)

  def test_function_pattern_argument(self):
    module = self.load_fixture('pakcs-3.10.0-testsuite/LanguageTests', 'TestFuncPattern')
    self.assert_typed_value(module.pali('otto'), 'Bool', True)

  def test_module_default(self):
    module = self.load_fixture('pakcs-3.10.0-testsuite/TypeclassTests', 'TestDefault')
    self.assert_typed_value(curry.term(module.withDefault), '()', ())

  def test_prelude_property_expression(self):
    module = self.load_fixture('base-3.4.0-test', 'TestPreludeGoals')
    self.assert_typed_value(curry.term(module.checkPlus), 'Int', 5)

  @unittest.skip('unsupported module Control.Search.SetFunctions; stage E')
  def test_set_functions(self):
    pass

  @cytest.with_flags(interpret='off')
  def check_non_linear_function_pattern(self, goal):
    source = ROOT / 'pakcs-3.10.0-testsuite/LanguageTests/TestFuncPatternGoals.curry'
    self.load_fixture('pakcs-3.10.0-testsuite/LanguageTests', source.stem)
    entry = next(e for e in GOALS if e['module'].endswith(source.name)
                 and e['goal'] == goal)
    expected = source.with_name(source.stem + '.' + goal + '.au-gen').read_text()
    proc, actual = sprite_results(source, goal, timeout=5)
    record(entry, expected, actual)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertSameResultMultiset(actual, expected)

  @unittest.expectedFailure
  def test_non_linear_function_pattern_just_zero(self):
    self.check_non_linear_function_pattern('justZeroGoal')

  @unittest.expectedFailure
  def test_non_linear_function_pattern_just_failed(self):
    self.check_non_linear_function_pattern('justFailedGoal')

  def test_local_polymorphism(self):
    curry.path.insert(0, str(ROOT / 'support'))
    curry.path.insert(0, str(ROOT / 'kics2-3.5.0-testsuite/SpecialTests'))
    module = curry.import_('TestPolySubExp')
    for name, expected, typename in (
        ('poly1', 3, 'Int'), ('poly2', True, 'Bool'), ('poly3', 42, 'Int')):
      with self.subTest(goal=name):
        expr = curry.term(getattr(module, name))
        self.assertEqual(curry.typeof(expr, defaulted=True), typename)
        self.assertEqual(list(curry.eval(expr)), [expected])

  @oracle.require
  @unittest.skipIf(config.frontend_version() == '2.0.0',
                   'front end 2.0.0 cannot parse multi-parameter classes')
  @cytest.with_flags(interpret='off')
  def test_multi_parameter_boundary(self):
    curry.path.insert(0, str(ROOT / 'support'))
    curry.path.insert(0, str(ROOT / 'pakcs-3.10.0-testsuite/TypeclassTests'))
    module = curry.import_('TestMPTCCoerceGoals')
    source = ROOT / 'pakcs-3.10.0-testsuite/TypeclassTests/TestMPTCCoerceGoals.curry'
    with oracle_source(source) as (reference, work):
      for entry, expected in zip(
          (e for e in GOALS if e['module'].endswith('TestMPTCCoerceGoals.curry')),
          (1, True, False, True)):
        actual = list(curry.eval(getattr(module, entry['goal'])))
        self.assertEqual(actual, [expected])
        stated = oracle.divine(reference, entry['goal'], [work], timeout=20,
                               record_errors=True).decode()
        shown = '\n'.join(curry.show(value) for value in actual)
        record(entry, stated, shown)
        self.assertEqual(clean(stated), clean(shown))
    original = curry.import_('TestMPTCCoerce')
    with self.assertRaisesRegex(InterfaceError,
        'multi-parameter class TestMPTCCoerce.Coerce is not supported'):
      original.coerce(True)


class TestCommunityIO(cytest.TestCase):
  @cytest.with_flags(interpret='off')
  def test_diamond_one_line(self):
    # The original size/spacing algorithm at n=1 is a bounded IO harness.
    code = (
        'import curry\n'
        "curry.reset(interpret='off')\n"
        "curry.path.insert(0, 'data/curry/community/curry2go-1.7.0-examples')\n"
        "module = curry.import_('DiamondGoals')\n"
        'list(curry.eval(module.diamondOne))\n'
      )
    proc = cytest.run_in_subprocess(code, timeout=30, address_space=2 << 30)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertEqual(proc.stdout, ' 1  \n')


class TestCommunityLoading(cytest.TestCase):
  def test_frontend_large_negative_literal(self):
    # Issue #167: an Int literal beyond 64 bits loads without narrowing.
    from unit_community_compile import check_source
    check_source(self, 'NegLit.curry')

  def test_frontend_pakcs_prelude(self):
    # Issue #168: a namesake of a library module (the front end's own Prelude
    # fixture) loads the library's symbols.
    from unit_community_compile import check_source
    check_source(self, 'Prelude.curry')


# Issue #168: a module named like the prefix of its hierarchical siblings
# recurses in the importer.
# Keep one bounded assertion for every affected source.
for filename in ('InstanceExport.curry', 'InstanceExport/M.curry',
                 'InstanceExport/N.curry', 'InstanceExport/O.curry',
                 'InstanceExport/P.curry'):
  def test(self, filename=filename):
    from unit_community_compile import check_source
    check_source(self, filename)
  setattr(TestCommunityLoading,
      'test_frontend_' + filename[:-6].replace('/', '_'),
      test)


class TestCommunityRegressions(cytest.TestCase):
  @unittest.expectedFailure
  @cytest.with_flags(interpret='off')
  def test_default_rule_blocks_solver(self):
    # Both PAKCS oracles enumerate six finite two-block solutions. Sprite
    # does not finish the search; retain a bounded reproducer for review.
    source = ROOT / 'tutorial/chapter6/BetterBlocksGoals.curry'
    reason = _preprocessor.missing(source.with_name('betterblocks.curry'))
    if reason:
      self.skipTest(reason)
    curry.path.insert(0, str(source.parent))
    curry.import_(source.stem)
    expected = source.with_name('BetterBlocksGoals.solveSimple.au-gen').read_text()
    proc, actual = sprite_results(source, 'solveSimple', timeout=5,
                                  address_space=256 << 20)
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertSameResultMultiset(actual, expected)

  def test_lifted_non_linear_function_pattern(self):
    # Issue #169: the lifted non-linear functional pattern gives one free value
    # where both oracles give none.
    from unit_community_compile import frontend_sources
    source = ROOT / 'frontend-3.1.0-test-pass/FP_Lifting.curry'
    with frontend_sources(source) as (local, work):
      for interpret in ('off', 'all'):
        for goal, expected in (('main3', ''), ('main2', '_a')):
          with self.subTest(interpret=interpret, goal=goal):
            # The bound guards against a divergence; the interpreted route of
            # every module takes tens of seconds on the Intel macOS runner of
            # CI (run 40245416616 timed out at five).
            proc, actual = sprite_results(local, goal, timeout=90,
                                           interpret=interpret)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertSameResultMultiset(actual, expected)
