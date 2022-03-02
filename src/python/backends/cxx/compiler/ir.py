from ...generic.compiler import ir

class IR(ir.IR):
  CODETYPE = 'C++'
  from .render import render

