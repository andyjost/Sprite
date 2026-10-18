'''The installed stub is the public surface, on either backend.'''
import cytest # from ./lib; must be first
import ast
import builtins
from collections import abc
import inspect
from pathlib import Path
import types
import unittest
import curry


def parameters(args):
  result = [(arg.arg, inspect.Parameter.POSITIONAL_ONLY) for arg in args.posonlyargs]
  result += [(arg.arg, inspect.Parameter.POSITIONAL_OR_KEYWORD) for arg in args.args]
  if args.vararg:
    result.append((args.vararg.arg, inspect.Parameter.VAR_POSITIONAL))
  result += [(arg.arg, inspect.Parameter.KEYWORD_ONLY) for arg in args.kwonlyargs]
  if args.kwarg:
    result.append((args.kwarg.arg, inspect.Parameter.VAR_KEYWORD))
  return result


def base_class(node):
  if isinstance(node, ast.Subscript):
    node = node.value
  name = ast.unparse(node)
  # NamedTuple is a class factory; its instances derive from tuple.
  if name == 'NamedTuple':
    return tuple
  if name == 'types.ModuleType':
    return types.ModuleType
  return getattr(curry, name, None) or getattr(abc, name, None) or getattr(builtins, name)


class TestSurface(cytest.TestCase):
  @classmethod
  def setUpClass(cls):
    cls.stub = Path(curry.__file__).with_suffix('.pyi')
    cls.tree = ast.parse(cls.stub.read_text(encoding='utf-8'))
    cls.names = ast.literal_eval(next(node.value for node in cls.tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
        and target.id == '__all__' for target in node.targets)))

  def test_exports_and_documentation(self):
    self.assertIn('public', ast.get_docstring(self.tree))
    self.assertEqual(curry.__all__, self.names)
    self.assertEqual(len(self.names), len(set(self.names)))
    documented = set()
    for node in self.tree.body:
      if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
        documented.add(node.name)
        if node.name in self.names:
          with self.subTest(name=node.name):
            self.assertTrue(ast.get_docstring(node))
      elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        documented.add(node.target.id)
    self.assertLessEqual(set(self.names), documented)
    for name in dir(curry):
      if not name.startswith('_'):
        with self.subTest(name=name):
          value = getattr(curry, name)
          self.assertTrue(name in self.names or isinstance(value, types.ModuleType)
              and value.__name__.startswith(curry.__name__ + '.'))
    for name in self.names:
      self.assertTrue(hasattr(curry, name), name)

  def check_function(self, node, value):
    self.assertEqual(parameters(node.args),
        [(p.name, p.kind) for p in inspect.signature(value).parameters.values()])

  def test_functions_and_methods(self):
    for node in self.tree.body:
      if not isinstance(node, (ast.FunctionDef, ast.ClassDef)) or node.name not in self.names:
        continue
      if isinstance(node, ast.FunctionDef):
        with self.subTest(name=node.name):
          self.check_function(node, getattr(curry, node.name))
      else:
        cls = getattr(curry, node.name)
        for method in node.body:
          if isinstance(method, ast.FunctionDef):
            with self.subTest(name=node.name, method=method.name):
              self.check_function(method, getattr(cls, method.name))

  def test_class_bases(self):
    for node in self.tree.body:
      if isinstance(node, ast.ClassDef) and node.name in self.names:
        with self.subTest(name=node.name):
          cls = getattr(curry, node.name)
          self.assertTrue(inspect.isclass(cls))
          self.assertEqual(cls.__bases__, tuple(map(base_class, node.bases)) or (object,))

  def test_removed_options_are_rejected(self):
    for keyword in ('mode', 'exprtype'):
      with self.subTest(keyword=keyword), self.assertRaises(TypeError):
        curry.compile('x = 1', **{keyword: 'expr'})
    with self.assertRaises(TypeError):
      curry.eval(1, **{'converter': None})
    for flag in ('default' + 'converter', 'typed' + '_expr'):
      self.assertNotIn(flag, curry.flags)

  def test_session_signatures(self):
    for name in ('import_', 'compile', 'reload', 'save', 'load', 'wait'):
      self.assertIn(name, self.names)
    self.assertEqual(list(inspect.signature(curry.wait).parameters), ['module'])
    self.assertEqual(list(inspect.signature(curry.reset).parameters), ['flags'])

  def test_constructor_class_surface(self):
    for name in ('DataClass', 'ConstructorClass'):
      self.assertIn(name, self.names)
    self.assertEqual(curry.DataClass.__bases__, (curry.Data,))
    self.assertEqual(curry.ConstructorClass.__bases__, (curry.DataClass,))

  def test_stream_surface(self):
    self.assertIn('stream', self.names)
    self.assertIn('Stream', self.names)
    self.assertEqual(list(inspect.signature(curry.stream).parameters), ['action'])
    self.assertEqual(curry.Stream.__bases__, (abc.Iterator,))

  def test_internal_node_evaluation(self):
    from curry import backends
    self.assertIsInstance(cytest.raw.values(curry.term(1)).one(), backends.Node)
    self.assertEqual(curry.eval(curry.term(1)).one(), 1)


if __name__ == '__main__':
  unittest.main()
