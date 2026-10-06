from . import commands
from . import options
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
    # The argument of the last :load, for switch_backend.
    self.loaded = None
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
    if self.module is None:
      self.command = ':load'
      self.args = ['Prelude']
      self.eval()

  def read(self):
    '''Read user input.'''
    try:
      line = input('%s> ' % self.module.__name__)
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

  def switch_backend(self, backend):
    '''
    Reloads the interpreter with ``backend`` (the setter of the option
    backend), records the backend in the options, and loads the module of
    the session again, so that the prompt and the expressions see the new
    interpreter.  A reload replaces the Curry path; the load puts the
    directory of the module back.  When that load fails, the session stays
    on the new backend with the Prelude at the prompt, keeps the argument
    of the last :load for a switch back, and reports the error.
    '''
    curry.reload({'backend': backend})
    self.options.values['backend'] = backend
    loaded = self.loaded
    if loaded is None:
      return
    try:
      commands.load(self, loaded)
    except BaseException:
      # The module object of the session belongs to the old interpreter.
      commands.load(self, 'Prelude')
      self.loaded = loaded
      raise

  def defaultaction(self, value):
    '''The default handler for values.'''
    print(value)

  def enter(self):
    '''Enter the loop.'''
    @trap(fatal=False)
    def body():
      self.read()
      self.eval()
    while True:
      body()
