from ..icurry import readcurry as iread, json as ijson
from .. import config
from . import _filenames, _system
from ..utility.binding import binding
from ..utility import filesys
from ..utility.strings import ensure_str, ensure_binary
import logging, os, zlib

__all__ = ['icurry2json']
logger = logging.getLogger(__name__)

# The ability to read ICurry files with curry.utility.readcurry was developed
# in Oct 2021.  Before that, an external program called icurry2jsontext was
# used to convert those to JSON.
CONVERT_JSON_INTERNALLY = True

def icurry2json(icurryfile, currypath, **kwds):
  '''
  Calls ``icurry2jsontext`` to produce an ICurry-JSON file.

  Args:
    curryfile:
        The name of the Curry file to convert.
    currypath:
        The list of Curry code search paths.
    **kwds:
        Additional keywords.  See :class:`ICurry2JsonConverter`.

  Returns:
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
    cmd_compact = [config.jq_tool(), '--compact-output', '.'] \
        if self.do_compact else None
    _system.makeOutputDir(file_out)

    if CONVERT_JSON_INTERNALLY:
      cmd = None
    else:
      cmd = [config.icurry2jsontext_tool(), '-i', file_in]

    logger.debug(
        'Command: %s %s%s> %s'
      ,  ' '.join(cmd) if cmd else '<internal-icurry2json>'
      , '| %s ' % ' '.join(cmd_compact) if cmd_compact else ''
      , '| zlib-flate -compress ' if self.do_zip else ''
      , file_out
      )

    if cmd:
      with _system.bindCurryPath(currypath):
        json = _system.popen(cmd, pipecmd=cmd_compact)
    else:
      rcdata = iread.load(file_in)
      json = ijson.dumps(rcdata)
      if self.do_compact:
        with _system.bindCurryPath(currypath):
          json = _system.popen(cmd_compact, input=json)
    if self.do_zip:
      mode = 'wb'
      json = zlib.compress(ensure_binary(json))
    else:
      mode = 'w'
      json = ensure_str(json)
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
  with open(file_in, 'rb') as istream:
    with filesys.remove_file_on_error(file_out):
      with open(file_out, 'wb') as ostream:
        json = istream.read()
        json = convert(json)
        ostream.write(json)

