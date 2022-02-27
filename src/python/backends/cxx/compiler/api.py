from .... import context
from .. import cyrt
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
  def materialize_function(self):
    return materialize.materialize

  @property
  def materialize_function_info_stub(self):
    return materialize.materialize_info_stub

  @property
  def materialize_type(self):
    return materialize.materialize_type

  @property
  def render(self):
    return render.render
