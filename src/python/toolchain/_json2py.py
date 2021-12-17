from . import _filenames, _system
import logging

__all__ = ['json2py']
logger = logging.getLogger(__name__)

def json2py(jsonfile, currypath, **kwds):
  '''
  Compiles JSON to Python and saves the result.

  Args:
    jsonfile:
        The name of the JSON file to convert.
    currypath:
        The list of Curry code search paths.
    **kwds:
        Additional keywords.  See :class:`Json2PyConverter`.

  Returns:
  -------
  The Python file name.
  '''
  return Json2PyConverter(**kwds).convert(jsonfile, currypath)

class Json2PyConverter(object):
  def __init__(self, **kwds):
    self.quiet = kwds.get('quiet', False)
    self.goal  = kwds.get('goal', None)

  @_system.updateCheck
  def convert(self, file_in, currypath):
    from . import _loadcurry
    icurry = _loadcurry.loadjson(file_in)

    from ..interpreter import Interpreter
    interp = Interpreter()
    interp.path = currypath
    module = interp.import_(icurry)

    file_out = _filenames.pyfilename(file_in)
    _system.makeOutputDir(file_out)
    interp.save(module, file_out, goal=self.goal)
    return file_out

