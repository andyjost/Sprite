from ...generic.compiler import ir
from .... import config

__all__ = ['IR']

class IR(ir.IR):
  CODETYPE = 'C++'
  from .render import render
