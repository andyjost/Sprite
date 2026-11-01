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
_lookup_result = None


def parse_environment(output):
  """Read cmd's set output, ignoring chatter and special drive variables."""
  result = {}
  for line in output.splitlines():
    name, separator, value = line.partition('=')
    if separator and name:
      result[name.upper()] = value
  return result


def _initialized_prompt():
  return (os.environ.get('INCLUDE')
          and os.environ.get('VSCMD_ARG_TGT_ARCH', 'x64').lower() == 'x64')


def _lookup():
  clang = shutil.which('clang-cl')
  if _initialized_prompt():
    return clang, None
  root = os.environ.get('VSINSTALLDIR')
  if not root:
    installer = os.path.join(os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
                             'Microsoft Visual Studio', 'Installer', 'vswhere.exe')
    found = subprocess.run(
        [installer, '-latest', '-products', '*', '-requires',
         'Microsoft.VisualStudio.Component.VC.Tools.x86.x64',
         '-property', 'installationPath', '-utf8'],
        capture_output=True, text=True, encoding='utf-8', check=True,
        timeout=120)
    root = found.stdout.strip()
  if not root:
    raise ValueError('no Visual Studio installation found')
  if not clang:
    candidate = os.path.join(root, 'VC', 'Tools', 'Llvm', 'x64', 'bin', 'clang-cl.exe')
    if os.path.exists(candidate):
      clang = candidate
  return clang, root


def _lookup_cached():
  global _lookup_result
  if _lookup_result is None:
    try:
      _lookup_result = _lookup()
    except (OSError, subprocess.SubprocessError, ValueError) as exc:
      logger.info('Visual Studio discovery unavailable: %s', exc)
      _lookup_result = (None, None)
  return _lookup_result


def compiler():
  """Look up clang-cl without running the developer environment script."""
  if sys.platform != 'win32':
    return None
  with _lock:
    return _lookup_cached()[0]


def _discover():
  if _initialized_prompt():
    logger.info('Visual Studio%s: environment from developer prompt',
                ' ' + os.environ['VSINSTALLDIR'] if os.environ.get('VSINSTALLDIR') else '')
    return shutil.which('clang-cl'), {}
  clang, root = _lookup_cached()
  if not root:
    return clang, {}
  script = os.path.join(root, 'VC', 'Auxiliary', 'Build', 'vcvars64.bat')
  if not os.path.exists(script):
    raise ValueError('vcvars64.bat is unavailable')
  captured = subprocess.run(
      [os.environ.get('COMSPEC', 'cmd.exe'), '/d', '/u', '/c',
       'call', script, '>nul', '&&', 'set'],
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
      encoding='utf-16-le', errors='replace', check=True, timeout=120)
  env = parse_environment(captured.stdout)
  clang = clang or shutil.which('clang-cl', path=env.get('PATH', ''))
  if not clang:
    raise ValueError('clang-cl is unavailable')
  if not env.get('INCLUDE') or not env.get('LIB'):
    raise ValueError('vcvars64 did not supply INCLUDE and LIB')
  # Make the selected compiler visible to children that reuse this prompt.
  if not shutil.which('clang-cl', path=env.get('PATH', '')):
    env['PATH'] = os.path.dirname(clang) + os.pathsep + env.get('PATH', '')
  logger.info('Visual Studio %s: environment from vcvars64.bat', root)
  return clang, {k: v for k, v in env.items() if os.environ.get(k) != v}


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
