'''The public module and session operations.'''

from .. import backends, config, exceptions
from ..objects import CurryPackage
from ..objects.handle import getHandle
from ..objects.terms import check_live, check_module, ModuleInfo, Term
from . import flags as flagmod
import base64, os, shutil, sys, tempfile, weakref
from collections.abc import Mapping
from types import MappingProxyType


class Modules(Mapping):
  '''A live view of the modules, without their packages.'''
  def __init__(self, interp):
    self.interp = interp

  def __iter__(self):
    return (name for name, module in self.interp.modules.items()
        if not isinstance(module, CurryPackage))

  def __len__(self):
    return sum(1 for _ in self)

  def __getitem__(self, name):
    module = self.interp.modules[name]
    if isinstance(module, CurryPackage):
      raise KeyError(name)
    return module


def import_(interp, name, *, path=None):
  isfile = isinstance(name, os.PathLike)
  name = os.fspath(name)
  isfile = isfile or name.endswith(('.curry', '.lcurry')) or os.sep in name \
      or bool(os.altsep and os.altsep in name)
  if isfile and not name.endswith('.curry'):
    modulename = os.path.splitext(os.path.basename(name))[0]
    if modulename in interp.modules:
      from .import_ import warn_edited
      module = interp.modules[modulename]
      warn_edited(module)
      return module
    try:
      text = _source_text(name)
    except OSError as error:
      raise exceptions.ModuleLookupError('%s; searched curry.path' % error) from None
    previous = list(interp.path)
    try:
      interp.path = [os.path.dirname(os.path.abspath(name))] + list(
          previous if path is None else path)
      module = compile(interp, text, name=modulename)
    finally:
      interp.path = previous
    setattr(module, '.source_file', os.path.abspath(name))
    from .import_ import record_source
    record_source(module)
    return module
  try:
    return interp.import_(name, currypath=path, is_sourcefile=isfile)
  except exceptions.ModuleLookupError as error:
    raise exceptions.ModuleLookupError('%s; searched curry.path' % error) from None


def _source_text(name):
  with open(name, encoding='utf-8') as stream:
    if not name.endswith('.lcurry'):
      return stream.read()
    lines, code = [], False
    for line in stream:
      if line.strip() == r'\begin{code}':
        code = True
        lines.append('')
      elif line.strip() == r'\end{code}':
        code = False
        lines.append('')
      else:
        lines.append(line if code else line[1:] if line.startswith('>') else '')
    return '\n'.join(lines)


def compile(interp, source, *, name=None, imports=()):
  imports = tuple(imports)
  module = interp.compile(source, imports=imports, modulename=name)
  setattr(module, '.compile_imports', imports)
  return module


def wait(interp, module=None):
  if module is not None:
    check_module(module)
  if interp.flags['backend'] == 'cxx' and interp.flags['interpret'] == 'tiered':
    from ..backends.cxx import tiered
    if module is None:
      tiered.wait(interp=interp)
    else:
      tiered.wait_for(module.__name__, interp=interp)


def reset(interp, **flags):
  settings = flagmod.get_default_flags() if flags else dict(interp.flags)
  if flags:
    settings['backend'] = interp.flags['backend']
    settings.update(flagmod.getflags(flags))
  flagmod.check_flags(settings)
  interp.reset(flags=settings)
  interp.import_('Prelude')
  # Python keeps the parent attributes as well as the import cache.
  prefix = config.python_package_name() + '.lib'
  for name in list(sys.modules):
    if name == prefix or name.startswith(prefix + '.'):
      module = sys.modules.pop(name)
      if name == prefix:
        for key, value in list(vars(module).items()):
          from ..objects import CurryModule
          if isinstance(value, CurryModule):
            delattr(module, key)
  package = sys.modules.get(config.python_package_name())
  if package is not None:
    package.__dict__.pop('lib', None)


def reload(interp, module, *, text=None):
  check_module(module)
  source = getattr(module, '.source_file', None) or ModuleInfo(module).file
  if text is None and source is None:
    raise exceptions.LoadError('cannot reload text module %r without text; use curry.reload(module, text=...)' % module.__name__)
  if source is not None and interp.flags['backend'] == 'cxx' \
      and interp.flags['interpret'] in ('tiered', 'off'):
    raise exceptions.LoadError(
        "cannot reload %r on backend 'cxx'; use curry.reset(interpret='new') "
        'or a new process' % source)
  imports = getattr(module, '.compile_imports', ())
  from .compile import _module_source, getImportSpecForExpr
  from .. import toolchain
  from ..toolchain import plans
  stmts, currypath = getImportSpecForExpr(interp, imports)
  if text is None:
    try:
      replacement = _source_text(source)
    except OSError as error:
      raise exceptions.LoadError('cannot reload %r on backend %r: %s' %
          (source, interp.flags['backend'], error)) from None
    currypath.insert(0, os.path.dirname(os.path.abspath(source)))
  else:
    replacement = text
  replacement = _module_source(replacement, module.__name__, stmts)
  # A frontend refusal must not retire the still usable runtime tables.
  with tempfile.TemporaryDirectory(prefix='sprite-reload-') as work:
    filename = os.path.join(work, module.__name__.replace('.', os.sep) + '.curry')
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, 'w', encoding='utf-8') as stream:
      stream.write(replacement)
    plan = plans.makeplan(flags=plans.MAKE_ICURRY | plans.MAKE_JSON)
    toolchain.makecurry(plan, filename, currypath, is_sourcefile=True)
  wait(interp)
  name = module.__name__
  old = dict(module.__dict__)
  getHandle(module).unlink(interp, keep_package=True)
  interp.sigtable.clear()
  try:
    fresh = import_(interp, source) if text is None else compile(interp, text, name=name, imports=imports)
  except Exception:
    module.__dict__.clear()
    module.__dict__.update(old)
    interp.modules[name] = module
    raise
  module.__dict__.clear()
  module.__dict__.update(fresh.__dict__)
  setattr(module, '.info', ModuleInfo(module))
  for symbol in getattr(module, '.symbols').values():
    symbol._module = weakref.ref(module)
  from ..objects.classes import build_classes
  build_classes(interp, module)
  # Materializers hold references to the module they built.
  setattr(module, '.replacement', fresh)
  interp.modules[name] = module
  parent, _, local = name.rpartition('.')
  if parent:
    setattr(interp.modules[parent], local, module)
  return module


