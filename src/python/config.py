from .utility.currypath import clean_currypath
import logging
import os
import sys

logger = logging.getLogger(__name__)

def debugging():
  '''Indicates whether debugging is turned on.'''
  return 'SPRITE_DEBUG' in os.environ

if debugging():
  logger.info('Debugging is enabled because SPRITE_DEBUG is set.')

def interactive_modname():
  return 'sprite__interactive_'

class _Variable(object):
  def __init__(self, name, type=str, use_env=False):
    self.use_env = use_env
    self.name = name
    self.type = type
    self.value = None

  def __call__(self):
    if self.value is None:
      filename = os.path.join(os.environ['SPRITE_HOME'], 'sysconfig', self.name)
      assert os.path.exists(filename)
      self.value = self.convert(open(filename).read().strip('\n'))
      logger.debug(
          'Config %r read from file %r (%s: %r)'
        , self.name, filename, self.type.__name__, self.value
        )
    return self.value

  def convert(self, x):
    if self.type is bool:
      if x.strip().lower() in ('true', 'yes', 'on'):
        return True
      elif x.strip().lower() in ('false', 'no', 'off', ''):
        return False
      else:
        try:
          return bool(int(x))
        except:
          logger.warning(
              'Failed to interpret %r as an integer for configuration variable '
              '%s.  The feature will be disabled.  Please update Make.config.'
            , x, self.name.upper()
            )
          return False
    if self.use_env:
      x = str(x).format(**os.environ)
    return self.type(x)

# These are read from under $PREFIX/sysconfig.  The source files are under
# $ROOT/src/export/sysconfig.  They can be set in Make.config.
default_sprite_cache_file = _Variable('default_sprite_cache_file', use_env=True)
enable_icurry_cache       = _Variable('enable_icurry_cache', type=bool)
enable_parsed_json_cache  = _Variable('enable_parsed_json_cache', type=bool)
intermediate_subdir       = _Variable('intermediate_subdir')
python_package_name       = _Variable('python_package_name')
system_curry_path         = _Variable('system_curry_path')
currylib_version          = _Variable('currylib_version')
currylib_module_names     = _Variable('currylib_module_names')

def syslibs():
  return currylib_module_names().split()

def syslibversion():
  return tuple(map(int, currylib_version().split('.')))

def currypath(cached=[]):
  '''
  Gets the Curry path from the environment variable CURRYPATH and appends the
  system path.  By default, the result is cached.  To pick up possible changes
  to the environment, pass an empty list.
  '''
  if not cached:
    envpath = os.environ.get('CURRYPATH', '').split(':')
    syspath = system_curry_path().split(':')
    currypath = clean_currypath(envpath + syspath)
    cached.append(currypath)
    verify_syslibs()
  return cached[0]

def verify_syslibs():
  from .utility import filesys
  if 'SPRITE_DISABLE_SYSLIB_CHECKS' in os.environ:
    return
  cypath = currypath()
  syspath = system_curry_path().split(':')
  for name in syslibs():
    name = name + '.curry'
    found = list(filesys.findfiles(cypath, name))
    if not found or not (found[-1].startswith(p) for p in syspath):
      logger.critical('System library %r was not found in the CURRYPATH' % name)
      logger.critical('The CURRYPATH is %r' % ':'.join(cypath))
    elif not any(found[0].startswith(p) for p in syspath):
      logger.critical('System library %r is shadowed by a file from the CURRYPATH.' % name)
      logger.critical('The CURRYPATH is %r' % ':'.join(cypath))
      logger.critical('The system %r is %r' % (name, found[-1]))
      logger.critical('%r was found at %r' % (name, found[0]))
    else:
      continue
    logger.critical('Set SPRITE_DISABLE_SYSLIB_CHECKS to ignore')
    sys.exit(1)

# External tools.
def jq_tool(cached=[]):
  '''The jq tool, if it can be found.  Otherwise, None.'''
  if not cached:
    jq = os.path.join(os.environ['SPRITE_HOME'], 'tools', 'jq')
    cached.append(jq if os.path.exists(jq) else None)
  return cached[0]

def icurry_tool(cached=[]):
  if not cached:
    path = os.path.join(os.environ['SPRITE_HOME'], 'tools', 'icurry')
    path = os.path.abspath(path)
    cached.append(path)
  return cached[0]

def icurry2jsontext_tool(cached=[]):
  if not cached:
    path = os.path.join(os.environ['SPRITE_HOME'], 'tools', 'icurry2jsontext')
    path = os.path.abspath(path)
    cached.append(path)
  return cached[0]

