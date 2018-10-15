def resolve(arg, keys, what):
  '''Resolves a name while allowing any non-ambiguous prefix.'''
  candidates = filter(lambda s: s.startswith(arg), keys)
  try:
    result, = candidates
  except ValueError:
    if candidates:
      raise ValueError("Ambiguous %s: '%s'\nCandidates are: %s"
          % (what, arg, ' '.join(map(repr, candidates)))
        )
    else:
      raise ValueError("Unknown %s: '%s'" % (what, arg))
  return result
