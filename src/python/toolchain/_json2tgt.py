from . import _filenames, _system
import logging

__all__ = ['json2tgt']
logger = logging.getLogger(__name__)

def json2tgt(backend_name, jsonfile, currypath, **kwds):
  '''
  Compiles JSON to a final target such as Python or C++, and saves the result.

  Args:
    backend_name:
        The name of the backend to use for code generation.
    jsonfile:
        The name of the JSON file to convert.
    currypath:
        The list of Curry code search paths.
    **kwds:
        Additional keywords.  See :class:`Json2TgtConverter`.

  Returns:
    The target file name.
  '''
  return Json2TgtConverter(backend_name, **kwds).convert(jsonfile, currypath)

class Json2TgtConverter(object):
  def __init__(self, backend_name, **kwds):
    self.backend_name = backend_name
    self.quiet  = kwds.get('quiet', False)
    self.goal   = kwds.get('goal', None)

  @_system.updateCheck
  def convert(self, file_in, currypath):
    from . import _loadcurry
    icurry = _loadcurry.loadjson(file_in)

    from ..interpreter import Interpreter
    interp = Interpreter(flags={'backend': self.backend_name})
    interp.path = currypath
    module = interp.import_(icurry)

    file_out = _filenames.tgtfilename(file_in, self.backend_name)
    _system.makeOutputDir(file_out)
    interp.save(module, file_out, goal=self.goal)
    return file_out

