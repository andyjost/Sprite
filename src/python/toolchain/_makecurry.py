from .. import config
from . import _findcurry, _curry2icurry, _icurry2json
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
    The JSON file name if json=True (the default) was supplied, else None.
  '''
  if currypath is None:
    from .. import path as currypath
  do_json = kwds.pop('json', True)
  do_icy = do_json or kwds.pop('icy', True)
  with IntermediateStep(
      tidy=kwds.pop('tidy', False)
    , output=kwds.get('output', None)
    ) as step:
    if do_icy:
      step.currentfile = _findcurry.currentfile(
          name, currypath, json=do_json, **kwds
        )
      if os.path.isdir(step.currentfile):
        return step.currentfile
      # suffix = .curry, .icy, .json, or .json.z.
      if step.currentfile.endswith('.curry'):
        step.currentfile = _curry2icurry.curry2icurry(step.currentfile, currypath, **kwds)
        assert step.currentfile.endswith('.icy')
        if do_json:
          step.intermediates.append(step.currentfile)
      # suffix = .icy, .json, or .json.z.
      if do_json:
        step.currentfile = _icurry2json.icurry2json(step.currentfile, currypath, **kwds)
        # suffix = .json, or .json.z.
        return step.currentfile

class IntermediateStep(object):
  '''
  Context manager to handle a toolchain step.

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
