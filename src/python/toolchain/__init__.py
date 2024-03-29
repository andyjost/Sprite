'''
Code for finding and converting Curry source.

Contains functions for invoking the toolchain to build ICurry and ICurry-JSON
files.  The following file types are used:

::

  Suffix      External Tool    Description
  +--------   +--------------  +---------------------------------------
  .curry                       Curry source code.
  .icy        icurry           ICurry code in Curry format.
  .json[.z]                    ICurry code in JSON format [compressed].
  .py                          Curry compiled to Python.
  .cpp                         Curry compiled to C++.
  .so         C++ compiler     C++ Curry compiled to a shared object.
'''

from ._curry2icurry import curry2icurry
from ._filenames import curryfilename, icurryfilename, jsonfilenames
from ._findcurry import currentfile
from ._icurry2json import icurry2json
from ._loadcurry import loadcurry, loadjson
from ._makecurry import makecurry
from ._mergecurry import mergebuiltins, validatemodule
from ._str2module import str2module

__all__ = [
    'currentfile', 'curry2icurry', 'curryfilename', 'icurry2json'
  , 'icurryfilename', 'jsonfilenames', 'loadcurry', 'loadjson'
  , 'makecurry', 'mergebuiltins', 'mergemodule'
  ]
