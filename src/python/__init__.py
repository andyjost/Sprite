'''
An interactive Curry environment.

This module wraps an instance of ``curry.interpreter.Interpreter`` and provides an
API to interact with it.
'''
from . import interpreter

_i = interpreter.Interpreter()
box = _i.box
eval = _i.eval
expr = _i.expr
flags = _i.flags
hnf = _i.hnf
import_ = _i.import_
module = _i.module
modules = _i.modules
nf = _i.nf
path = _i.path
symbol = _i.symbol
type = _i.type
unbox = _i.unbox

# del _i, interpreter
