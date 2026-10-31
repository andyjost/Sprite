from .. import cache
from ..icurry import readcurry as iread, json as ijson
from . import _filenames, _system
from ..utility import filesys
import hashlib, logging, os, zlib

__all__ = ['icurry2json']
logger = logging.getLogger(__name__)

def write_receipt(jsonfile, icyfile):
  with open(icyfile, 'rb') as stream:
    digest = hashlib.sha256(stream.read()).hexdigest()
  cache.write_file(jsonfile + '.input', digest + '\n')

def json_is_stale(filename, currypath=None):
  if not filename.endswith(('.json', '.json.z')):
    return False
  icyfile = _filenames.icurryfilename(filename)
  if not os.path.isfile(icyfile):
    return False # JSON-only inputs remain valid translation inputs.
  try:
    with open(icyfile, 'rb') as stream:
      digest = hashlib.sha256(stream.read()).hexdigest()
    with open(filename + '.input', encoding='ascii') as stream:
      return stream.read().strip() != digest
  except OSError:
    return True

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
    plain = text.encode('utf-8')
    data = plain
    if self.do_zip:
      data = zlib.compress(data)
    cache.write_file(file_out, data)
    write_receipt(file_out, file_in)
    # Both spellings must describe the same ICurry. Inspection and save
    # can request either one after an interpreted image load.
    sibling = file_out[:-2] if self.do_zip else file_out + '.z'
    if os.path.isfile(sibling):
      cache.write_file(sibling, plain if self.do_zip else zlib.compress(plain))
      write_receipt(sibling, file_in)
    logger.info('module %s: JSON written', rcdata.fullname)
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
    data = convert(istream.read())
  cache.write_file(file_out, data)
  if os.path.isfile(file_in + '.input'):
    with open(file_in + '.input', encoding='ascii') as stream:
      cache.write_file(file_out + '.input', stream.read())
  if logger.isEnabledFor(logging.INFO):
    logger.info('module %s: JSON written', _filenames.logging_module_name(file_out))

icurry2json.is_stale = json_is_stale
