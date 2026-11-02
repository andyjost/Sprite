"""A namespace child must coexist with its built-in module parent."""
from pathlib import Path
from curry import interpreter

interp = interpreter.Interpreter(flags={'interpret': 'all', 'jit': 'off'})
interp.path.insert(0, str(Path(__file__).resolve().parent))
interp.import_('System.IO.Child')
