import logging
import os

logger = logging.getLogger(__name__)

def debugging():
  '''Indicates whether debugging is turned on.'''
  return 'SPRITE_DEBUG' in os.environ

if debugging():
  logger.info('Debugging is enabled because SPRITE_DEBUG is set.')

def interactive_modname():
  return 'sprite__interactive_'

class _Variable(object):
  def __init__(self, name, type=str, interpolate=False):
    self.interpolate = interpolate
    self.name = name
    self.type = type
    self.value = None

  def __call__(self):
    if self.value is None:
      filename = os.path.join(os.environ['SPRITE_HOME'], 'vars', self.name)
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
    else:
      if self.interpolate:
        x = str(x).format(**os.environ)
      return self.type(x)

# These are read from under $PREFIX/vars.  The source files are under
# $ROOT/src/export/vars.  They can be set in Make.config.
default_sprite_cache_file = _Variable('default_sprite_cache_file', interpolate=True)
enable_icurry_cache       = _Variable('enable_icurry_cache', type=bool)
enable_parsed_json_cache  = _Variable('enable_parsed_json_cache', type=bool)
intermediate_subdir       = _Variable('intermediate_subdir')
python_package_name       = _Variable('python_package_name')
system_curry_path         = _Variable('system_curry_path')

def currypath(cached=[]):
  '''
  Gets the Curry path from the environment variable CURRYPATH and appends the
  system path.  By default, the result is cached.  To pick up possible changes
  to the environment, pass an empty list.
  '''
  if not cached:
    envpath = os.environ.get('CURRYPATH', '').split(':')
    syspath = system_curry_path().split(':')
    cached.append(filter(lambda x:x, envpath + syspath))
  return cached[0]

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

  
