'''Issue #154: compile errors carry the diagnostic without a command line.'''
import cytest # from ./lib; must be first
import curry
import os
import tempfile
import unittest

class TestCompileDiagnostic(cytest.TestCase):
  def test_first_error_after_a_warning(self):
    report = ('/source/M.curry:1:1 Warning: overlapping rules\n'
        '/source/M.curry:3:4 Error:\n    undefined symbol\n'
        '/source/M.curry:5:6 Error: another error\n')
    error = curry.CompileError(report)
    self.assertEqual(str(error), 'M.curry:3:4 Error: undefined symbol')
    self.assertEqual(error.report, report)
    self.assertEqual((error.line, error.column), (3, 4))
    from curry.objects.terms import text_error
    mapped = text_error(error, 'goal', 0, False)
    self.assertEqual((mapped.line, mapped.column), (3, 4))

  def test_expression_and_parse(self):
    for compile_ in (lambda: curry.parse('1 +'),
        lambda: curry.parse('1 +')):
      with self.assertRaises(curry.CompileError) as caught:
        compile_()
      error = caught.exception
      self.assertIn('Unexpected end-of-file', str(error))
      self.assertIn('Unexpected end-of-file', error.report)
      self.assertNotIn('while running', str(error))
      self.assertNotIn('--flat', str(error))
      self.assertNotIn(tempfile.gettempdir(), str(error))
      self.assertNotIn(os.getcwd(), str(error))
      self.assertIsInstance(error.line, int)
      self.assertIsInstance(error.column, int)

class TestErrorRendering(cytest.TestCase):
  def test_defaulting_preserves_constraints_on_both_routes(self):
    P = curry.import_('Prelude')
    for build in (lambda: curry.eval(P['+'](P.maxBound, 1)),
        lambda: curry.eval(curry.parse('maxBound + 1')),
        lambda: curry.eval(curry.parse('maxBound + 1'))):
      with self.assertRaises((curry.CompileError, curry.DefaultingError)) as caught:
        build()
      lines = str(caught.exception).splitlines()
      self.assertEqual(lines[0], 'cannot handle the overloaded goal maxBound + 1 '
          'of type (Bounded a, Num a) => a')
      self.assertEqual(lines[1].strip(),
          'Cannot handle arbitrary overloaded top-level expressions')
      self.assertIn('state the type:', lines[2])
      self.assertNotIn('<Term', lines[2])
      self.assertNotIn('P.+', lines[2])

  def test_defaulting_builder_and_symbol_routes(self):
    P = curry.import_('Prelude')
    for build in (lambda: curry.eval(P.read('5')), lambda: curry.eval(P.show)):
      with self.assertRaises(curry.DefaultingError) as caught:
        build()
      lines = str(caught.exception).splitlines()
      self.assertEqual(len(lines), 3)
      self.assertTrue(lines[0].startswith('cannot handle the overloaded goal '))
      self.assertEqual(lines[1], 'Cannot handle arbitrary overloaded top-level expressions')
      self.assertTrue(lines[2].startswith('state the type: curry.term('))

  def test_annotation_mismatch_is_not_syntax(self):
    with self.assertRaises(curry.MismatchError) as caught:
      curry.term(True, type='Int')
    self.assertNotIsInstance(caught.exception, curry.TypeSyntaxError)

if __name__ == '__main__':
  unittest.main()
