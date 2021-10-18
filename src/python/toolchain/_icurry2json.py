from .. import config
from . import _filenames, _system
from ..utility.binding import binding
from ..utility import filesys
import logging, os, zlib

__all__ = ['icurry2json']
logger = logging.getLogger(__name__)

def icurry2json(icurryfile, currypath, **kwds):
  '''
  Calls "icurry2jsontext" to produce an ICurry-JSON file.

  Parameters:
  -----------
  ``curryfile``
      The name of the Curry file to convert.
  ``currypath``
      The list of Curry code search paths.
  ``kwds``
      Additional keywords.  See ICurry2JsonConverter.

  Returns:
  -------
  The JSON file name.  May end with .json or .json.z.
  '''
  return ICurry2JsonConverter(**kwds).convert(icurryfile, currypath)

class ICurry2JsonConverter(object):
  def __init__(self, **kwds):
    self.do_compact = config.jq_tool() and kwds.get('compact', True)
    self.do_zip     = kwds.get('zip', True)

  @_system.updateCheck
  def convert(self, file_in, currypath):
    file_in, is_shortcut = _getIcyOrShortcut(file_in, self.do_zip)
    if is_shortcut:
      return file_in
    assert file_in.endswith('.icy')
    file_out = file_in[:-4] + '.json'
    if self.do_zip:
      file_out += '.z'
    with binding(os.environ, 'CURRYPATH', ':'.join(currypath)):
      _system.makeOutputDir(file_out)
      cmd = [config.icurry2jsontext_tool(), '-i', file_in]
      cmd_compact = [config.jq_tool(), '--compact-output', '.'] \
          if self.do_compact else None
      logger.debug(
          'Command: %s %s%s> %s'
        ,  ' '.join(cmd)
        , '| %s ' % ' '.join(cmd_compact) if cmd_compact else ''
        , '| zlib-flate -compress ' if self.do_zip else ''
        , file_out
        )
      json = _system.popen(cmd, pipecmd=cmd_compact)
      if self.do_zip:
        json = zlib.compress(json)
        mode = 'wb'
      else:
        mode = 'w'
      with filesys.remove_file_on_error(file_out):
        with open(file_out, mode) as output:
          output.write(json)
    return file_out

def _getIcyOrShortcut(file_in, do_zip):
  '''
  If the input file is the desired JSON output or can be converted to it, apply
  the conversion (if any) and return the JSON filename.  Otherwise, find the
  ICurry file to use as the source for the ICurry-to-JSON convertion and return
  that.

  Returns:
  --------
  A pair contining the JSON or ICurry filename, and a Boolean indicating
  whether the opertion was shortcut.
  '''
  if file_in.endswith('.json'):
    if do_zip:
      file_out = file_in + '.z'
      _convertFile(file_in, file_out, zlib.compress)
      return file_out, True
    else:
      return file_in, True
  elif file_in.endswith('.json.z'):
    if not do_zip:
      file_out = file_in[:-2]
      _convertFile(
          file_in, file_out
        , lambda json: zlib.decompress(json).encode('utf-8')
        )
      return file_out, True
    else:
      return file_in, True
  elif file_in.endswith('.curry'):
    file_in = _filenames.icurryfilename(file_in)
  return file_in, False

def _convertFile(file_in, file_out, convert):
  '''
  Read from file_in, apply the conversion, and write the result to file_out.
  '''
  with open(file_in, 'r') as istream:
    with filesys.remove_file_on_error(file_out):
      with open(file_out, 'wb') as ostream:
        json = istream.read()
        json = convert(json)
        ostream.write(json)
