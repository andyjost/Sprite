"""Reduced generators used by EasyCheck's quantified property runner."""
import cytest # from ./lib; must be first
from curry import config
from pathlib import Path
import os
import json
import shutil
import subprocess
import tempfile
import unittest


class TestCPMSearch(cytest.TestCase):
  @unittest.skipUnless(os.environ.get('SPRITE_CPM_INDEX_CHECKER'),
                       'the prepared CPM index framework is absent')
  @unittest.expectedFailure
  def test_functional_tree_pattern_property(self):
    checker = Path(os.environ['SPRITE_CPM_INDEX_CHECKER']).resolve()
    home = checker.parent
    cypm = Path(config.installed_path('tools', 'pakcs')).resolve().with_name('cypm')
    with tempfile.TemporaryDirectory(dir=home, prefix='index-pattern-') as directory:
      project = Path(directory)
      (project / 'package.json').write_text(json.dumps({
          'name': 'sprite-index-pattern-test', 'version': '0.0.1',
          'author': 'Sprite', 'synopsis': 'Functional pattern regression test',
          'dependencies': {'base': '= 3.4.0'},
          'testsuite': {'src-dir': '.', 'modules': ['PatternProperty']}}))
      (project / 'PatternProperty.curry').write_text('''module PatternProperty where
import Test.Prop
data Tree = Text String | Elem String [(String,String)] [Tree] deriving (Eq,Ord,Show)
xml :: String -> [Tree] -> Tree
xml tag children = Elem tag [] children
xtxt :: String -> Tree
xtxt = Text
with :: Data a => [a] -> [a]
with [] = unknown
with (x:xs) = unknown ++ x : with xs
match :: Tree -> String
match (xml "entry" (with [xml "name" [xtxt name], xml "phone" [xtxt phone]])) = name ++ ":" ++ phone
property :: Prop
property = match (xml "entry" [xml "name" [xtxt "a"], xml "other" [xtxt "unused"], xml "phone" [xtxt "b"]]) -=- "a:b"
''')
      result = subprocess.run([str(cypm), '-d',
          'CURRYBIN=' + config.installed_path('bin', 'sprite'), '-d',
          'REPOSITORYPATH=' + str(home / 'sprite-index'), 'test'], cwd=project,
          env=dict(os.environ, HOME=str(home),
                   PATH=str(checker) + os.pathsep + os.environ['PATH']),
          capture_output=True, text=True, timeout=180)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

  @unittest.skipUnless(os.environ.get('SPRITE_CPM_INDEX_CHECKER'),
                       'the prepared CPM index framework is absent')
  def test_quantified_properties_use_sprite(self):
    checker = Path(os.environ['SPRITE_CPM_INDEX_CHECKER']).resolve()
    home = checker.parent
    candidate = Path(config.installed_path('tools', 'pakcs')).resolve().parent / 'cypm'
    cypm = str(candidate) if candidate.is_file() else shutil.which('cypm')
    self.assertTrue(cypm, 'cypm is required by the prepared framework')
    with tempfile.TemporaryDirectory(dir=home, prefix='index-generator-') as directory:
      project = Path(directory)
      (project / 'package.json').write_text(json.dumps({
          'name': 'sprite-index-generator-test', 'version': '0.0.1',
          'author': 'Sprite', 'synopsis': 'Quantified property regression test',
          'dependencies': {'base': '= 3.4.0'},
          'testsuite': {'src-dir': '.', 'modules': ['GeneratorProperties'],
                        'options': '-m10'}}))
      (project / 'GeneratorProperties.curry').write_text('''
module GeneratorProperties where
import Test.Prop
import Curry.Compiler.Distribution (curryCompiler)
roundTrip :: Int -> Prop
roundTrip n = (n + 1) - 1 -=- n
booleanIdentity :: Bool -> Prop
booleanIdentity b = not (not b) -=- b
pairIdentity :: (Bool,Bool) -> Prop
pairIdentity pair = pair -=- pair
compilerIsSprite :: Prop
compilerIsSprite = curryCompiler -=- "sprite"
''')
      environment = dict(os.environ, HOME=str(home),
                         PATH=str(checker) + os.pathsep + os.environ['PATH'])
      result = subprocess.run([cypm, '-d',
          'CURRYBIN=' + config.installed_path('bin', 'sprite'), '-d',
          'REPOSITORYPATH=' + str(home / 'sprite-index'), 'test'], cwd=project,
          env=environment, capture_output=True, text=True, timeout=180)
      output = result.stdout + result.stderr
      self.assertEqual(result.returncode, 0, output)
      self.assertIn('TOTAL NUMBER OF TESTS: 4', output)
      self.assertNotIn('No tests, just compiling', output)

  @unittest.expectedFailure
  def test_deterministic_search_inside_io(self):
    import curry
    module = curry.compile('''onlyTrue True = True
value :: Bool
value = onlyTrue (True ? False)
goal :: IO Bool
goal = if value then return True else return False
''')
    self.assertEqual(list(curry.eval(module.value)), [True])
    self.assertTrue(curry.eval(module.goal).one())

  def test_pakcs_closed_boolean_choices(self):
    pakcs = Path(config.installed_path('tools', 'pakcs')).resolve()
    if not pakcs.is_file():
      self.skipTest('PAKCS is absent')
    with tempfile.TemporaryDirectory() as directory:
      (Path(directory) / 'ClosedGenerator.curry').write_text('''
module ClosedGenerator where
import Control.Search.Unsafe
goal :: [Bool]
goal = allValues (id $## (aValue :: Bool))
''')
      environment = dict(os.environ, HOME=directory)
      environment.pop('CURRYPATH', None)
      result = subprocess.run([str(pakcs), '--nocypm', ':set', 'v0',
          ':load', 'ClosedGenerator', ':eval', 'print goal', ':quit'],
          cwd=directory, env=environment, text=True, capture_output=True, timeout=30)
      self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
      self.assertRegex(result.stdout + result.stderr, r'\[(?:False,True|True,False)\]')

  def test_closed_boolean_choices(self):
    result = cytest.run_in_subprocess('''
import curry
module = curry.compile("""
import qualified Control.Search.Unsafe as U
import qualified Control.Search.SearchTree as S
direct :: [Bool]
direct = U.allValues (id $## (aValue :: Bool))
tree :: [Bool]
tree = S.allValuesDFS (S.someSearchTree (id $## (aValue :: Bool)))
""")
results = {}
for name in ('direct', 'tree'):
    results[name] = [curry.show(value) for value in curry.eval(module[name])]
print(results, flush=True)
for values in results.values():
    assert values in (['[False,True]'], ['[True,False]']), values
''', timeout=20, address_space=1 << 30)
    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
