from .. import config
from . import plans, _findcurry
from ..utility import formatDocstring
import importlib.util, logging, os, shutil, sys, time

__all__ = ['compile_seconds', 'makecurry']
logger = logging.getLogger(__name__)

class CompileClock(object):
  '''
  Accumulates the wall time this process spends in the steps of the
  toolchain: the Curry front end, the ICurry-JSON conversion, the code
  generator, and the C++ compiler.  A nested call (a step that imports a
  package) counts once, within the outermost call.  ``Interpreter.stats``
  reports the total as ``compile``.
  '''
  def __init__(self):
    self.seconds = 0.0
    self._depth = 0
    self._start = None

  def __enter__(self):
    if self._depth == 0:
      self._start = time.perf_counter()
    self._depth += 1
    return self

  def __exit__(self, *exc_info):
    self._depth -= 1
    if self._depth == 0:
      self.seconds += time.perf_counter() - self._start

compile_clock = CompileClock()

def compile_seconds():
  '''
  The seconds this process has spent in the steps of the toolchain.  Zero
  when every file was current.
  '''
  return compile_clock.seconds

@formatDocstring(config.python_package_name())
def makecurry(plan, name, currypath=None, **kwds):
  '''
  Run the build toolchain for a Curry target.

  Following this, the specified file is up-to-date and can be loaded.  This
  function uses the timestamps of prerequisite files to avoid repeating steps.

  Args:
    plan:
        The build plan.
    name:
        The module or source file name.
    currypath:
        A sequence of paths to search (i.e., CURRYPATH split on ':').  By
        default, ``{0}.path`` is used.
    is_sourcefile:
        If true, the name arguments is interpreted as a source file.
        Otherwise, it is interpreted as a module name.
    **kwds:
        See documentation for :ref:`sprite-make`.

  Returns:
    The name of the final file in the build pipeline.
  '''
  if currypath is None:
    from .. import path as currypath
  do_tidy = kwds.pop('tidy', False)
  output = kwds.pop('output', None)
  kwds['zip'] = bool(kwds.get('zip', plan.flags & plans.ZIP_JSON))
  with ToolchainContext(tidy=do_tidy, output=output) as pipeline:
    pipeline.currentfile = _findcurry.currentfile(
        plan, name, currypath, **kwds
      )
    if not os.path.isdir(pipeline.currentfile):
      maker = Maker(plan, pipeline, name, currypath, kwds)
      if not maker.done:
        with compile_clock:
          maker.make()
    return pipeline.currentfile

class Maker(object):
  '''
  Executes a compilation plan.
  '''
  def __init__(self, plan, pipeline, name, currypath, kwds):
    self.plan = plan
    self.pipeline = pipeline
    self.name = name
    self.currypath = currypath
    self.kwds = kwds

  @property
  def current_position(self):
    return self.plan.position(self.pipeline.currentfile)

  @property
  def done(self):
    position = self.current_position
    if position == len(self.plan):
      return True
    # A step may end the plan at its input: the C++ backend interprets a
    # module from its JSON instead of compiling it (see Json2Cpp.ends_plan).
    step = self.plan.stages[position].step
    ends_plan = getattr(step, 'ends_plan', None)
    return ends_plan is not None and ends_plan(self.pipeline.currentfile)

  def make(self):
    if self.done:
      return
    while True:
      stage = self.plan.stages[self.current_position]
      self.pipeline.currentfile = stage.step(
          self.pipeline.currentfile, self.currypath, **self.kwds
        )
      if not self.done:
        self.pipeline.intermediates.append(self.pipeline.currentfile)
      else:
        break

class ToolchainContext(object):
  '''
  Context manager to handle a toolchain invocation.

  Handles the removal of intermediate files.  Moves the output file
  to its proper location, if the external tool could not manage that.
  '''
  def __init__(self, currentfile=None, tidy=False, output=None):
    self.currentfile = currentfile
    self.intermediates = []
    self.output = output
    self.tidy = tidy

  def __enter__(self):
    return self

  def __exit__(self, excty, excva, exctb):
    if excty is None:
      # Move the file if "output" was specified.
      if self.copy_required:
        shutil.copy(self.currentfile, self.output)
        if self.currentfile not in self.intermediates:
          self.intermediates.append(self.currentfile)
    if self.tidy:
      for intermediate in self.intermediates:
        logger.debug('Removing intermediate %r', intermediate)
        os.unlink(intermediate)
        if intermediate.endswith('.py'):
          # The toolchain writes the bytecode cache beside a Python file.
          cache = importlib.util.cache_from_source(intermediate)
          if os.path.exists(cache):
            os.unlink(cache)

  @property
  def copy_required(self):
    if self.output is None or self.currentfile is None:
      return False
    else:
      return not (os.path.exists(self.output) and
                  os.path.samefile(self.output, self.currentfile))

