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
'''

from ._curry2icurry import curry2icurry
from ._filenames import curryfilename, icurryfilename, jsonfilenames
from ._findcurry import currentfile
from ._icurry2json import icurry2json
from ._json2tgt import json2tgt
from ._loadcurry import loadicurry, loadjson
from ._makecurry import makecurry
from ._mergecurry import mergebuiltins, mergemodule
from ._str2icurry import str2icurry

__all__ = [
    'currentfile', 'curry2icurry', 'curryfilename', 'icurry2json'
  , 'icurryfilename', 'json2tgt', 'jsonfilenames', 'loadicurry', 'loadjson'
  , 'makecurry', 'mergebuiltins', 'mergemodule'
  ]
