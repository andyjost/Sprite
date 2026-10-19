'''
Implements Interpreter.compile.
'''

from .. import config, exceptions, objects, toolchain
from ..objects import handle
from ..typecheck import goals, sigtable
from ..utility.visitation import dispatch
import itertools, os, re, tempfile, types, weakref, threading

__all__ = ['compile', 'expression_scheme']

COMPILED_NAME = 'compiled_expression'

# Numbers anonymous module and expression compilations. The counter belongs
# to the process, not to the interpreter, so a name never repeats after reset() or reload().  The C++
# backend resolves a module's symbols against the same-named module loaded
# first, so a reused name could resolve to stale code.  See
# config.expression_modname.
_module_counter = itertools.count()
_counter_lock = threading.Lock()

def _next_module():
  with _counter_lock:
    return next(_module_counter)

def compile(interp, string, imports=None, modulename=None):
  """Compile Curry source as a module, optionally naming it and its imports."""
  stmts, currypath = getImportSpecForExpr(interp, [] if imports is None else imports)
  header = re.search(r'^\s*module\s+([\w.]+)\b', string, re.M)
  generated = modulename is None and header is None
  if modulename is None:
    modulename = header.group(1) if header else config.interactive_modname() + str(_next_module())
  if generated:
    while modulename in interp.modules:
      modulename = config.interactive_modname() + str(_next_module())
  if modulename in interp.modules:
    raise exceptions.ModuleExistsError(
        "module %r is loaded; curry.reload(curry.modules[%r], text=...) replaces its code"
        % (modulename, modulename))
  string = _module_source(string, modulename, stmts)
  moduleobj, icur = toolchain.str2module(
      interp, string, currypath
    , modulename=modulename
    , keep_temp_files=interp.flags['keep_temp_files']
    , postmortem=interp.flags['postmortem']
    )
  try:
    return moduleobj
  finally:
    if icur.name == config.interactive_modname() \
        and icur.name in interp.modules:
      del interp.modules[icur.name]

def _module_source(string, modulename, stmts):
  header = re.search(r'^\s*module\s+([\w.]+)\b', string, re.M)
  if header:
    string = string[:header.start(1)] + modulename + string[header.end(1):]
    start = header.start(1) + len(modulename)
    where = re.search(r'\bwhere\b', string[start:])
    if where is None:
      return string
    end = where.end() + start
    return string[:end] + '\n' + '\n'.join(stmts) + string[end:]
  if '.' in modulename:
    stmts = ['module %s where' % modulename] + list(stmts)
  return '%s\n%s' % ('\n'.join(stmts), string)


def compile_expression(
    interp, string, stmts, currypath, exprtype=None, lift_freevars=True
  ):
  '''
  Compiles a Curry expression into a module of its own, as the binding
  ``compiled_expression = <string>``.  With ``lift_freevars``, the variables
  of a trailing ``where x, y free`` become parameters of the binding, as
  the REPL of PAKCS does; with ``exprtype`` the text is compiled as written
  under the signature. Returns the symbol of the binding, the names of the
  lifted variables, and the module.
  '''
  freevars = []
  if lift_freevars and not exprtype:
    string, freevars = goals.split_where_free(string)
  stmts = list(stmts)
  if exprtype:
    stmts += ['%s :: %s' % (COMPILED_NAME, exprtype)]
  stmts += ['%s%s = %s' % (COMPILED_NAME, ''.join(' ' + v for v in freevars), string)]
  curry_code = '\n'.join(stmts)
  moduleobj, icur = toolchain.str2module(
      interp, curry_code, currypath
    , modulename=config.expression_modname(_next_module())
    , keep_temp_files=interp.flags['keep_temp_files']
    , postmortem=interp.flags['postmortem']
    )
  # The step functions of the module are compiled now, while the module is
  # in the registry, where the compiled code resolves the symbols of the
  # module by name (a lifted lambda, a derived instance method).
  interp.backend.compile_pending(moduleobj)
  # The module leaves the registry, but it stays loaded until the
  # interpreter resets: the goal's graph refers to the module's code and
  # data (string literals, local functions), and nothing in the goal keeps
  # the module alive.  On the C++ backend, an unloaded module leaves
  # dangling pointers in any goal compiled from it.  The name is unique for
  # the process, so the modules cannot clash.
  with interp._state_lock:
    interp.modules.pop(icur.name, None)
    interp._expression_modules.append(moduleobj)
  return getattr(moduleobj, '.symbols')[COMPILED_NAME], freevars, moduleobj

def expression_scheme(interp, string, imports=None):
  '''
  The type scheme of a Curry expression, as the front end infers it for the
  binding ``compiled_expression = <string>``, before any defaulting; what
  ``:type`` prints in the REPL.  A trailing ``where x free`` stays a local
  declaration, as in the ``:type`` of PAKCS.
  '''
  stmts, currypath = getImportSpecForExpr(
      interp, [] if imports is None else imports
    )
  func, _, _ = compile_expression(
      interp, string, stmts, currypath, lift_freevars=False
    )
  return interp.sigtable.lookup(func, required=True)

def getImportSpecForExpr(interp, modules):
  '''
  Generates the import statements and the CURRYPATH to use when compiling a
  standalone Curry expression.

  Args:
    interp:
        The interpreter.
    modules:
        The list of modules to import.  Each one may be a string or a Curry
        module object.  Instead of a list, a module object may be passed.

  Returns:
    A pair consisting of a list of Curry import statements and the updated
    search path.
  '''
  stmts = []
  currypath = list(interp.path)
  if isinstance(modules, objects.CurryModule):
    modules = [modules]
  for module in modules:
    _updateImports(interp, module, stmts, currypath)
  return stmts, currypath

@dispatch.on('module')
def _updateImports(interp, module, stmts, currypath):
  assert False

@_updateImports.when(str)
def _updateImports(interp, modulename, stmts, currypath):
  try:
    module = interp.modules[modulename]
  except KeyError:
    module = interp.import_(modulename)
  return _updateImports(interp, module, stmts, currypath)

@_updateImports.when(types.ModuleType)
def _updateImports(interp, module, stmts, currypath):
  if isinstance(module, objects.CurryModule):
    from ..objects.terms import check_module
    check_module(module)
  if module.__name__ != '_System':
    stmts.append('import ' + module.__name__)
    # If this is a dynamic module, add its directory to the search path.
    h = handle.Handle(module)
    tmpd = h.icurry.metadata.get('all.tmpd', None)
    if not h.is_package and h.icurry.filename:
      # A module loaded from a file outside the search path, e.g., by the
      # :load command of the REPL: the front end must find its source.
      root = sigtable.module_root(
          os.path.dirname(os.path.abspath(h.icurry.filename)), h.fullname
        )
      if root not in currypath:
        currypath.insert(0, root)

    if tmpd is None and not h.is_package:
      from .import_ import edited_source
      if edited_source(module) is not None:
        text = getattr(h.icurry, '_source_text', None)
        if text is not None:
          snapshot = getattr(h.icurry, '_frontend_snapshot', None)
          if snapshot is None:
            snapshot = tempfile.TemporaryDirectory(prefix='sprite-scope-')
            filename = os.path.join(snapshot.name, h.fullname.replace('.', os.sep) + '.curry')
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            with open(filename, 'w', encoding='utf-8') as stream:
              stream.write(text)
            h.icurry._frontend_snapshot = snapshot
            weakref.finalize(h.icurry, snapshot.cleanup)
          tmpd = snapshot.name
    if tmpd is not None:
      # The front end sees the code the loaded scope belongs to.
      currypath.insert(0, tmpd)
