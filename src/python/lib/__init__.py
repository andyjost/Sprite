'''
Implements import hacking to load Curry modules into Python.

Any name imported relative to this package is considered to be a Curry module.
It will be located using CURRYPATH and imported into ``curry._i`` via the
``import_`` method.
'''
import sys
from .. import importer
sys.meta_path.insert(0, importer.CurryImporter())
del importer, sys # Leave it empty so that imported Curry moduels cannot clash.

