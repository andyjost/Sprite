"""Refused externals retain their named diagnostics in both execution routes."""
import cytest # from ./lib; must be first
import curry
import re
from curry import inspect
from curry.backends.cxx import curryrtbindings as curryrt
from curry.backends.refusals import refusal_message
from curry.exceptions import EvaluationError


class TestRefusals(cytest.TestCase):
  def check_messages(self, interpreted):
    cases = [
        ('Control.AllValues', 'allValues',
         'strong encapsulation; its results depend on the evaluation order'),
        ('Control.Findall', 'rewriteSome',
         'strong encapsulation; its results depend on the evaluation order'),
        ('GlobalVariable', 'prim_readGVar',
         'backtrackable global variables; their values depend on the search order'),
        ('CLP.R', 'prim_CLPR_i2f',
         'PAKCS constraint solvers; they are bound to the Prolog back end of PAKCS'),
        ('MissingPrimitive', 'f', None),
    ]
    for module, function, reason in cases:
      with self.subTest(module=module):
        M = curry.compile('%s :: Int -> Int\n%s external\n'
                          'argument :: Int\nargument = error "argument evaluated"'
                          % (function, function), name=module)
        symbol = getattr(M, function)
        fullname = module + '.' + function
        message = (fullname + ': not supported by Sprite: ' + reason +
            ' (see https://andyjost.github.io/Sprite/Compatibility.html)') if reason else (
            fullname + ': not implemented (no primitive in the runtime)')
        self.assertEqual(curryrt.icurry_is_interpreted(symbol.info), interpreted)
        with self.assertRaisesRegex(EvaluationError, re.escape(message)):
          list(curry.eval(symbol(M.argument)))
        expected_inspection = message if reason else message.replace(
            ': not implemented', ': external, not implemented')
        self.assertEqual(inspect.getimpl(symbol), expected_inspection)

  @cytest.with_flags(interpret='all', jit='off')
  def test_interpreted(self):
    self.check_messages(True)

  @cytest.with_flags(interpret='off', jit='off')
  def test_compiled(self):
    self.check_messages(False)

  def test_supported_and_unrelated_names(self):
    for fullname in [
        'Control.Search.AllValues.allValues',
        'Control.Search.Unsafe.rewriteAll', 'Control.Search.Unsafe.allValues',
        'Control.SetFunctions.set0', 'Data.Global.readGlobal',
        'Control.ValueSequence.emptyVS', 'Control.SearchTree.Traversal.traverse',
        'Control.Search.SearchTree.emptyVS', 'Other.allValues',
        'Control.AllValuesExtra.allValues']:
      with self.subTest(fullname=fullname):
        self.assertIsNone(refusal_message(fullname))
