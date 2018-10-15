from . import options
from . import commands
import sys

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
        sys.stderr.write('**** ERROR ****\n%s\n' % str(e))
        sys.stderr.flush()
        if fatal:
          sys.exit(1)
    return decorated
  return decorator

class REPL(object):
  '''A Curry read-eval-print loop.'''
  def __new__(cls, args, **kwds):
    self = object.__new__(cls)
    self.command = None
    self.args = None
    self.module = None
    self.action = kwds.pop('action', cls.defaultaction)
    self.options = options.Options()
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
        illegal += command
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
    if self.module is None:
      self.command = ':load'
      self.args = ['Prelude']
      self.eval()

  def read(self):
    '''Read user input.'''
    try:
      line = raw_input('%s> ' % self.module.__name__)
    except EOFError:
      sys.exit(0)
    if not line:
      self.command = None
      self.args = None
    elif line.startswith(':'):
      args = line.split()
      self.command = args[0]
      self.args = args[1:]
    else:
      self.command = ':eval'
      self.args = line.split()

  def eval(self):
    '''Evaluate a command.'''
    if not self.command:
      return
    else:
      commands.eval(self.command, self)

  def defaultaction(self, value):
    '''The default handler for values.'''
    print value

  def enter(self):
    '''Enter the loop.'''
    @trap(fatal=False)
    def body():
      self.read()
      self.eval()
    while True:
      body()
