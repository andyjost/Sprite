'''
Code for finding and converting Curry source.

Contains functions for invoking the toolchain to build ICurry and module image
files.  The following file types are used:

::

  Suffix      External Tool    Description
  +--------   +--------------  +---------------------------------------
  .curry                       Curry source code.
  .icy        Curry front end  ICurry code in Curry format.  The front
                               end writes FlatCurry; the translation to
                               ICurry is built in (flat2icurry).  The
                               icurry program is the alternative.
  .img                         Runtime module image.
  .cpp                         Curry compiled to C++.
  .so         C++ compiler     C++ Curry compiled to a shared object.
'''

from ._curry2icurry import curry2icurry
from ._filenames import curryfilename, icurryfilename
from ._findcurry import currentfile
from ._loadcurry import loadcurry, loadicurry
from ._makecurry import compile_seconds, makecurry
from ._mergecurry import mergebuiltins, mergemodule, validatemodule
from ._str2module import str2module

__all__ = [
    'compile_seconds', 'currentfile', 'curry2icurry', 'curryfilename'
  , 'icurryfilename', 'loadcurry', 'loadicurry'
  , 'makecurry', 'mergebuiltins', 'mergemodule'
  ]
