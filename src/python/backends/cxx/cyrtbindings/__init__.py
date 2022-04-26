'''Python bindings for libcyrt.so.'''
from ._cyrtbindings import *
from . import fingerprint
import logging

logger = logging.getLogger(__name__)

def make_node(info, *args, **kwds):
  target = kwds.pop('target', None)
  partial = kwds.pop('partial', None)
  info = getattr(info, 'info', info)
  return Node.create(info, list(args), target, bool(partial))

