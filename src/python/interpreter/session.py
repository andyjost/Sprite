'''The public module and session operations.'''

from .. import backends, config, exceptions
from ..objects import CurryPackage
from ..objects.handle import getHandle
from ..objects.terms import check_live, check_module, ModuleInfo, Term
from . import flags as flagmod
import base64, os, re, shutil, sys, tempfile, weakref
from collections.abc import Mapping
from types import MappingProxyType


class Flags(Mapping):
  """A live read-only view of settings published by reset."""
  def __init__(self, interp):
    self.interp = interp
  def __getitem__(self, key): return self.interp.flags[key]
  def __iter__(self): return iter(self.interp.flags.copy())
  def __len__(self): return len(self.interp.flags)


class Modules(Mapping):
  '''A live view of the modules, without their packages.'''
  def __init__(self, interp):
    self.interp = interp

  def __iter__(self):
    return (name for name, module in self.interp.modules.copy().items()
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
    try:
      text = _source_text(name)
    except OSError as error:
      raise exceptions.ModuleLookupError('%s; searched curry.path' % error) from None
    from ..toolchain import _filenames, _findcurry
    tokens = iter(_filenames._header_tokens(text))
    modulename = os.path.splitext(os.path.basename(name))[0]
    for token in tokens:
      if token == 'module':
        modulename = next(tokens, modulename)
        break
    _findcurry.reject_library_shadow(modulename, name, interp)
    if modulename in interp.modules:
      from .import_ import warn_edited, warn_other_file
      module = interp.modules[modulename]
      warn_edited(module)
      source = getattr(module, '.source_file', None)
      if source is None or os.path.realpath(source) != os.path.realpath(name):
        warn_other_file(module, name)
      return module
    search = [os.path.dirname(os.path.abspath(name))] + list(
        interp.path if path is None else path)
    with interp._using_path(search):
      module = compile(interp, text, name=modulename)
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
  from ..backends.cxx import tiered
  if tiered.enabled(interp):
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
  # Python owns publication of a hook result until exec_module completes.
  # Wait for each tracked name without holding the heap or a Sprite lock.
  from importlib._bootstrap import _get_module_lock
  from ..utility.locking import lib_import_lock, lib_import_names
  prefix = config.python_package_name() + '.lib'
  with lib_import_lock:
    names = set(lib_import_names)
  names.update(name for name in sys.modules.copy()
      if name == prefix or name.startswith(prefix + '.'))
  for name in sorted(names, reverse=True):
    mutex = _get_module_lock(name)
    mutex.acquire()
    try:
      module = sys.modules.pop(name, None)
      if name == prefix and module is not None:
        for key, value in vars(module).copy().items():
          from ..objects import CurryModule
          if isinstance(value, CurryModule):
            delattr(module, key)
    finally:
      mutex.release()
  package = sys.modules.get(config.python_package_name())
  if package is not None:
    package.__dict__.pop('lib', None)


def reload(interp, module, *, text=None):
  check_module(module)
  _check_reload_owner(interp, module)
  source = getattr(module, '.source_file', None) or ModuleInfo(module).file
  if text is None and source is None:
    raise exceptions.LoadError('cannot reload text module %r without text; use curry.reload(module, text=...)' % module.__name__)
  if source is not None \
      and interp.flags['interpret'] == 'off':
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
    plan = plans.makeplan(flags=plans.MAKE_ICURRY)
    toolchain.makecurry(plan, filename, currypath, is_sourcefile=True)
  wait(interp)
  from ..utility.locking import native_metadata
  return native_metadata(_replace_module)(interp, module, source, text, imports)


def _check_reload_owner(interp, module):
  if getattr(getHandle(module).obj, '.interp') is not interp:
    raise exceptions.StaleError('module %s belongs to another interpreter' % module.__name__)


def _replace_module(interp, module, source, text, imports):
  check_module(module)
  _check_reload_owner(interp, module)
  name = module.__name__
  old = module.__dict__.copy()
  from ..backends.cxx import llvmjit
  llvmjit.invalidate(interp._its)
  llvmjit.refresh(interp._its, name)
  getHandle(module).unlink(interp, keep_package=True)
  interp.sigtable.clear()
  try:
    # Only the final module is published, after its wrappers/classes refer
    # to the original Python module object (reload preserves its identity).
    registry = interp.modules
    with interp._private_modules():
      fresh = import_(interp, source) if text is None else compile(interp, text, name=name, imports=imports)
      dependencies = interp.modules.copy()
    registry.update((key, value) for key, value in dependencies.items() if key != name)
    metadata = getattr(fresh, '.info')
    metadata._module = module
    for symbol in metadata._symbols.values():
      symbol.module = module
    for datatype in metadata._types.values():
      datatype.module = module
    for symbol in getattr(fresh, '.symbols').values():
      symbol._module = weakref.ref(module)
    replacement = fresh.__dict__.copy()
    replacement['.replacement'] = fresh # keep materializers' owner alive
  except Exception:
    module.__dict__.update(old)
    if '.retired' not in old:
      module.__dict__.pop('.retired', None)
    interp.modules[name] = module
    raise
  # Never clear the module's mandatory metadata slots: concurrent checks
  # see an old/new complete view or a retired module, never absent fields.
  module.__dict__.update(replacement)
  for key in old.keys() - replacement.keys():
    if key != '.retired':
      module.__dict__.pop(key, None)
  module.__dict__.pop('.retired', None)
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
      from ..backends.cxx import toolchain
      objects = {}
      class SavedCpp2So(toolchain.Cpp2So):
        def _sofilename(self, name, currypath=None):
          if name in objects:
            return objects[name]
          return super()._sofilename(name, currypath)

      def compile_module(current):
        cpp = os.path.join(directory, current.__name__ + '.cpp')
        interp.save(current, cpp, module_main=False, interfaces=True)
        product = SavedCpp2So(interp)(cpp, interp.path)
        objects[current.__name__] = product
        return product

      if main is None:
        shutil.copyfile(compile_module(module), path)
      else:
        # Keep imports before their users: the dynamic linker needs their
        # SONAMEs mapped before it opens an object that refers to them.
        products = []
        visited = set()
        def collect(current):
          name = current.__name__
          if name in visited:
            return
          visited.add(name)
          from ..toolchain._findcurry import _installed_library_file
          source = getHandle(current).icurry.filename
          for dependency in getHandle(current).icurry.imports:
            collect(interp.import_(dependency))
          if name != module.__name__ and source and _installed_library_file(source):
            step = SavedCpp2So(interp)
            product = step._object_on_disk(name, interp.path)
            if product is not None and not step.import_lacks_an_object(product, interp.path):
              return
          product = compile_module(current)
          with open(product, 'rb') as stream:
            data = base64.b64encode(stream.read()).decode('ascii')
          products.append((os.path.basename(product), data))
        # A library module can itself be the requested main module.
        visited.discard(module.__name__)
        collect(module)
        program = '''#!%s
import base64, os, tempfile
import curry
from curry.interpreter.session import _load_saved
curry.reset(backend=%r)
with tempfile.TemporaryDirectory(prefix='sprite-program-') as work:
  for filename, data in %r:
    path = os.path.join(work, filename)
    with open(path, 'wb') as stream:
      stream.write(base64.b64decode(data))
    module = _load_saved(curry._interpreter_, path)
  from curry.__main__ import moduleMain
  moduleMain(__file__, module.__name__, goal=%r, goalscheme=%r)
''' % (sys.executable, backend, products, goal, scheme)
        if sys.platform == 'win32':
          _save_windows_program(interp, path, program, work)
        else:
          with open(path, 'w', encoding='utf-8') as stream:
            stream.write(program)
          os.chmod(path, os.stat(path).st_mode | 0o111)
  except (OSError, exceptions.CurryError) as error:
    raise exceptions.LoadError('cannot save %r on backend %r: %s' % (path, backend, error)) from None


def _save_windows_program(interp, path, program, work):
  # Keep the Python goal/defaulting protocol shared with POSIX. The native
  # launcher owns the temporary directory so mapped DLLs are removed only
  # after the Python child has exited.
  import json
  from ..backends.cxx import toolchain, msvc
  from ..toolchain import _system
  program = program[program.index('import base64'):]
  program = program.replace("with tempfile.TemporaryDirectory(prefix='sprite-program-') as work:",
                            "if True:\n  work = os.path.dirname(__file__)")
  source = os.path.join(work, 'launcher.cpp')
  text = r'''#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <process.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <cerrno>
#include <cstdio>
#include <cstring>
std::wstring quote(wchar_t const * value)
{
  std::wstring result = L"\"";
  size_t slashes = 0;
  for(wchar_t c: std::wstring(value))
  {
    if(c == L'\\') { ++slashes; continue; }
    result.append(c == L'"' ? 2 * slashes + 1 : slashes, L'\\');
    result += c;
    slashes = 0;
  }
  result.append(2 * slashes, L'\\');
  return result + L'"';
}
int wmain(int argc, wchar_t ** argv)
{
  auto pid = GetCurrentProcessId();
  wchar_t temp[MAX_PATH + 1];
  if(!GetTempPathW(MAX_PATH, temp)) return 1;
  auto directory = std::filesystem::path(temp) /
      (L"sprite-program-" + std::to_wstring(pid) + L"-" + std::to_wstring(GetTickCount64()));
  std::error_code error;
  if(!std::filesystem::create_directory(directory, error))
  {
    std::fprintf(stderr, "cannot create temporary directory: %s\n", error.message().c_str());
    return 127;
  }
  auto script = directory / std::filesystem::path(argv[0]).filename();
  { std::ofstream out(script, std::ios::binary); out << SCRIPT; }
  std::vector<std::wstring> quoted{quote(script.c_str())};
  for(int i = 1; i < argc; ++i) quoted.push_back(quote(argv[i]));
  std::filesystem::path python = PYTHON;
  if(!std::filesystem::is_regular_file(python, error)) python = L"python";
  auto executable = quote(python.c_str());
  std::vector<wchar_t const *> args{executable.c_str()};
  for(auto const & argument: quoted) args.push_back(argument.c_str());
  args.push_back(nullptr);
  auto status = python == L"python"
      ? _wspawnvp(_P_WAIT, python.c_str(), args.data())
      : _wspawnv(_P_WAIT, python.c_str(), args.data());
  if(status < 0)
    std::fprintf(stderr, "cannot run %s: %s\n", python.u8string().c_str(), std::strerror(errno));
  std::error_code ignored;
  std::filesystem::remove_all(directory, ignored);
  return status < 0 ? 127 : static_cast<int>(status);
}
'''
  with open(source, 'w', encoding='ascii') as stream:
    replacements = {
        'PYTHON': 'L' + json.dumps(sys.executable, ensure_ascii=True),
        'SCRIPT': json.dumps(program, ensure_ascii=True)
      }
    stream.write(re.sub(r'\b(PYTHON|SCRIPT)\b',
                        lambda match: replacements[match.group()], text))
  step = toolchain.Cpp2So(interp)
  command = list(step._compileCommand(source, path))
  command.remove('/LD')
  command = [arg for arg in command if not arg.startswith('/IMPLIB:')
             and arg != config.installed_path('lib', 'libcurryrt.lib')]
  try:
    _system.pexec(command, env=msvc.environment())
  finally:
    for suffix in ('.obj', '.pdb', '.lib', '.exp'):
      try:
        os.unlink(path + suffix)
      except FileNotFoundError:
        pass


def load(interp, path):
  return _load_object(interp, path)


def _load_saved(interp, path):
  """Load one object from the saving session's collected payload."""
  return _load_object(interp, path, _saved_payload=True)


def _load_object(interp, path, _saved_payload=False):
  path = os.path.abspath(os.fspath(path))
  backend = interp.flags['backend']
  try:
    from ..toolchain import _findcurry
    for module in interp.modules.copy().values():
      loaded = getattr(module, '.load_path', None) or getHandle(module).sofilename
      if loaded is not None and os.path.realpath(loaded) == os.path.realpath(path):
        if not _saved_payload:
          _findcurry.reject_library_shadow(module.__name__, path, interp)
        return module
    from ..backends.cxx.loader import _dynamic_names
    name, _ = _dynamic_names(path)
    if name is None:
      raise ValueError('no Curry module record')
    if not _saved_payload:
      _findcurry.reject_library_shadow(name, path, interp)
    if name in interp.modules and not isinstance(interp.modules[name], CurryPackage):
      module = interp.modules[name]
      loaded = getattr(module, '.load_path', None) or getHandle(module).sofilename
      if loaded is not None and os.path.realpath(loaded) == os.path.realpath(path):
        return module
      raise ValueError('module %r is already loaded from another file' % name)
    # Public saves accept any suffix; the record above established the format.
    # Map the requested file directly, without a temporary DLL to delete while
    # Windows still has it mapped. Internal plan loads keep their suffix check.
    module = interp.backend.load_module(interp, path, fresh=True,
        _saved_payload=_saved_payload)
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
