from .... import context
from . import compile, misc, materialize

__all__ = ['Compiler']

class Compiler(context.Compiler):
  @property
  def IR(self):
    return misc.IR

  @property
  def compile(self):
    return compile.compile

  @property
  def materialize(self):
    return materialize.materialize

