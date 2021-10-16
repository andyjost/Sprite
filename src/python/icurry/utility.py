
def splitname(name):
  parts = name.split('.')
  return parts[0], '.'.join(parts[1:])

def joinname(*parts):
  return '.'.join(parts)

