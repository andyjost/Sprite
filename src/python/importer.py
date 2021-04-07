from __future__ import absolute_import
'''
Code for finding and converting Curry source.

Contains functions for invoking the toolchain to build ICurry and ICurry-JSON
files.  The following file types are used:

  Suffix      Ext. Tool        Description
  +-------    +----------      +---------------------------------------
  .curry                       Curry source code.
  .icy        icurry           ICurry code in Curry format.
  .json[.z]   icurry2jsontext  ICurry code in JSON format [compressed].
'''

from .exceptions import CompileError, ModuleLookupError, PrerequisiteError
from .icurry import json as icurry_json
from . import cache
from . import config
from . import icurry
from . import utility
from .programs.utility import make_exception
from .utility.binding import binding, del_
from .utility import filesys
from .utility import formatting
import errno
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
import types
import zlib


__all__ = [
    'curryFilename'
  , 'CurryImporter'
  , 'findCurryModule'
  , 'findOrBuildICurry'
  , 'icurryFilename'
  , 'jsonFilename'
  , 'loadJsonFile'
  , 'loadModule'
  , 'str2icurry'
  ]
logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

class CurryImporter(object):
  '''An import hook that loads Curry modules into Python.'''
  def __init__(self):
    self.curry = __import__(__name__.split('.')[0])
  def find_module(self, fullname, path=None):
    if fullname.startswith(__package__ + '.lib.'):
      return self
    return None
  def load_module(self, fullname):
    if fullname not in sys.modules:
      name = fullname[len(__package__ + '.lib.'):]
      moduleobj = self.curry.import_(name)
      this = sys.modules[__name__]
      head = name.split('.')[0]
      assert head
      setattr(this, head, moduleobj)
      sys.modules[fullname] = moduleobj
    return sys.modules[fullname]

def loadModule(name, currypath, **kwds):
  '''
  Loads into Python the ICurry for a Curry module or source file, building if
  necessary.

  Parameters:
  -----------
  ``name``
      The module name or source file name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').
  ``is_sourcefile``
      If true, the name arguments is interpreted as a source file.  Otherwise,
      it is interpreted as a module name.

  Raises:
  -------
  ``ModuleLookupError`` if the module is not found.

  Returns:
  --------
  A Python object containing the ICurry for the given name.
  '''
  filename = findOrBuildICurry(name, currypath, **kwds)
  logger.debug('Found module %s at %s', name, filename)
  return loadJsonFile(filename)

def loadJsonFile(jsonfile):
  '''
  Reads an ICurry-JSON file and returns the ICurry.  The file
  must contain one Curry module.
  '''
  assert os.path.exists(jsonfile)
  cached = cache.ParsedJsonCache(jsonfile)
  if cached:
    logger.info('Loading cached ICurry-JSON for %s from %s', jsonfile, cache.filename)
    return cached.icur
  else:
    logger.info('Reading ICurry-JSON from %s', jsonfile)
  if jsonfile.endswith('.z'):
    json = open(jsonfile, 'rb').read()
    json = zlib.decompress(json)
  else:
    json = open(jsonfile).read()
  icur = icurry_json.parse(json)
  icur.filename = curryFilename(jsonfile)
  cached.update(icur)
  return icur

def str2icurry(
    string, currypath
  , modulename=config.interactive_modname()
  , keep_temp_files=False
  ):
  '''
  Compile a string into ICurry.  The string is interpreted as a module
  definition.

  Returns:
  --------
  The ICurry object.  The attributes __file__ and _tmpd_ will be set.
  '''
  moduledir = filesys.CurryModuleDir(modulename, string, keep=keep_temp_files)
  with moduledir:
    jsonfile = findOrBuildICurry(moduledir.curryfile, currypath, is_sourcefile=True)
    icur = loadJsonFile(jsonfile)
    icur.__file__ = moduledir.curryfile
    icur._tmpd_ = moduledir
  return icur

