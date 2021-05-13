from . import compile
from .... import context

class Compiler(context.Compiler):
  @property
  def compile_function(self):
    return compile.compile_function

