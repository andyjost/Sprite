from . import options
from .resolve import resolve
import curry
import os
import sys
import traceback

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

def cmdEval(repl):
  '''Executes an :eval command.  Calls ``repl.action`` for each value.'''
  assert repl.command == ':eval'
  if repl.args:
    goal = curry.compile(' '.join(repl.args), mode='expr')
    values = iter(curry.eval(goal))
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
      print >>sys.stderr, 'Usage:'
      print >>sys.stderr, '    :set <option> <value>'
      print >>sys.stderr, '    :set [+/-]<option>        (Boolean options only)'
      print >>sys.stderr
      print >>sys.stderr, 'Options for ":set" command:'
      for name in sorted(options.Options.names()):
        print >>sys.stderr, options.Options.usage(name, indent=4)
      print >>sys.stderr
      print >>sys.stderr, 'Current settings:'
      boolopts = []
      valueopts = []
      for name in sorted(options.Options.names()):
        name,value,spec = repl.options.state(name)
        if spec.isbool:
          boolopts.append(('+' if value else '-') + spec.name)
        else:
          valueopts.append((name, value))
      print >>sys.stderr, ' '.join(boolopts)
      w = max([len(item[0]) for item in valueopts] or [0]) # FIXME: remove "or [0]" when a valueopt exists
      for name,value in valueopts:
        print >>sys.stderr, name.ljust(w), ':', repr(value)
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
  , ':set'  : cmdSet
  , ':quit' : cmdQuit
  }

def eval(name, *args):
  '''Evaluate a command.'''
  name = resolve(name, COMMANDS.keys(), 'command')
  return COMMANDS[name](*args)

