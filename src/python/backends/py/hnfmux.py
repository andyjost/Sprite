def demux(hnf_calls):
  '''
  Separates a sequence of calls to hnf into the arguments and guards.
  '''
  hnf_calls = list(hnf_calls)
  if hnf_calls:
    args, guards = zip(*hnf_calls)
    guards = set.union(*guards)
    # TODO: find every place where this can occur in a built-in function and
    # update as needed.
    if guards:
      breakpoint()
    return args, guards
  else:
    return [], set()

