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

  @property
  def synthesize_function_info_stub(self):
    return _sprite.synthesize_function_info_stub
    assert False

  @property
  def synthesize_type(self):
    return _sprite.synthesize_type
