'''The build tools of this tree, for the tests that drive them.'''
import os, shutil

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))

def cmake_executable(build=None):
  '''
  The cmake of this tree's build (CMAKE_COMMAND of its cache), or the one on
  PATH; None when there is neither.  A test that needs cmake skips on None.
  '''
  cache = os.path.join(build or os.path.join(ROOT, 'object-root', 'cmake'), 'CMakeCache.txt')
  try:
    with open(cache) as stream:
      for line in stream:
        if line.startswith('CMAKE_COMMAND:INTERNAL='):
          path = line.split('=', 1)[1].strip()
          if os.access(path, os.X_OK):
            return path
  except OSError:
    pass
  return shutil.which('cmake')


def runtime_test_command(source, target):
  """Compile a standalone test against the installed Windows runtime."""
  from curry import config
  from curry.backends.cxx import toolchain
  return [config.cxx_tool()] + toolchain.MSVC_FLAGS + toolchain.gc_flags() + [
      '/O2', '/I' + config.installed_path('include'), source,
      '/Fe' + target, '/Fo' + os.path.splitext(target)[0] + '.obj',
      '/link', '/LIBPATH:' + config.installed_path('lib'), 'libcurryrt.lib']


def runtime_test_environment():
  """Let standalone Windows executables find the runtime DLL."""
  if os.name != 'nt':
    return None
  from curry import config
  return dict(os.environ, PATH=config.installed_path('lib') + os.pathsep +
      os.environ.get('PATH', ''))
