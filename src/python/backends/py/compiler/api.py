from .... import context
from . import compile, ir, materialize, render, synthesize

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
    return synthesize.synthesize_function_info_stub

  @property
  def synthesize_type(self):
    return synthesize.synthesize_type
