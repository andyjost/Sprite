from .... import context
from .... import _sprite
from . import compile, ir, materialize, render

__all__ = ['Compiler']

class Compiler(context.Compiler):
  @property
  def IR(self):
    return ir.IR

  @property
  def compile(self):
    return compile.compile

  @property
  def materialize(self):
    return materialize.materialize

  @property
  def render(self):
    return render.render
