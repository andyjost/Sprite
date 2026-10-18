from ..evaluation import report_error
from . import commands
from . import options
from .resolve import resolve
import importlib, sys
curry = importlib.import_module(__package__[:__package__.find('.')])

__all__ = ['REPL']

def trap(fatal=False):
  def decorator(f):
    def decorated(*args, **kwds):
      try:
        f(*args, **kwds)
      except SystemExit:
        raise
      except KeyboardInterrupt:
        if fatal:
          sys.exit(1)
      except BaseException as e:
        args[0].status = report_error(e)
        if fatal:
          sys.exit(1)
    return decorated
  return decorator

class REPL(object):
  '''A Curry read-eval-print loop.'''
  def __new__(cls, args, **kwds):
    self = object.__new__(cls)
    self.status = 0
    self.command = None
    self.args = None
    self.module = None
    # The last load, retained across a reset or an unsuccessful retry.
    self.loaded = None
    self.loaded_name = None
    self.action = kwds.pop('action', cls.defaultaction)
    self.options = options.Options(self)
    return self

  @trap(fatal=True)
  def __init__(self, args, **kwds):
    '''
    Initialize the REPL.

    Command-line arguments are processed, and an exception is raised if any of
    them fail.
    '''
    args = args[::-1]
    illegal = []
    cmds = []
    while args:
      command = args.pop()
      if not command.startswith(':'):
        illegal.append(command)
      else:
        subargs = []
        while args:
          if args[-1].startswith(':'):
            break
          else:
            subargs.append(args.pop())
        cmds += [(command, subargs)]
    if illegal:
      raise ValueError("Illegal arguments: %s" % (' '.join(illegal),))
    for self.command, self.args in cmds:
      self.eval()
      if self.status:
        sys.exit(self.status)
    if self.module is None:
      self.command = ':load'
      self.args = ['Prelude']
      self.eval()

  def read(self):
    '''Read user input.'''
    try:
      line = input('%s> ' % self.module.__name__)
    except EOFError:
      sys.exit(self.status)
    if not line:
      self.command = None
      self.args = None
    elif line.startswith(':'):
      command, *tail = line.split(maxsplit=1)
      self.command = resolve(command, commands.COMMANDS, 'command')
      text = tail[0] if tail else ''
      self.args = [text] if self.command in (':eval', ':type', ':load') and text else text.split()
    else:
      self.command = ':eval'
      self.args = [line]

  def eval(self):
    '''Evaluate a command.'''
    if not self.command:
      return
    else:
      commands.eval(self.command, self)

  def set_flags(self, **flags):
    """Reset with validated flags, then import the session's module again."""
    from ...interpreter.flags import get_default_flags, getflags
    defaults = dict(get_default_flags(), **getflags())
    flags = dict({name: value for name, value in self.options.values.items()
        if value != defaults[name]}, **flags)
    curry.reset(**flags)
    self.options.values.update(curry.flags)
    self.options.values.update(flags)
    loaded = self.loaded
    loaded_name = self.loaded_name
    if loaded is None:
      return
    try:
      commands.load(self, loaded_name)
      self.loaded = loaded
    except Exception:
      commands.load(self, 'Prelude')
      self.loaded = loaded
      self.loaded_name = loaded_name
      raise

  def defaultaction(self, value):
    '''The default handler for values.'''
    print(curry.show(value))

  def enter(self):
    '''Enter the loop.'''
    @trap(fatal=False)
    def body(repl):
      self.read()
      self.eval()
    while True:
      body(self)
