from __future__ import absolute_import

'''
Implementation of sprite-make.

Contains functions for invoking the toolchain to build ICurry and ICurry-JSON
files.  The following file types are used:

  Suffix      Ext. Tool        Description
  +-------    +----------      +---------------------------------------
  .curry                       Curry source code.
  .icy        icurry           ICurry code in Curry format.
  .json[.z]   icurry2jsontext  ICurry code in JSON format [compressed].
'''

from .exceptions import CompileError, ModuleLookupError, PrerequisiteError
from . import cache
from . import config
from . import utility
from .utility.binding import binding, del_
from .utility import filesys
import errno
import logging
import os
from .programs.utility import make_exception
import shutil
import subprocess
import sys
import tempfile
import time
import types
import zlib

__all__ = ['curryFilename', 'icurryFilename', 'jsonFilename', 'updateTarget']

logger = logging.getLogger(__name__)
SUBDIR = config.intermediate_subdir()

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

def _selectPrerequisite(
    name, currypath, is_sourcefile=False, json=True, **ignored
  ):
  '''
  Searches for the current prerequisite used to get ICurry.  The file returned
  is the newest among the Curry source file (suffix: .curry), the ICurry file
  (suffix: .icy), and the JSON file (suffix: .json.z).

  Parameters:
  -----------
  ``name``
      The module name or source file name.
  ``currypath``
      A sequence of paths to search (i.e., CURRYPATH split on ':').
  ``is_sourcefile``
      If true, the name arguments is interpreted as a source file.  Otherwise,
      it is interpreted as a module name.
  ``json``
      Whether to include JSON files in the search.  Setting this to false can
      be used when targeting .icy as the output.

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
      raise ModuleLookupError('"%s" is not a legal module name.' % name)
    # Search for the JSON file first, then ICurry, then .curry.
    suffixes = ['.json', '.json.z', '.icy'] if json else ['.icy']
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
  icyfile = icurryFilename(curryfile)
  filelist = [curryfile, icyfile]
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

def updateTarget(name, currypath=[], **kwds):
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
  if do_icy:
    intermediates = []
    prereq = _selectPrerequisite(name, currypath, json=do_json, **kwds)
    if prereq.endswith('.curry'):
      prereq = curry2icurry(prereq, currypath, **kwds)
      assert prereq.endswith('.icy')
      intermediates.append(prereq)
    if do_json:
      try:
        return icurry2json(prereq, currypath, **kwds)
      finally:
        if do_tidy:
          for intermediate in intermediates:
            logger.debug('Removing intermediate %r', intermediate)
            os.unlink(intermediate)
  if not intermediates:
    logger.debug('Nothing to do for %r -> %r', name, prereq)


def _popen(cmd, stdin=None, pipecmd=None):
  '''
  Invokes the given command and returns its stdout as a string.  A second
  pipeline stage may be provided.
  '''
  child = subprocess.Popen(cmd, stdin=stdin, stdout=subprocess.PIPE)
  if pipecmd:
    term = subprocess.Popen(pipecmd, stdin=child.stdout, stdout=subprocess.PIPE)
    child.stdout.close()
  else:
    term = child
  try:
    stdout,_ = term.communicate()
    retcode = term.wait()
  except:
    term.kill()
    raise
  if retcode:
    raise CompileError('while running %s' % ' '.join(cmd))
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
          'Command: %s %s> %s'
        ,  ' '.join(cmd)
        , '| %s ' % ' '.join(cmd_compact) if cmd_compact else ''
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

