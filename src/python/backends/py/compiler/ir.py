from ...generic.compiler import ir
from .... import config

__all__ = ['IR']

class IR(ir.IR):

  CODETYPE = 'Python'

  from .render import render

  def header(self):
    return '#!%s\n' % config.python_exe()
