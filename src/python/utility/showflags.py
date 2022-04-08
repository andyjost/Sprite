from .. import common

def showflags(flagvalue):
  parts = []
  for name, value in common.BITFLAGS.items():
    if isinstance(name, str):
      if flagvalue & value:
        flagvalue = flagvalue &~ value
        parts.append(name)
  stem = common.FLAGS.get(flagvalue, flagvalue)
  if stem:
    parts.insert(0, stem)
  if not parts:
    parts = [0]
  return ' | '.join(str(p) for p in parts)

