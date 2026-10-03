from ..icurry import readcurry as iread, json as ijson
from . import _filenames, _system
from ..utility import filesys
import logging, zlib

__all__ = ['icurry2json']
logger = logging.getLogger(__name__)

def icurry2json(icurryfile, currypath, **kwds):
  '''
  Converts an ICurry file to an ICurry-JSON file.

  Args:
    icurryfile:
        The name of the ICurry file to convert.  A Curry file name selects its
        ICurry file.  A JSON file is compressed or decompressed as needed.
    currypath:
        The list of Curry code search paths.  The conversion reads one file
        and does not use it.  The compilation plan passes it to every step.
    **kwds:
        Additional keywords.  See :class:`ICurry2JsonConverter`.

  Returns:
    The JSON file name.  May end with .json or .json.z.
  '''
  return ICurry2JsonConverter(**kwds).convert(icurryfile, currypath)

class ICurry2JsonConverter(object):
  '''
  Reads an ICurry file with Sprite's own reader and writes it as JSON.

  Keyword ``compact`` (default True) selects the compact form of
  :class:`curry.icurry.json.Encoder`.  Keyword ``zip`` (default True)
  compresses the text with zlib and appends ``.z`` to the file name.  The text
  ends with a newline.
  '''
  def __init__(self, **kwds):
    self.do_compact = kwds.get('compact', True)
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
    _system.makeOutputDir(file_out)
    logger.debug(
        'Converting %s to %s%sJSON %s'
      , file_in
      , 'compact ' if self.do_compact else ''
      , 'compressed ' if self.do_zip else ''
      , file_out
      )
    rcdata = iread.load(file_in)
    text = ijson.dumps(rcdata, compact=self.do_compact) + '\n'
    data = text.encode('utf-8')
    if self.do_zip:
      data = zlib.compress(data)
    with filesys.remove_file_on_error(file_out):
      with open(file_out, 'wb') as output:
        output.write(data)
    return file_out

def _getIcyOrShortcut(file_in, do_zip):
  '''
  If the input file is the desired JSON output or can be converted to it, apply
  the conversion (if any) and return the JSON filename.  Otherwise, find the
  ICurry file to use as the source for the ICurry-to-JSON convertion and return
  that.

  Returns:
    A pair containing the JSON or ICurry filename, and a Boolean indicating
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
        , lambda json: zlib.decompress(json)
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

