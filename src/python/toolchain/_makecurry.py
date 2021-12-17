from .. import config
from . import plans, _findcurry
from ..utility import formatDocstring
import logging, os, shutil, sys

__all__ = ['makecurry']
logger = logging.getLogger(__name__)

@formatDocstring(config.python_package_name())
def makecurry(name, currypath=None, **kwds):
  '''
  Run the build toolchain for a Curry target.

  Following this, the specified file is up-to-date and can be loaded.  This
  function uses the timestamps of prerequisite files to avoid repeating steps.

  Args:
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
  with ToolchainContext(tidy=do_tidy, output=output) as pipeline:
    plan = plans.Plan(kwds)
    pipeline.currentfile = _findcurry.currentfile(
        name, currypath
      , py=plan.do_py, json=plan.do_json, icy=plan.do_icy
      , **kwds
      )
    if not os.path.isdir(pipeline.currentfile):
      Maker(plan, pipeline, name, currypath, kwds).make()
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
    return self.current_position == len(self.plan)

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

  @property
  def copy_required(self):
    if self.output is None or self.currentfile is None:
      return False
    else:
      return not (os.path.exists(self.output) and
                  os.path.samefile(self.output, self.currentfile))

