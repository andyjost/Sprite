"""A qualified module must not shadow an unqualified import of its basename."""
from pathlib import Path
from curry import interpreter

root = Path(__file__).resolve().parent
interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
interp.path[:0] = [str(root / 'src'), str(root / 'deps')]
interp.import_('Parent.Leaf')
