def split(fullname, modules=None, modulename=None):
  '''
  Split a full-qualified Curry name into the module and non-module parts.
  '''
  if modulename:
    assert fullname.startswith(modulename)
    return modulename, fullname[len(modulename)+1:]
  else:
    try:
      assert modules
    except:
      breakpoint()
    parts = fullname.split('.')
    for i in range(1, len(parts)):
      modulename = '.'.join(parts[:i])
      if modulename in modules:
        return modulename, '.'.join(parts[i:])
    assert False

