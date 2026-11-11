'''Issue #285: front-end diagnostics reach public error views.'''
import cytest # from ./lib; must be first
import curry
from curry import config
from pathlib import Path
import os
import subprocess
import sys
import tempfile
import unittest


class TestDiagnostic(cytest.TestCase):
  def check_notes(self, error):
    error_notes = getattr(error, '__notes__', ())
    notes = '\n'.join(error_notes)
    for forbidden in (tempfile.gettempdir(), os.getcwd(), config.installed_path(), '--flat'):
      self.assertNotIn(str(forbidden), notes)
    self.assertEqual(len(str(error).splitlines()), 1)
    summary = str(error).split('Error:', 1)[-1].strip()
    self.assertNotIn(summary, error_notes[0] if error_notes else '')
    return notes

  def module_error(self, source):
    with tempfile.TemporaryDirectory() as directory:
      Path(directory, 'Bad285.curry').write_text('module Bad285 where\n' + source)
      with self.assertRaises(curry.CompileError) as caught:
        curry.import_('Bad285', path=[directory])
      return caught.exception

  def test_module_type(self):
    error = self.module_error('f :: Int -> Int\nf x = x ++ [1]\n')
    # Front end 3.1.0 names the function definition, 2.0.0 the equation.
    self.assertRegex(str(error),
        r'^Bad285\.curry:3:1-3:14 Error: Type error in (function definition|equation)$')
    notes = self.check_notes(error)
    for text in ('Inferred type', 'Expected type', 'f x = x ++ [1]'):
      self.assertIn(text, notes)

  def test_syntax(self):
    error = self.module_error('f = )\n')
    self.assertIn('Error:', str(error))
    self.check_notes(error)

  def test_two_errors(self):
    error = self.module_error('f :: Int -> Int\nf x = x ++ [1]\ng :: Int -> Int\ng x = x ++ [2]\n')
    self.assertEqual(len(error.__notes__), 2)
    self.assertIn('Bad285.curry:5:', error.__notes__[1])
    self.check_notes(error)

  def test_text(self):
    with self.assertRaises(curry.CompileError) as caught:
      curry.parse("1 + 'a'")
    notes = self.check_notes(caught.exception)
    self.assertRegex(notes, 'arising from infix operator|in infix application')
    self.assertNotIn('compiled_expression', notes)
    self.assertNotIn('|', notes)

  def test_report_blocks(self):
    report = ('[1 of 2] Compiling Bad\n'
        '/private/Bad.curry:1:1 Warning: ignore this\n    warning body\n'
        '/private/Bad.curry:2:1 Error:\n    first error\n'
        '    See /private/Other.curry and C:\\private\\Other.curry\n'
        '[2 of 2] Compiling Other\n'
        '/private/Other.curry:3:1 Error:\n    second error\n')
    error = curry.CompileError(report)
    self.assertEqual(len(error.__notes__), 2)
    notes = self.check_notes(error)
    self.assertIn('/private/Other.curry', notes)
    self.assertIn('C:\\private\\Other.curry', notes)
    self.assertNotIn('Compiling', notes)
    self.assertNotIn('warning', notes)
    self.assertTrue(error.__notes__[1].startswith('Other.curry:3:1 Error:'))

  def test_source_text(self):
    source = 'f = (map (/2) [1.0], "/data/input", True + 1) -- /example/comment\n'
    error = self.module_error(source)
    self.assertIn(source.strip(), self.check_notes(error))

  def test_text_syntax(self):
    with self.assertRaises(curry.CompileError) as caught:
      curry.parse(')')
    self.check_notes(caught.exception)

  def test_text_two_frontend_errors(self):
    with self.assertRaises(curry.CompileError) as caught:
      curry.parse("(1 + True,\n 1 + 'a')")
    notes = self.check_notes(caught.exception)
    # The columns of the front ends differ; the line is that of the text.
    self.assertRegex(notes, r'(?m)^2:\d+ Error:')
    self.assertIn('Prelude.Char', notes)
    self.assertNotIn('|', notes)

  def test_text_two_errors(self):
    from curry.objects.terms import text_error
    report = ('M.curry:4:40 Error:\n    first error\n    detail\n'
        '   |\n 4 | synthetic\n'
        'M.curry:5:6 Error: another error\n    second detail\n'
        '   |\n 5 | synthetic\n')
    error = text_error(curry.CompileError(report), 'bad\nbad', 3, False)
    self.assertIn('2:6 Error: another error', error.__notes__[1])
    self.assertIn('second detail', error.__notes__[1])
    self.assertNotIn('synthetic', '\n'.join(error.__notes__))

  def test_known_directories(self):
    for root in (tempfile.gettempdir(), os.getcwd(), config.installed_path()):
      with self.subTest(root=root):
        path = os.path.join(str(root), 'detail.curry')
        report = 'Bad.curry:1:1 Error: bad\n    See ' + path + '\n'
        notes = self.check_notes(curry.CompileError(report))
        self.assertIn('See detail.curry', notes)
    with tempfile.TemporaryDirectory(dir='.') as directory:
      Path(directory, 'Bad285.curry').write_text('module Bad285 where\nf = True + 1\n')
      with self.assertRaises(curry.CompileError) as caught:
        curry.import_('Bad285', path=[os.path.abspath(directory)])
      self.check_notes(caught.exception)

  def test_repl(self):
    with tempfile.TemporaryDirectory() as directory:
      Path(directory, 'Bad.curry').write_text('module Bad where\nf :: Int -> Int\nf x = x ++ [1]\n')
      result = subprocess.run([sys.executable, '-m', 'curry.tools.repl'],
          input=':load Bad\n1 + True\n:quit\n', cwd=directory,
          text=True, capture_output=True, timeout=120)
    self.assertEqual(result.returncode, 1)
    self.assertIn('ERROR: Bad.curry:', result.stderr)
    self.assertIn('Inferred type', result.stderr)
    self.assertIn('Expected type', result.stderr)
    self.assertIn('Missing instance', result.stderr)


if __name__ == '__main__':
  unittest.main()
