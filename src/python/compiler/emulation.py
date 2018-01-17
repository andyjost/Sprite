'''
A pure-Python Curry emulator.
'''

from .visitation import dispatch
from .icurry import *
import collections

class Emulator(object):
  '''
  Implements a Curry emulator.

  Use ``compile`` to add modules, types, and function definitions to the
  system.  Then use ``eval`` to evaluate expressions.
  '''
  def __new__(cls):
    self = object.__new__(cls)
    return self

  @dispatch.on('node')
  def compile_(self, node):
    raise RuntimeError('unhandled node')

  @compile_.when(collections.Sequence)
  def compile_(self, seq):
    for item in seq:
      self.compile_(item)

  @compile_.when(IModule)
  def compile_(self, node):
    print "compiling module", node.name
