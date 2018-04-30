'''
Implements partial function application.
'''
from . import runtime

def apply_impl(interpreter, partapplic, arg):
  missing, term = partapplic # note: "missing" is unboxed.
  assert missing >= 1
  if missing == 1:
    yield term.info
    for t in term.successors:
      yield t
    yield arg
  else:
    yield partapplic.info
    yield missing-1
    yield runtime.Node(term.info, *(term.successors+[arg]))

