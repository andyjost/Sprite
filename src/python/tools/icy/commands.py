from ..evaluation import evaluate
from . import options
from .resolve import resolve
import importlib, os, sys
curry = importlib.import_module(__package__[:__package__.find('.')])

__all__ = ['COMMANDS', 'eval', 'load']

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
  load(repl, arg)

def load(repl, arg):
  '''
  Loads the module that the file name or module name ``arg`` names, as
  :load does.  Sets ``repl.module`` and ``repl.loaded``.
  '''
  repl.module = curry.import_(arg)
  repl.loaded = arg
  repl.loaded_name = repl.module.__name__
  filename = curry.info(repl.module).file
  if filename is not None:
    dirname = os.path.dirname(os.path.abspath(filename))
    if dirname not in curry.path:
      curry.path.insert(0, dirname)


def cmdReload(repl):
  """Read the current module's source again, in place."""
  if repl.args:
    raise ValueError("':reload' takes no arguments")
  if repl.module is None:
    raise ValueError('No module loaded')
  curry.reload(repl.module)


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
    repl.status = evaluate(
        curry.parse(' '.join(repl.args), imports=imports(repl))
      , action=lambda answer: repl.action(repl, answer)
      )


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
  print('%s :: %s' % (text, curry.typeof(curry.parse(text, imports=imports(repl)))))

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
      for name,value in valueopts:
        print(name, ':', repr(value), file=sys.stderr)
      return
  else:
    if name.startswith('+') or name.startswith('-'):
      # Handles, e.g., ":set +option True".
      raise ValueError('Invalid command.  Type ":set" for help.')
  repl.options[name] = value

def cmdQuit(repl):
  '''Executes the :quit command.'''
  assert repl.command == ':quit'
  sys.exit(repl.status)

COMMANDS = {
    ':load' : cmdLoad
  , ':reload' : cmdReload
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

