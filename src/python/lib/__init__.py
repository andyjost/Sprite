'''
Implements import hacking to load Curry modules into Python.

Any name imported relative to this package is considered to be a Curry module.
It will be located using CURRYPATH and imported into the global interpreter via
``import_``.
'''
from ..import_hook import CurryImportHook
import sys
sys.meta_path.insert(0, CurryImportHook())
del CurryImportHook, sys # Leave it empty so that imported Curry moduels cannot clash.

