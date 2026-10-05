'''
The parts of a split functional corpus.

A heavy corpus runs in several func_* files, each over a part of its
sources (FILE_PATTERN of cytest.FunctionalTestCase, tests/README section
10).  The tests here check that the parts of each split corpus cover it
exactly once, so a split cannot lose or double a program, and that the
driver takes a list of globs.
'''
import cytest # from ./lib; must be first
from cytest.testcase import functional
import glob, importlib, os, re, unittest

# The corpus directories that are split, and the test files of their parts.
PARTS = {
    'data/curry/eqconstr/': [
        'func_eqconstr', 'func_eqconstr_a0', 'func_eqconstr_a0b0c0_1'
      , 'func_eqconstr_a0b0c0_2', 'func_eqconstr_a0b0c0_3'
      , 'func_eqconstr_a2b1c0'
      ]
  , 'data/curry/math/': ['func_math', 'func_math_int', 'func_math_float']
  }

def driver_class(module):
  '''The FunctionalTestCase subclass of a test module.'''
  classes = [
      obj for obj in vars(module).values()
          if isinstance(obj, type)
         and issubclass(obj, cytest.FunctionalTestCase)
         and obj is not cytest.FunctionalTestCase
    ]
  assert len(classes) == 1, module.__name__
  return classes[0]

def test_methods(cls):
  '''The names of the test methods a driver class defines.'''
  return sorted(name for name in vars(cls) if name.startswith('test_'))

class TestFunctionalParts(cytest.TestCase):
  def test_parts_cover_each_corpus_once(self):
    for source_dir, names in PARTS.items():
      with self.subTest(corpus=source_dir):
        corpus = set(glob.glob(source_dir + '[a-z]*.curry'))
        self.assertTrue(corpus, source_dir)
        seen = {}
        for name in names:
          cls = driver_class(importlib.import_module(name))
          self.assertEqual(cls.SOURCE_DIR, source_dir, name)
          sources = functional.source_files(cls.SOURCE_DIR, cls.FILE_PATTERN)
          self.assertTrue(sources, name)
          # One test per source: the part filters nothing out.
          self.assertEqual(len(test_methods(cls)), len(sources), name)
          for source in sources:
            self.assertNotIn(
                source, seen
              , '%s is in %s and %s' % (source, seen.get(source), name)
              )
            seen[source] = name
        self.assertEqual(set(seen), corpus)

  def test_file_patterns(self):
    self.assertEqual(functional.file_patterns('a*.curry'), ('a*.curry',))
    self.assertEqual(
        functional.file_patterns(['a*.curry', 'b*.curry'])
      , ('a*.curry', 'b*.curry')
      )
    # A source that two patterns match is listed once, and the list is
    # sorted whatever the order of the patterns.
    sources = functional.source_files(
        'data/curry/math/', ['sort0[0-1].curry', 'sort*.curry']
      )
    self.assertEqual(
        sources, sorted(glob.glob('data/curry/math/sort*.curry'))
      )
    self.assertEqual(len(sources), 5)

  def test_driver_takes_a_list(self):
    # The class is local, so the loader of this file does not run it.
    class Parts(cytest.FunctionalTestCase):
      SOURCE_DIR = 'data/curry/math/'
      FILE_PATTERN = ['sort0[0-1].curry', 'sort*.curry']
    self.assertEqual(
        test_methods(Parts)
      , ['test_sort00', 'test_sort01', 'test_sort02', 'test_sort03', 'test_sort04']
      )
    class One(cytest.FunctionalTestCase):
      SOURCE_DIR = 'data/curry/math/'
      FILE_PATTERN = 'sort00.curry'
    self.assertEqual(test_methods(One), ['test_sort00'])

  def test_skip_reason_names_the_file_that_holds_the_test(self):
    '''
    unit_io_bind.py skips its rotation test on the Python backend and names
    the file that covers it there.  The split of unit_py_io.py moved that
    test; the pointer must follow it.
    '''
    with open(os.path.join(os.path.dirname(__file__), 'unit_io_bind.py')) as stream:
      text = stream.read()
    match = re.search(r"'(unit_\w+) covers the Python backend", text)
    self.assertIsNotNone(match)
    module = importlib.import_module(match.group(1))
    holders = [
        obj for obj in vars(module).values()
            if isinstance(obj, type) and issubclass(obj, unittest.TestCase)
           and hasattr(obj, 'test_writeFile_keeps_prefix_across_rotation')
      ]
    self.assertEqual(len(holders), 1, match.group(1))
