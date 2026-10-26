'''Optional source preprocessors named by a Curry module's pragma.'''
import os, re, shlex, shutil

PRAGMA = re.compile(
    r'\{-#\s*OPTIONS_(?:CYMAKE|FRONTEND)\b(.*?)#-\}', re.DOTALL
  )


def preprocessor(filename):
  '''The tool named by --pgmF in an OPTIONS pragma, or None.'''
  try:
    with open(filename, errors='replace') as stream:
      source = stream.read()
  except OSError:
    return None
  for pragma in PRAGMA.finditer(source):
    try:
      options = iter(shlex.split(pragma.group(1)))
      for option in options:
        if option.startswith('--pgmF='):
          return option.partition('=')[2] or None
        if option == '--pgmF':
          return next(options, None)
    except ValueError:
      continue
  return None


def missing(filename, path=None):
  '''A diagnostic when the source needs an unavailable tool, else None.'''
  tool = preprocessor(filename)
  if tool and shutil.which(tool, path=path) is None:
    return '%s needs the preprocessor %s, which is not on PATH.' % (
        os.path.basename(filename), tool
      )
  return None
