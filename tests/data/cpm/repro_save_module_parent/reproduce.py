"""Saving a child of an ordinary module treats the parent as a mapping."""
from pathlib import Path
import tempfile
import curry

root = Path(__file__).resolve().parent
curry.reset(interpret='all', jit='off')
module = curry.import_(root / 'Family/Child.curry')
with tempfile.TemporaryDirectory() as work:
    curry.save(module, Path(work) / 'program', main='main')
