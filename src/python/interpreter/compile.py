'''
Implements Interpreter.compile.
'''

from .. import config, exceptions, icurry, objects, toolchain, utility
from ..utility.visitation import dispatch
import six, types

__all__ = ['compile']

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
        Used only in 'expr' mode.
    modulename:
        Specifies the module name.  Used only in 'module' mode.  If the name
        begins with an underscore, then it will not be placed in
        :data:`curry.interpreter:Interpreter.modules`.  By default, a unique
        name is chosen.

  Returns:
    In 'module' mode, a :class:`CurryModule <{0}.objects.CurryModule>`.  In
    'expr' mode, a Curry expression.
  '''
  stmts, currypath = getImportSpecForExpr(
      interp, [] if imports is None else imports
    )
  # currypath = currypath + interp.path
  if mode == 'module':
    if exprtype is not None:
      raise ValueError('%r is only allowed in mode=%r', ('exprtype', 'expr'))
    if modulename is None:
      modulename = config.interactive_modname() + str(next(interp._counter))
    if modulename in interp.modules:
      raise ValueError('module %r is already defined' % modulename)
    string = '%s\n%s' % ('\n'.join(stmts), string)
    icur = toolchain.str2icurry(
        interp, string, currypath
      , modulename=modulename
      , keep_temp_files=interp.flags['keep_temp_files']
      , postmortem=interp.flags['postmortem']
      )
    try:
      module = interp.import_(icur)
      module.__file__ = icur.__file__
      module._tmpd_ = icur._tmpd_
      return module
    finally:
      if icur.name == config.interactive_modname() \
          and icur.name in interp.modules:
        del interp.modules[icur.name]
  elif mode == 'expr':
    # Compile the expression with a legal name but then rename it to "<expr>".
    # The frontend requires a legal name, of course, but renaming makes it
    # clear that this is a system-generated name when reported to the user.
    if modulename is not None:
      raise ValueError('%r is only allowed in mode=%r', ('modulename', 'module'))
    compiled_name = 'compiled_expression'
    visible_name = '<expr>'
    if exprtype:
      stmts += ['%s :: %s' % (compiled_name, exprtype)]
    stmts += ['%s = %s' % (compiled_name, string)]
    curry_code = '\n'.join(stmts)
    icur = toolchain.str2icurry(
        interp, curry_code, currypath
      , keep_temp_files=interp.flags['keep_temp_files']
      , postmortem=interp.flags['postmortem']
      )
    funobj = icur.functions.pop(compiled_name)
    funobj.fullname = '.'.join([funobj.modulename, visible_name])
    icur.functions[visible_name] = funobj
    module = interp.import_(icur)
    del interp.modules[icur.name]
    func = getattr(module, '.symbols')[visible_name]
    if func.info.arity > 0:
      raise exceptions.CompileError(
          'expression %r requires a type annotation' % string
        )
    expr = interp.expr(func)
    return interp.backend.single_step(interp, expr)
  else:
    raise TypeError('expected mode %r or %r' % ('module', 'expr'))

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

@_updateImports.when(six.string_types)
def _updateImports(interp, modulename, stmts, currypath):
  module = interp.modules[modulename]
  return _updateImports(interp, module, stmts, currypath)

@_updateImports.when(types.ModuleType)
def _updateImports(interp, module, stmts, currypath):
  if module.__name__ != '_System':
    stmts.append('import ' + module.__name__)
    # If this is a dynamic module, add its directory to the search path.
    if getattr(module, '_tmpd_', None) is not None:
      currypath.insert(0, module._tmpd_)