# Keyword defaults.
def _fileNotFoundHint(name, **kwds):
  if os.path.exists(name + '.curry'):
    return 'Perhaps you meant "%s.curry"?' % name

def _targetNotUpdatedHint(prereq, target, start_time, **kwds):
  # Perhaps there is some file under a subdirectory of .curry with the correct
  # name and which is new enough.
  dirname, targetname = os.path.split(target)
  while not dirname.endswith('.curry'):
    dirname, _ = os.path.split(dirname)
  for root, dirs, files in os.walk(dirname):
    candidate = os.path.join(root, targetname)
    if os.path.exists(candidate):
      if start_time <= os.stat(candidate).st_mtime:
        assert not filesys.newer(prereq, candidate)
        return 'It appears %s was updated instead.  Sprite was configured ' \
               'with %s.' % (candidate, SUBDIR)

def findCurryModule(
    name, currypath, is_sourcefile=False, json=True, icy=True, **ignored
  ):
  '''
  Searches for Curry code.  The file returned is the newest among the Curry
  source file (suffix: .curry), the ICurry file (suffix: .icy), and the JSON
  file (suffix: .json.z).

  Parameters:
  -----------
  ``name``
      The module name or source file name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').
  ``is_sourcefile``
      Indicates how to interpreter the name.  If true, the name arguments is
      interpreted as a source file.  Otherwise, it is interpreted as a module
      name.
  ``json``
      Whether to include JSON files in the search.  Setting this to false can
      be used to find an .icy file.
  ``icy``
      Whether to include ICurry .icy files in the search.  Setting this to
      false can be used to search for Curry source code.

  Raises:
  -------
  ``ModuleLookupError`` if the module is not found.

  Returns:
  --------
  The name of either an ICurry-JSON file (suffix: .json) or Curry source file
  (suffix: .curry).  The JSON name may have an additional .z suffix.  The JSON
  file is returned if it is up-to-date, otherwise, the Curry file is returned.
  '''
  if not is_sourcefile:
    # If name is a module name, then search CURRYPATH for the source file or
    # (possibly zipped) JSON and set it as the name.  source file and
    # is_sourcefile=True.  It is acceptable to use a JSON file that has no
    # corresponding source file.  This means a library could be installed as
    # JSON only, without needing to install its source.
    if not utility.isLegalModulename(name):
      raise ModuleLookupError('%r is not a legal module name.' % name)
    # Search for the JSON file first, then ICurry, then .curry.
    suffixes = ['.json', '.json.z'] if json else []
    suffixes += ['.icy'] if icy else []
    search_names = [
        os.path.join('.curry', SUBDIR, name + suffix)
            for suffix in suffixes
      ]
    search_names += [name + '.curry']
    files = filesys.findfiles(currypath, search_names)
    try:
      name = next(files)
    except StopIteration:
      raise make_exception(
          ModuleLookupError
        , 'Curry module "%s" not found.' % name
        , hint=lambda:_fileNotFoundHint(name)
        )
    name = curryFilename(name)

  # Find the newest prerequisite.
  curryfile = name
  if not curryfile.endswith('.curry'):
    raise ModuleLookupError('expected .curry extension in "%s"' % curryfile)
  curryfile = os.path.abspath(curryfile)
  filelist = [curryfile]
  if icy:
    icyfile = icurryFilename(curryfile)
    filelist += [icyfile]
  if json:
    jsonfile = jsonFilename(curryfile)
    filelist += [jsonfile, jsonfile + '.z']
  prereq = os.path.abspath(filesys.newest(filelist))
  if not os.path.exists(prereq):
    # If there is no prerequisite, then there is no Curry file or any of its
    # derivatives (it could be OK to ship Curry files with no source).  Report
    # this as there being no source file.
    assert not os.path.exists(curryfile)
    raise PrerequisiteError('Curry file does not exist: %r' % curryfile)
  if not (os.access(prereq, os.R_OK) and os.path.isfile(prereq)):
    raise PrerequisiteError(
        'prerequisite is the wrong type or is unreadable: %r' % prereq
      )
  logger.debug('Prerequisite for compilation of %r is %r', name, prereq)
  return prereq

