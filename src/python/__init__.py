'''
An interactive Curry environment.

This module wraps an instance of ``curry.interpreter.Interpreter`` and provides
an API to interact with it.  To reset the interpreter, just reload this module.
'''
from . import interpreter

_interpreter_ = interpreter.Interpreter(flags={'defaultconverter':'topython'})
box = _interpreter_.box
compile = _interpreter_.compile
currytype = _interpreter_.currytype
eval = _interpreter_.eval
expr = _interpreter_.expr
flags = _interpreter_.flags
hnf = _interpreter_.hnf
import_ = _interpreter_.import_
module = _interpreter_.module
modules = _interpreter_.modules
nf = _interpreter_.nf
path = _interpreter_.path
symbol = _interpreter_.symbol
topython = _interpreter_.topython
type = _interpreter_.type
unbox = _interpreter_.unbox
