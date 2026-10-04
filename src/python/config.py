'''
Code related to the configuration of Sprite.
'''

###############################
# Logging set-up.
import logging, os, sys

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
  if isinstance(level, str) and level in log_level_names():
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

def expression_modname(n):
  '''
  The name of the module that holds compiled expression number ``n``.  Each
  expression gets its own name: the C++ backend resolves a module's symbols
  against the same-named module loaded first, so two expression modules must
  never share a name.
  '''
  return 'sprite__expression_%d' % n

def is_expression_modname(name):
  return name.startswith('sprite__expression_')

def is_anonymous_modname(name):
  '''
  Tells whether ``name`` belongs to an anonymous module: an interactive module
  compiled without a name, or an expression module.  curry.compile numbers
  these per process, so the same text gets another name in another process.
  The ICurry cache leaves the name out of its key for these modules.
  '''
  return name.startswith(interactive_modname()) or is_expression_modname(name)

class _Variable(object):
  def __init__(self, name, type=str, use_env=False):
    self.use_env = use_env
    self.name = name
    self.type = type
    self.value = None

  def __call__(self):
    if self.value is None:
      filename = installed_path('sysconfig', self.name)
      assert os.path.exists(filename)
      with open(filename) as istream:
        self.value = self.convert(istream.read().strip('\n'))
      logger.debug(
          'Config %r read from file %r (%s: %r)'
        , self.name, filename, self.type.__name__, self.value
        )
    return self.value

  def convert(self, x):
    from .utility.strings import ensure_str
    x = ensure_str(x)
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
# The name of the subdirectory of .curry into which the Curry front end
# writes FlatCurry.  It names the front end, e.g., pakcs-3.4.1.
frontend_subdir           = _Variable('frontend_subdir')
# The options passed to the Curry front end after the output directory and
# the search path, as one string.
frontend_flags            = _Variable('frontend_flags')
# The route from Curry to ICurry chosen at configuration time: 'frontend' or
# 'icurry'.  Empty when configure left the choice open.
default_curry2icurry_tool = _Variable('curry2icurry_tool')
# The name of the top-level Python package.  By default, 'curry'.
python_package_name       = _Variable('python_package_name')
# The version of the Curry library.  It names the PAKCS release whose library
# Sprite ships under curry/lib.  Some tests key their expectations on it.
currylib_version          = _Variable('currylib_version')
# The names of all modules in the system Curry library, the Prelude first.
currylib_module_names     = _Variable('currylib_module_names')
# The names of the system library modules that Sprite cannot compile.  See
# CURRYLIB_UNSUPPORTED_MODULES in Make.include.
currylib_unsupported_modules = _Variable('currylib_unsupported_modules')
# The name of the default backend.
default_backend           = _Variable('default_backend')
# The location of ld.so.
ld_interpreter_path       = _Variable('ld_interpreter_path')


def syslibs():
  '''
  The names of the modules of the system Curry library.  Each one is found as
  a source under :func:`system_curry_path`.
  '''
  return currylib_module_names().split()

def unsupported_syslibs():
  '''
  The names of the system library modules that Sprite cannot compile: their
  externals have no implementation in a backend, they import such a module,
  or the importer cannot load them.  See CURRYLIB_UNSUPPORTED_MODULES in
  Make.include.
  '''
  return currylib_unsupported_modules().split()

def supported_syslibs():
  '''
  The names of the system library modules that Sprite compiles, the Prelude
  first: :func:`syslibs` without :func:`unsupported_syslibs`.  The
  installation compiles them for both backends.
  '''
  unsupported = set(unsupported_syslibs())
  return [name for name in syslibs() if name not in unsupported]

def syslibversion():
  return tuple(int(x) for x in currylib_version().split('.'))

def prefix():
  return os.environ['SPRITE_HOME']

def force_recompile_cxx():
  return os.environ.get('SPRITE_FORCE_RECOMPILE_CXX', False)

def cxx_pch_root():
  '''
  The directory under which the C++ backend keeps its precompiled header.
  Returns None when the header is disabled.

  By default the header lives beside the installed headers, where the C++
  compiler finds it with no extra flag.  SPRITE_CXX_PCH_ROOT names another
  directory.  Set it to the empty string to compile without the header.
  '''
  root = os.environ.get('SPRITE_CXX_PCH_ROOT')
  if root is None:
    return installed_path('include')
  root = root.strip()
  return os.path.abspath(root) if root else None

# The path to system Curry files, such as the Prelude.  This is appended to
# whatever the user might supply via the CURRYPATH environment variable.
def system_curry_path():
  return os.path.join(prefix(), 'curry')

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

def installed_path(*relpath):
  return os.path.join(prefix(), *relpath)

# External tools and libraries.
def cxx_tool(cached=[]):
  '''The C++ compiler used with the cxx backend.'''
  if not cached:
    cxx = installed_path('tools', 'cxx')
    cached.append(cxx if os.path.exists(cxx) else None)
  return cached[0]

def curry_frontend(cached=[]):
  '''The Curry front end, if it is configured.  Otherwise, None.'''
  if not cached:
    path = installed_path('tools', 'curry-frontend')
    cached.append(os.path.abspath(path) if os.path.exists(path) else None)
  return cached[0]

def icurry_tool(cached=[]):
  '''The icurry program, if it is configured.  Otherwise, None.'''
  if not cached:
    path = installed_path('tools', 'icurry')
    cached.append(os.path.abspath(path) if os.path.exists(path) else None)
  return cached[0]

# The names of the routes from Curry to ICurry.
CURRY2ICURRY_TOOLS = 'frontend', 'icurry'

def curry2icurry_tool(name=None):
  '''
  The name of the route from Curry to ICurry.  ``frontend`` runs the Curry
  front end and the built-in translation; ``icurry`` runs the icurry program.

  Args:
    name:
        A name given by the caller.  It wins when it is not None.

  The environment variable SPRITE_CURRY2ICURRY comes next, then the choice of
  configure, then whichever tool is installed, the front end first.
  '''
  if name is None:
    name = os.environ.get('SPRITE_CURRY2ICURRY') or default_curry2icurry_tool()
  if not name:
    if curry_frontend() is not None:
      name = 'frontend'
    elif icurry_tool() is not None:
      name = 'icurry'
    else:
      raise ValueError(
          'no route from Curry to ICurry is configured; rerun configure'
        )
  if name not in CURRY2ICURRY_TOOLS:
    raise ValueError(
        'the Curry-to-ICurry tool should be one of %s, not %r'
            % (', '.join(repr(x) for x in CURRY2ICURRY_TOOLS), name)
      )
  return name

def python_exe(cached=[]):
  if not cached:
    path = installed_path('bin', 'python')
    path = os.path.abspath(path)
    cached.append(path)
  return cached[0]

def sprite_exec(cached=[]):
  if not cached:
    path = installed_path('bin', 'sprite-exec')
    path = os.path.abspath(path)
    cached.append(path)
  return cached[0]


def cyrt_lib(cached=[]):
  if not cached:
    path = installed_path('lib', 'libcyrt.so')
    path = os.path.abspath(path)
    assert os.path.exists(path)
    cached.append(path)
  return cached[0]

