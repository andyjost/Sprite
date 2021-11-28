def resolve(arg, keys, what):
  '''Resolves a name while allowing any non-ambiguous prefix.'''
  candidates = filter(lambda s: s.startswith(arg), keys)
  try:
    result, = candidates
  except ValueError:
    if candidates:
      raise ValueError("Ambiguous %s: '%s'\nCandidates are: %s"
          % (what, arg, ' '.join(repr(x) for x in candidates))
        )
    else:
      raise ValueError("Unknown %s: '%s'" % (what, arg))
  return result
