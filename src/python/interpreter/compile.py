'''
Implements Interpreter.compile.
'''

from ..backends.generic.eval import evaluator
from .. import config, exceptions, icurry, inspect, objects, toolchain, utility
from ..objects import handle
from ..typecheck import defaulting, goals, sigtable
from ..utility.visitation import dispatch
import itertools, os, types

__all__ = ['compile', 'expression_scheme']

COMPILED_NAME = 'compiled_expression'

# Numbers the anonymous modules: interactive modules (mode 'module' without a
# name) and expression modules.  The counter belongs to the process, not to
# the interpreter, so a name never repeats after reset() or reload().  The C++
# backend resolves a module's symbols against the same-named module loaded
# first, so a reused name could resolve to stale code.  See
# config.expression_modname.
_module_counter = itertools.count()

@utility.formatDocstring(config.python_package_name())
def compile(
    interp, string, mode='module', imports=None, exprtype=None, modulename=None
  ):
  '''
  Compile a string containing Curry code.  In mode 'module', the string is
  interpreted as a Curry module.  In mode 'expr', the string is interpreted
  as a Curry expression.

  Args:
    string:
        A string containing Curry code.
    mode:
        Indicates how to interpret the string (see above).
    imports:
        A list specifying additional modules to import.  The elements can be
        strings or :class:`CurryModule <{0}.objects.CurryModule>` objects.
        Import statements will be prepended to the code string and CURRYPATH
        will be adjusted accordingly.  This can be useful when importing
        dynamically-compiled modules whose names and locations are difficult to
        obtain.
    exprtype:
        A string specifying the expression type. This is what would appear to
        the right of ``::`` in a Curry type annotation for the expression.
        Used only in 'expr' mode.  Without it, the class constraints of the
        expression are defaulted with the table of the PAKCS REPL: ``Num``
        to ``Int``, ``Fractional`` to ``Float``, ``Monad`` to ``IO``, a
        lone ``Data`` to ``Bool``; see :mod:`{0}.typecheck.defaulting`.
    modulename:
        Specifies the module name.  Used only in 'module' mode.  If the name
        begins with an underscore, then it will not be placed in
        :data:`curry.interpreter:Interpreter.modules`.  By default, a unique
        name is chosen.

  Returns:
    In 'module' mode, a :class:`CurryModule <{0}.objects.CurryModule>`.  In
    'expr' mode, a Curry expression.  A text that ends in ``where x, y
    free`` gives a :class:`Goal <{0}.typecheck.goals.Goal>` whose values
    carry the bindings of the variables, as the REPL of PAKCS prints them;
    with ``exprtype`` the clause stays a local declaration.

  Raises:
    CompileError:
        The front end rejects the text, or, in 'expr' mode without
        ``exprtype``, the table cannot default a class constraint.
  '''
  stmts, currypath = getImportSpecForExpr(
      interp, [] if imports is None else imports
    )
  if mode == 'module':
    if exprtype is not None:
      raise ValueError('%r is only allowed in mode=%r', ('exprtype', 'expr'))
    if modulename is None:
      modulename = config.interactive_modname() + str(next(_module_counter))
    if modulename in interp.modules:
      raise ValueError('module %r is already defined' % modulename)
    string = '%s\n%s' % ('\n'.join(stmts), string)
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
  elif mode == 'expr':
    if modulename is not None:
      raise ValueError('%r is only allowed in mode=%r', ('modulename', 'module'))
    func, freevars = compile_expression(
        interp, string, stmts, currypath, exprtype=exprtype
      )
    return expression_goal(interp, func, string, freevars)
  else:
    raise TypeError('expected mode %r or %r' % ('module', 'expr'))

def compile_expression(
    interp, string, stmts, currypath, exprtype=None, lift_freevars=True
  ):
  '''
  Compiles a Curry expression into a module of its own, as the binding
  ``compiled_expression = <string>``.  With ``lift_freevars``, the variables
  of a trailing ``where x, y free`` become parameters of the binding, as
  the REPL of PAKCS does; with ``exprtype`` the text is compiled as written
  under the signature.  Returns the symbol of the binding and the names of
  the lifted variables.
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
    , modulename=config.expression_modname(next(_module_counter))
    , keep_temp_files=interp.flags['keep_temp_files']
    , postmortem=interp.flags['postmortem']
    )
  # The module leaves the registry, but it stays loaded until the
  # interpreter resets: the goal's graph refers to the module's code and
  # data (string literals, local functions), and nothing in the goal keeps
  # the module alive.  On the C++ backend, an unloaded module leaves
  # dangling pointers in any goal compiled from it.  The name is unique for
  # the process, so the modules cannot clash.
  del interp.modules[icur.name]
  interp._expression_modules.append(moduleobj)
  return getattr(moduleobj, '.symbols')[COMPILED_NAME], freevars

def expression_goal(interp, func, string, freevars):
  '''
  The goal of a compiled expression.  The leading parameters of the binding
  are class dictionaries; the table of the PAKCS REPL defaults them.  The
  parameters after them are the lifted free variables, which get fresh
  variables.  A saturated call takes one rewrite step here, so the result
  looks like the expression and not like a call of the binding.
  '''
  nfree = len(freevars)
  dicts = []
  scheme = None
  if func.info.arity > nfree:
    try:
      scheme = interp.sigtable.lookup(func, required=True)
    except sigtable.InterfaceError as err:
      raise exceptions.CompileError(
          'expression %r has parameters but no type: %s' % (string, err)
        )
    if scheme.source_arity != nfree:
      raise exceptions.CompileError(
          'expression %r compiled to a function of %d value parameter(s); '
          'add a type annotation (exprtype)' % (string, scheme.source_arity)
        )
    try:
      defaulted = defaulting.default_scheme(
          scheme, what='expression %r' % string
        , hint='add a type annotation (exprtype)'
        , type_arity=goals.type_arity(interp)
        )
    except defaulting.DefaultingError as err:
      raise exceptions.CompileError(str(err))
    dicts = goals.dictionaries(interp, defaulted)
  markers = [goals.free_marker() for _ in freevars]
  expr = interp.expr(func, *dicts, *markers)
  if freevars:
    root = interp.expr((expr,) + tuple(markers))
    return goals.Goal(root, freevars, scheme, string)
  if inspect.isa_func(expr):
    evaluator.single_step(interp, expr)
  return expr

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
  func, _ = compile_expression(
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
  module = interp.modules[modulename]
  return _updateImports(interp, module, stmts, currypath)

@_updateImports.when(types.ModuleType)
def _updateImports(interp, module, stmts, currypath):
  if module.__name__ != '_System':
    stmts.append('import ' + module.__name__)
    # If this is a dynamic module, add its directory to the search path.
    h = handle.Handle(module)
    tmpd = h.icurry.metadata.get('all.tmpd', None)
    if tmpd is not None:
      currypath.insert(0, tmpd)
    elif not h.is_package and h.icurry.filename:
      # A module loaded from a file outside the search path, e.g., by the
      # :load command of the REPL: the front end must find its source.
      root = sigtable.module_root(
          os.path.dirname(os.path.abspath(h.icurry.filename)), h.fullname
        )
      if root not in currypath:
        currypath.insert(0, root)

