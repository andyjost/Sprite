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
      if x == 'True':
        return True
      elif x == 'False':
        return False
      else:
        return bool(int(x))
    else:
      text = self.type(x)
      if self.interpolate:
        assert self.type is str
        text = text.format(**os.environ)
      return text

# These are read from under $PREFIX/vars.  The source files are under
# $ROOT/src/export/vars.  They can be set in Make.config.
default_sprite_cache_file = _Variable('default_sprite_cache_file', interpolate=True)
enable_icurry_cache       = _Variable('enable_icurry_cache', type=bool)
enable_parsed_json_cache  = _Variable('enable_parsed_json_cache', type=bool)
intermediate_subdir       = _Variable('intermediate_subdir')
python_package_name       = _Variable('python_package_name')

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

  