def findOrBuildICurry(name, currypath=[], **kwds):
  '''
  Update a target file containing the given Curry module.  Prerequisites are
  checked so that the minimum work is performed.

  Parameters:
  -----------
  ``name``
      The module name or source file name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').
  ``is_sourcefile``
      If true, the name arguments is interpreted as a source file.  Otherwise,
      it is interpreted as a module name.
  ``kwds``
      See documentation for sprite-make.

  Returns:
  --------
  The JSON file name if json=True (the default) was supplied, else None.
  '''
  do_json = kwds.pop('json', True)
  do_icy = do_json or kwds.pop('icy', True)
  do_tidy = kwds.pop('tidy', False)
  curentfile = None
  intermediates = []
  try:
    if do_icy:
      currentfile = findCurryModule(name, currypath, json=do_json, **kwds)
      # suffix = .curry, .icy, .json, or .json.z.
      if currentfile.endswith('.curry'):
        currentfile = curry2icurry(currentfile, currypath, **kwds)
        assert currentfile.endswith('.icy')
        if do_json:
          intermediates.append(currentfile)
      # suffix = .icy, .json, or .json.z.
      if do_json:
        currentfile = icurry2json(currentfile, currypath, **kwds)
        # suffix = .json, or .json.z.
        return currentfile
  finally:
    # Move the file if "output" was specified.
    output = kwds.pop('output', None)
    if output is not None and currentfile is not None and \
        not os.path.samefile(output, currentfile):
      shutil.copy(currentfile, output)
      if currentfile not in intermediates:
        intermediates.append(currentfile)
    # Remove intermediates.
    if do_tidy:
      for intermediate in intermediates:
        logger.debug('Removing intermediate %r', intermediate)
        os.unlink(intermediate)

def _popen(cmd, stdin=None, pipecmd=None):
  '''
  Invokes the given command and returns its stdout as a string.  A second
  pipeline stage may be provided.
  '''
  child = subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if pipecmd:
    term = subprocess.Popen(pipecmd, stdin=child.stdout, stdout=subprocess.PIPE)
    child.stdout.close()
  else:
    term = child

  try:
    stdout,stderr = term.communicate()
  except:
    term.kill()
    raise

  try:
    retcode = term.wait()
  except:
    term.kill()
    sys.stderr.write(stderr)
    raise

  if retcode:
    raise CompileError(
        'while running %s:\n%s' % (' '.join(cmd), formatting.indent(stderr, 8))
      )
  return stdout

def _makeOutputDir(file_out):
  dirname, _ = os.path.split(file_out)
  try:
    os.makedirs(dirname)
  except OSError as e:
    if e.errno != errno.EEXIST:
      raise

def _updateCheck(f):
  def replacement(self, file_in, currypath):
    start_time = time.time()
    file_out = f(self, file_in, currypath)
    if filesys.newer(file_in, file_out):
      raise make_exception(
          CompileError
        , '%s was not updated as expected.' % file_out
        , hint=lambda:_targetNotUpdatedHint(file_in, file_out, start_time)
        )
    elif os.stat(file_out).st_mtime >= start_time:
      logger.debug('Updated %r', file_out)
    return file_out
  return replacement

class Curry2ICurryConverter(object):
  def __init__(self, **kwds):
    self.quiet      = kwds.get('quiet', False)
    self.use_cache  = kwds.get('use_cache', True) \
                          if config.enable_icurry_cache() else False

  @_updateCheck
  def convert(self, file_in, currypath):
    file_out = icurryFilename(file_in)
    cached = self.use_cache and cache.Curry2ICurryCache(file_in, file_out)
    if not cached:
      with binding(os.environ, 'CURRYPATH', ':'.join(currypath)):
        logger.debug('Using CURRYPATH %s', os.environ['CURRYPATH'])
        _makeOutputDir(file_out)
        cmd = [config.icurry_tool(), '-o', file_out, file_in]
        if self.quiet:
          cmd.insert(1, '-q')
        logger.debug('Command: %s', ' '.join(cmd))
        _popen(cmd)
      if self.use_cache:
        cached.update()
    else:
      logger.debug('Found %s in the cache', file_out)
    return file_out

