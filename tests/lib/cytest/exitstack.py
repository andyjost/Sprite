# Provides ExitStack and a nested() helper modelled on the old contextlib.nested.
from contextlib import ExitStack
import contextlib

@contextlib.contextmanager
def nested(*contexts):
  with ExitStack() as stack:
    [stack.enter_context(ctx) for ctx in contexts]
    yield contexts
