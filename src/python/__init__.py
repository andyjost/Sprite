'''
An interactive Curry environment.

This module wraps an instance of ``curry.interpreter.Interpreter`` and provides an
API to interact with it.
'''
from . import interpreter

_interp = interpreter.Interpreter(flags={'defaultconverter':'topython'})
box = _interp.box
compile = _interp.compile
eval = _interp.eval
expr = _interp.expr
flags = _interp.flags
hnf = _interp.hnf
import_ = _interp.import_
module = _interp.module
modules = _interp.modules
nf = _interp.nf
path = _interp.path
symbol = _interp.symbol
type = _interp.type
unbox = _interp.unbox
tocurry = _interp.tocurry
topython = _interp.topython

del interpreter
