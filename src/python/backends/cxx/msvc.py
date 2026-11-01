"""Discover the x64 Visual Studio compiler environment, once per process."""
import logging
import os
import shutil
import subprocess
import sys
import threading

logger = logging.getLogger(__name__)
_lock = threading.Lock()
_result = None


def parse_environment(output):
  """Read cmd's set output, ignoring chatter and special drive variables."""
  result = {}
  for line in output.splitlines():
    name, separator, value = line.partition('=')
    if separator and name:
      result[name.upper()] = value
  return result


def _discover():
  clang = shutil.which('clang-cl')
  if os.environ.get('INCLUDE') and clang:
    logger.info('Visual Studio %s: environment from developer prompt',
                os.environ.get('VSINSTALLDIR', '(on PATH)'))
    return clang, {}
  root = os.environ.get('VSINSTALLDIR')
  if not root:
    installer = os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                             'Microsoft Visual Studio', 'Installer', 'vswhere.exe')
    found = subprocess.run(
        [installer, '-latest', '-products', '*', '-requires',
         'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
         '-property', 'installationPath'],
        capture_output=True, text=True, check=True)
    root = found.stdout.strip()
  if not root:
    raise ValueError('no Visual Studio installation found')
  script = os.path.join(root, 'VC', 'Auxiliary', 'Build', 'vcvars64.bat')
  if not os.path.exists(script):
    raise ValueError('vcvars64.bat is unavailable')
  captured = subprocess.run(
      [os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/u', '/c',
       'call "%s" >nul && set' % script],
      capture_output=True, text=True, encoding='utf-16-le', check=True)
  env = parse_environment(captured.stdout)
  clang = clang or shutil.which('clang-cl', path=env.get('PATH', ''))
  if not clang:
    candidate = os.path.join(root, 'VC', 'Tools', 'Llvm', 'x64', 'bin', 'clang-cl.exe')
    if os.path.exists(candidate):
      clang = candidate
  if not clang:
    raise ValueError('clang-cl is unavailable')
  if not env.get('INCLUDE') or not env.get('LIB'):
    raise ValueError('vcvars64 did not supply INCLUDE and LIB')
  logger.info('Visual Studio %s: environment from vcvars64.bat', root)
  return clang, env


def discover():
  """Return (clang-cl, environment overrides); cache success and failure."""
  global _result
  if sys.platform != 'win32':
    return None, {}
  with _lock:
    if _result is None:
      try:
        _result = _discover()
      except (OSError, subprocess.SubprocessError, ValueError) as exc:
        logger.info('Visual Studio discovery unavailable: %s', exc)
        _result = (None, {})
    return _result


def environment():
  """Merge the captured developer environment over the current environment."""
  env = os.environ.copy()
  env.update(discover()[1])
  return env