def save(interp, module, path, *, main=None):
  check_module(module)
  path = os.fspath(path)
  backend = interp.flags['backend']
  wait(interp)
  goal = main
  if isinstance(main, Term):
    check_live(main)
    goal = main.symbol.name
  scheme = None
  if main is not None:
    from .loadsave import goal_scheme_text
    scheme = goal_scheme_text(interp, getHandle(module).getsymbol(goal))
  try:
    with tempfile.TemporaryDirectory(prefix='sprite-save-') as work:
      directory = os.path.join(work, '.curry', config.intermediate_subdir())
      os.makedirs(directory)
      product = os.path.join(directory, module.__name__ + ('.so' if backend == 'cxx' else '.py'))
      if backend == 'py':
        interp.save(module, product, module_main=False, interfaces=True)
      else:
        from ..backends.cxx import toolchain
        cpp = os.path.join(directory, module.__name__ + '.cpp')
        interp.save(module, cpp, module_main=False, interfaces=True)
        product = toolchain.Cpp2So(interp)(cpp, interp.path)
      if main is None:
        shutil.copyfile(product, path)
      else:
        with open(product, 'rb') as stream:
          data = base64.b64encode(stream.read()).decode('ascii')
        program = '''#!%s
import base64, os, tempfile
import curry
curry.reset(backend=%r)
with tempfile.TemporaryDirectory(prefix='sprite-program-') as work:
  path = os.path.join(work, %r)
  with open(path, 'wb') as stream:
    stream.write(base64.b64decode(%r))
  module = curry.load(path)
  from curry.__main__ import moduleMain
  moduleMain(__file__, module.__name__, goal=%r, goalscheme=%r)
''' % (sys.executable, backend, os.path.basename(product), data, goal, scheme)
        with open(path, 'w', encoding='utf-8') as stream:
          stream.write(program)
        os.chmod(path, os.stat(path).st_mode | 0o111)
  except (OSError, exceptions.CurryError) as error:
    raise exceptions.LoadError('cannot save %r on backend %r: %s' % (path, backend, error)) from None


def load(interp, path):
  path = os.path.abspath(os.fspath(path))
  backend = interp.flags['backend']
  try:
    for module in interp.modules.values():
      loaded = getattr(module, '.load_path', None) or getHandle(module).sofilename
      if loaded is not None and os.path.realpath(loaded) == os.path.realpath(path):
        return module
    if backend == 'cxx':
      from ..backends.cxx.loader import _dynamic_names
      name, _ = _dynamic_names(path)
      if name is None:
        raise ValueError('no Curry module record')
    else:
      import ast
      with open(path, encoding='utf-8') as stream:
        tree = ast.parse(stream.read())
      # Read the module record without executing an arbitrary Python file.
      name = None
      for node in ast.walk(tree):
        if isinstance(node, ast.keyword) and node.arg == 'fullname' \
            and isinstance(node.value, ast.Constant):
          name = node.value.value
      if name is None:
        raise ValueError('no Curry module record')
    if name in interp.modules:
      module = interp.modules[name]
      loaded = getattr(module, '.load_path', None) or getHandle(module).sofilename
      if loaded is not None and os.path.realpath(loaded) == os.path.realpath(path):
        return module
      raise ValueError('module %r is already loaded from another file' % name)
    # Internal loaders require their backend suffix; save accepts any suffix.
    suffix = interp.backend.object_file_extension
    if path.endswith(suffix):
      module = interp.load(path, **({'fresh': True} if backend == 'cxx' else {}))
    else:
      with tempfile.TemporaryDirectory(prefix='sprite-load-') as work:
        copy = os.path.join(work, name + suffix)
        shutil.copyfile(path, copy)
        module = interp.load(copy, **({'fresh': True} if backend == 'cxx' else {}))
    setattr(module, '.load_path', path)
    metadata = getHandle(module).icurry.metadata
    if metadata.get('all.fint'):
      directory = tempfile.TemporaryDirectory(prefix='sprite-interfaces-')
      for suffix, key in (('.fint', 'all.fint'), ('.icurry', 'all.interface')):
        with open(os.path.join(directory.name, name + suffix), 'w', encoding='utf-8') as stream:
          stream.write(metadata.get(key, ''))
      setattr(module, '.interfaces', directory)
      setattr(module, '.interface_file', os.path.join(directory.name, name + '.fint'))
    return module
  except Exception as error:
    if isinstance(error, exceptions.StaleError):
      raise
    raise exceptions.LoadError('cannot load %r on backend %r: %s' % (path, backend, error)) from None
