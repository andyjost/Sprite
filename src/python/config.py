'''
Code related to the configuration of Sprite.
'''

###############################
# Logging set-up.
import logging, os, six, sys

_LOG_FILE_ = os.environ.get('SPRITE_LOG_FILE', '-')
_LOG_LEVEL_NAME_ = os.environ.get('SPRITE_LOG_LEVEL', 'WARNING').upper()
_LOG_LEVEL_NAMES_ = 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'
_LOG_LEVEL_VALUES_ = tuple(getattr(logging, s) for s in _LOG_LEVEL_NAMES_)
if _LOG_LEVEL_NAME_ not in _LOG_LEVEL_NAMES_:
  raise EnvironmentError(
      'SPRITE_LOG_LEVEL should be one of %s or %r, not %r' % (
          ', '.join(repr(x) for x in _LOG_LEVEL_NAMES_[:-1])
        , _LOG_LEVEL_NAMES_[-1]
        , _LOG_LEVEL_NAME_
        )
    )
else:
  _LOG_LEVEL_ = getattr(logging, _LOG_LEVEL_NAME_)

logging.basicConfig(
    level=_LOG_LEVEL_
  , format='%(asctime)s [%(levelname)s] %(message)s'
  , datefmt='%m/%d/%Y %H:%M:%S'
  , **({'filename': _LOG_FILE_} if _LOG_FILE_ not in ['-', ''] else {})
  )

logger = logging.getLogger(__name__)

# Logging query API.

def log_file_name():
  return _LOG_FILE_

def log_level():
  return _LOG_LEVEL_

def log_level_names():
  return _LOG_LEVEL_NAMES_

def log_level_map():
  return dict(zip(_LOG_LEVEL_NAMES_, _LOG_LEVEL_VALUES_))

def logging_enabled_for(level):
  if isinstance(level, six.string_types) and level in log_level_names():
    level = log_level_map()[level]
  if level not in _LOG_LEVEL_VALUES_:
    raise ValueError('logging level %r is not valid')
  return level <= _LOG_LEVEL_

###############################
# Debugging set-up.

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
      with open(filename) as istream:
        self.value = self.convert(istream.read().strip('\n'))
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
# $ROOT/src/export/sysconfig.  They can be set in Make.config.  This machanism
# is essentially a way of passing information contained in Make variables to
# the Sprite runtime.

# The default location of the cache file.
default_sprite_cache_file = _Variable('default_sprite_cache_file', use_env=True)
# Whether to enable caching (by default).
enable_icurry_cache       = _Variable('enable_icurry_cache', type=bool)
# Whether to cache parsed JSON.  The stored objects are pickled Python.
enable_parsed_json_cache  = _Variable('enable_parsed_json_cache', type=bool)
# The name of the subdirectory of .curry in which to place Sprite files.
intermediate_subdir       = _Variable('intermediate_subdir')
# The name of the top-level Python package.  By default, 'curry'.
python_package_name       = _Variable('python_package_name')
# The path to system Curry files, such as the Prelude.  This is appended to
# whatever the user might supply via the CURRYPATH environment variable.
system_curry_path         = _Variable('system_curry_path')
# The version of the Curry library.  Corresponds with a PAKCS version, since
# that is where the Prelude is taken from.
currylib_version          = _Variable('currylib_version')
# The names of all files in the system Curry library.
currylib_module_names     = _Variable('currylib_module_names')
# The name of the default backend.
default_backend           = _Variable('default_backend')

def syslibs():
  return currylib_module_names().split()

def syslibversion():
  return tuple(int(x) for x in currylib_version().split('.'))

def currypath(reset=False, cache=[]):
  '''
  Gets the Curry path from the environment variable CURRYPATH and appends the
  system path.

  Args:
    reset:
      If true, the cache will be cleared and the Curry path reloaded from the
      environment.

    cache:
      A list into which the Cury path is cached.
  '''
  if reset:
    cache[:] = ()
  if not cache:
    from .utility import curryname
    envpath = os.environ.get('CURRYPATH', '').split(':')
    syspath = system_curry_path().split(':')
    currypath = curryname.makeCurryPath(envpath + syspath)
    cache.append(currypath)
    verify_syslibs()
  return cache[0]

def verify_syslibs():
  from .utility import filesys
  if 'SPRITE_DISABLE_SYSLIB_CHECKS' in os.environ:
    return
  cypath = currypath()
  syspath = system_curry_path().split(':')
  for name in syslibs():
    name = name.replace('.', os.sep) + '.curry'
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

def python_exe(cached=[]):
  if not cached:
    path = os.path.join(os.environ['SPRITE_HOME'], 'bin', 'python')
    path = os.path.abspath(path)
    cached.append(path)
  return cached[0]

