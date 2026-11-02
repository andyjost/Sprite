"""The base package's source copies conflict with reserved library names."""
from pathlib import Path
from curry import interpreter

root = Path(__file__).resolve().parent
interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
interp.import_(str(root / 'Numeric.curry'), is_sourcefile=True)