def curry2icurry(curryfile, currypath, **kwds):
  '''
  Calls "icurry" to produce an ICurry file from a Curry file.

  Parameters:
  -----------
  ``curryfile``
      The name of the Curry file to convert.
  ``currypath``
      The list of Curry code search paths.
  ``kwds``
      Additional keywords.  See Curry2ICurryConverter.

  Returns:
  -------
  The ICurry file name.
  '''
  return Curry2ICurryConverter(**kwds).convert(curryfile, currypath)

class ICurry2JsonConverter(object):
  def __init__(self, **kwds):
    self.do_compact = config.jq_tool() and kwds.get('compact', True)
    self.do_zip     = kwds.get('zip', True)

  @_updateCheck
  def convert(self, file_in, currypath):
    if file_in.endswith('.json'):
      if self.do_zip:
        with open(file_in, 'r') as json_in:
          with open(file_in + '.z', 'wb') as json_out:
            json = json_in.read()
            json = zlib.compress(json)
            json_out.write(json)
        return file_in + '.z'
      else:
        return file_in
    elif file_in.endswith('.json.z'):
      if not self.do_zip:
        with open(file_in, 'rb') as json_in:
          with open(file_in[:-2], 'w') as json_out:
            json = json_in.read()
            json = zlib.decompress(json).encode('utf-8')
            json_out.write(json)
        return file_in[:-2]
      else:
        return file_in
    elif file_in.endswith('.curry'):
      file_in = icurryFilename(file_in)
    assert file_in.endswith('.icy')
    file_out = file_in[:-4] + '.json'
    if self.do_zip:
      file_out += '.z'
    # Generate it.
    with binding(os.environ, 'CURRYPATH', ''):
      _makeOutputDir(file_out)
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
      json = _popen(cmd, pipecmd=cmd_compact)
      if self.do_zip:
        json = zlib.compress(json)
        mode = 'wb'
      else:
        mode = 'w'
      with open(file_out, mode) as output:
        output.write(json)
    return file_out

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

def icurryFilename(filename):
  '''Gets the ICurry file name associated with a Curry file.'''
  if filename.endswith('.z'):
    filename = filename[:-2]
  if filename.endswith('.icy'):
    return filename
  elif filename.endswith('.json'):
    return filename[:-5] + '.icy'
  elif not filename.endswith('.curry'):
    raise ValueError('bad suffix for %s' % filename)
  assert filename.endswith('.curry')
  path,name = os.path.split(filename)
  return os.path.join(path, '.curry', SUBDIR, name[:-6]+'.icy')

def jsonFilename(filename):
  '''Gets the JSON file name associated with a Curry or ICY file.'''
  if filename.endswith('.z'):
    filename = filename[:-2]
  if not filename.endswith('.icy'):
    filename = icurryFilename(filename)
  assert filename.endswith('.icy')
  return filename[:-4] + '.json'

def curryFilename(filename):
  '''
  Gets the Curry file associated with a JSON file or ICurry file.  If the input
  is a Curry file, it is returned.
  '''
  if filename.endswith('.z'):
    filename = filename[:-2]
  if filename.endswith('.curry'):
    return filename
  else:
    parts = filename.split(os.sep)
    if len(parts) < 3 or parts[-2] != SUBDIR or parts[-3] != '.curry':
      raise ValueError('bad path for %s' % filename)
    name = parts[-1]
    for suffix in ['.json', '.json.z', '.icy', '.icy.z']:
      if name.endswith(suffix):
        break
    else:
      raise ValueError('bad suffix for %s' % filename)
    return os.path.join(
        os.sep.join(parts[:-3])
      , name[:-len(suffix)]+'.curry'
      )

