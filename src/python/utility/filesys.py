import os

def getdir(name, mkdirs=False, access=os.O_RDWR):
  '''
  Creates or gets a directory and ensures it has the specified access rights.
  '''
  path = os.path.abspath(name)
  if not os.path.exists(path):
    if mkdirs:
      os.makedirs(path)
    else:
      os.mkdir(path)
  elif not os.path.isdir(path):
    raise RuntimeError("%s exists but is not a directory" % path)
  if not os.access(path, access):
    aname = [k for k,v in os.__dict__.items() if k.startswith('O_') and v == access]
    aname = aname[0] if len(aname) else '(invalid)'
    raise RuntimeError("%s does not have %s access" % (path, aname))
  return path

