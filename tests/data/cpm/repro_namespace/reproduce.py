"""An earlier namespace must not hide a later module of the same name."""
from pathlib import Path
from curry import interpreter

root = Path(__file__).resolve().parent
interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
interp.path[:0] = [str(root / 'early'), str(root / 'late')]
module = interp.import_('Consumer')
print(list(interp.eval(module.answer)))
