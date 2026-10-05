from . import options
from .resolve import resolve
import importlib, os, sys, traceback
curry = importlib.import_module(__package__[:__package__.find('.')])
_compile = importlib.import_module(curry.__name__ + '.interpreter.compile')

__all__ = ['COMMANDS', 'eval']

def cmdLoad(repl):
  '''Executes a :load command.  Sets ``repl.module``.'''
  assert repl.command == ':load'
  try:
    arg, = repl.args
  except ValueError:
    if repl.args:
      raise ValueError("Too many arguments provided to ':load'")
    else:
      raise ValueError("No argument provided to ':load'")
  filename = os.path.abspath(arg)
  dirname = os.path.dirname(filename)
  currypath = [dirname] + curry.path
  basename = os.path.basename(filename)
  modulename = os.path.splitext(basename)[0]
  repl.module = curry.import_(modulename, currypath=currypath)
  # The expressions of :eval and :type import the loaded module, so the
  # front end must find it.
  if dirname not in curry.path:
    curry.path.insert(0, dirname)

def imports(repl):
  '''The modules in scope at the prompt: the loaded module.'''
  return [] if repl.module is None else [repl.module]

def cmdEval(repl):
  '''
  Executes an :eval command.  Calls ``repl.action`` for each value.  The
  expression sees the loaded module.  A class constraint of the expression is
  defaulted with the table of the PAKCS REPL; a variable of a trailing
  ``where x free`` whose type is absent from the result type is reported
  with its binding, as PAKCS prints it (see curry.typecheck.goals).
  '''
  assert repl.command == ':eval'
  if repl.args:
    # The expression goes to curry.eval and is not kept here.  A reference
    # to the root of the goal keeps the history of the search reachable
    # while the evaluation runs; see curry.typecheck.goals.Goal.evaluate.
    values = iter(curry.eval(
        curry.compile(' '.join(repl.args), mode='expr', imports=imports(repl))
      ))
    while True:
      try:
        value = next(values)
      except StopIteration:
        break
      except:
        msg = 'An error occurred during evaluation.'
        if repl.options['internal-error-details']:
          msg += '  To suppress details, type ":set -internal-error-details".\n'
          msg += traceback.format_exc()
        else:
          msg += '  For details, rerun with ":set +internal-error-details".'
        raise RuntimeError(msg)
      else:
        repl.action(repl, value)

def cmdType(repl):
  '''
  Executes a :type command: prints the type of an expression as the front
  end infers it, with its class context and before any defaulting, e.g.,
  ``1+2 :: Num a => a``.
  '''
  assert repl.command == ':type'
  if not repl.args:
    raise ValueError("No argument provided to ':type'")
  text = ' '.join(repl.args)
  scheme = _compile.expression_scheme(
      curry.getInterpreter(), text, imports=imports(repl)
    )
  module = None if repl.module is None else repl.module.__name__
  print('%s :: %s' % (text, curry.typecheck.show_scheme(scheme, module=module)))

def cmdSet(repl):
  '''Executes a :set command.  May update ``repl.options``.'''
  assert repl.command == ':set'
  try:
    name,value = repl.args
  except ValueError:
    try:
      name, = repl.args
      if name.startswith('+'):
        name = name[1:]
        value = True
      elif name.startswith('-'):
        name = name[1:]
        value = False
      else:
        raise ValueError('Invalid command.  Type ":set" for help.')
    except ValueError:
      if repl.args:
        raise ValueError('Invalid command.  Type ":set" for help.')
      print('Usage:', file=sys.stderr)
      print('    :set <option> <value>', file=sys.stderr)
      print('    :set [+/-]<option>        (Boolean options only)', file=sys.stderr)
      print(file=sys.stderr)
      print('Options for ":set" command:', file=sys.stderr)
      for name in sorted(options.Options.names()):
        print(options.Options.usage(name, indent=4), file=sys.stderr)
      print(file=sys.stderr)
      print('Current settings:', file=sys.stderr)
      boolopts = []
      valueopts = []
      for name in sorted(options.Options.names()):
        name,value,spec = repl.options.state(name)
        if spec.isbool:
          boolopts.append(('+' if value else '-') + spec.name)
        else:
          valueopts.append((name, value))
      print(' '.join(boolopts), file=sys.stderr)
      w = max([len(item[0]) for item in valueopts] or [0]) # FIXME: remove "or [0]" when a valueopt exists
      for name,value in valueopts:
        print(name.ljust(w), ':', repr(value), file=sys.stderr)
      return
  else:
    if name.startswith('+') or name.startswith('-'):
      # Handles, e.g., ":set +option True".
      raise ValueError('Invalid command.  Type ":set" for help.')
  repl.options[name] = value

def cmdQuit(repl):
  '''Executes the :quit command.'''
  assert repl.command == ':quit'
  sys.exit(0)

COMMANDS = {
    ':load' : cmdLoad
  , ':eval' : cmdEval
  , ':type' : cmdType
  , ':set'  : cmdSet
  , ':quit' : cmdQuit
  }

def eval(name, *args):
  '''Evaluate a command.  The name may be any unambiguous prefix.'''
  name = resolve(name, COMMANDS.keys(), 'command')
  if args:
    # The handlers check the full name of the command.
    args[0].command = name
  return COMMANDS[name](*args)

