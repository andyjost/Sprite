'''
Implements Interpreter.compile.
'''

from .. import importer

def compile(
    interp, string, mode='module', imports=None, modulename='_interactive_'
  ):
  '''
  Compile a string containing Curry code.  In mode "module", the string is
  interpreted as a Curry module.  In mode "expr", the string is interpreted
  as a Curry expression.

  Parameters:
  -----------
  ``string``
      A string containing Curry code.
  ``mode``
      Indicates how to interpret the string (see above).
  ``imports``
      Names the modules to import when compiling an expresion.  Unused in
      "module" mode.  By default, all modules loaded in the current
      interpreter are imported.
  ``modulename``
      Specifies the module name.  Used only in "module" mode.  If the name
      begins with an underscore, then it will not be placed in
      ``Interpreter.modules``.

  Returns:
  --------
  In "module" mode, a Curry module.  In "expr" mode, a Curry expression.
  '''
  if mode == 'module':
    if modulename in interp.modules:
      raise ValueError('module "%s" is already defined' % modulename)
    icur = importer.str2icurry(string, interp.path, modulename=modulename)
    try:
      module = interp.import_(icur)
      module.__file__ = icur.__file__
      module._tmpd_ = icur._tmpd_
      return module
    finally:
      if icur.name.startswith('_') and icur.name in interp.modules:
        del interp.modules[icur.name]
  elif mode == 'expr':
    stmts, currypath = importer.getImportSpecForExpr(
        interp
      , interp.modules.keys() if imports is None else imports
      )
    stmts += ['expression = ' + string]
    string = '\n'.join(stmts)
    icur = importer.str2icurry(string, currypath)
    module = interp.import_(icur)
    del interp.modules[icur.name]
    expr = interp.expr(module.expression)
    interp._step(expr)
    return expr
  else:
    raise TypeError('expected mode "module" or "expr"')

