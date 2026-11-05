from ..evaluation import evaluate
from . import options
from .resolve import resolve
import importlib, logging, os, shlex, sys
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
  # :load accepts a local source basename even when CPM's path contains
  # only package source directories. Import it through the file API.
  source = arg if arg.endswith('.curry') else arg + '.curry'
  target = os.path.abspath(source) if os.path.isfile(source) else arg
  if os.path.isfile(source):
    # Named transitive imports also need the local program's search root.
    dirname = os.path.dirname(target)
    if dirname not in curry.path:
      curry.path.insert(0, dirname)
  repl.module = curry.import_(target)
  repl.added = []
  curry.program_name = curry.info(repl.module).name
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


def cmdAdd(repl):
  """Add a module to the expression scope, retaining the loaded program."""
  if len(repl.args) != 1:
    raise ValueError(':add expects one module')
  module = curry.import_(repl.args[0])
  if module not in repl.added:
    repl.added.append(module)


def imports(repl):
  '''The modules in scope at the prompt: the loaded module.'''
  return ([] if repl.module is None else [repl.module]) + repl.added

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
  args = list(repl.args)
  # CPM puts the verbosity and the package's compiler options in one :set.
  if args and args[0] in ('v0', 'v1', 'v2', 'v3', 'v4'):
    repl.verbosity = int(args.pop(0)[1:])
    logging.getLogger('curry').setLevel(
        logging.ERROR if repl.verbosity == 0 else logging.WARNING)
    if not args:
      return
  if args and args[0] in ('+time', '-time'):
    repl.pakcs_options['time'] = args.pop(0) == '+time'
    if args:
      raise ValueError('Unexpected arguments to :set time')
    return
  if args and args[0] in ('parser', 'rts', 'path', 'args'):
    name = args.pop(0)
    if not args and name != 'args':
      raise ValueError('Missing value for :set ' + name)
    value = ' '.join(args)
    if name == 'path':
      if len(args) == 1 and not value.startswith(('"', "'")):
        path = value
      else:
        paths = shlex.split(value)
        if len(paths) != 1:
          raise ValueError(':set path expects one search path')
        path = paths[0]
      curry.path[:0] = path.split(os.pathsep)
    elif name == 'args':
      curry.program_arguments = shlex.split(value)
    elif name == 'parser' and value != '-Wnone':
      raise ValueError('Unsupported parser options: ' + value)
    elif name == 'rts' and value != '-T':
      raise ValueError('Unsupported runtime options: ' + value)
    if name == 'parser':
      os.environ['SPRITE_FRONTEND_WARNINGS'] = '0'
    repl.pakcs_options[name] = value
    return
  repl.args = args
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

def cmdSave(repl):
  """Save an executable named after the loaded module in the current directory."""
  if repl.loaded is None:
    raise ValueError('No module loaded')
  expression = ' '.join(repl.args) if repl.args else 'main'
  module = repl.module
  goal = expression
  try:
    module[expression]
  except curry.exceptions.SymbolLookupError:
    module = curry.compile('spriteSavedMain = ' + expression,
        imports=imports(repl))
    goal = 'spriteSavedMain'
  filename = repl.loaded_name
  from ...interpreter.session import save
  save(curry._interpreter_, module, filename, main=goal, program_arguments=True)
  os.chmod(filename, os.stat(filename).st_mode | 0o111)


def cmdQuit(repl):
  '''Executes the :quit command.'''
  assert repl.command == ':quit'
  sys.exit(repl.status)

COMMANDS = {
    ':load' : cmdLoad
  , ':add' : cmdAdd
  , ':reload' : cmdReload
  , ':eval' : cmdEval
  , ':type' : cmdType
  , ':set'  : cmdSet
  , ':save' : cmdSave
  , ':quit' : cmdQuit
  }

def eval(name, *args):
  '''Evaluate a command.  The name may be any unambiguous prefix.'''
  name = resolve(name, COMMANDS.keys(), 'command')
  if args:
    # The handlers check the full name of the command.
    args[0].command = name
  return COMMANDS[name](*args)

