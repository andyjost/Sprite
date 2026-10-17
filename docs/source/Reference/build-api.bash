#!/bin/bash
set -eu
# The Reference describes the installed public package.
rm -f curry.*.rst curry.*.rst.rej
../../../install/bin/python - <<'PY'
from pathlib import Path
import curry

Path('curry.rst').write_text('''curry package
=============

The :download:`public surface <../../../src/python/__init__.pyi>` is
installed beside the package as ``curry/__init__.pyi``. It records the
names and signatures available in this version.

.. automodule:: curry
   :members: %s
   :show-inheritance:
   :undoc-members:
''' % ', '.join(curry.__all__), encoding='utf-8')
PY
