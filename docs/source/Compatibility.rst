Compatibility
=============

Sprite was developed and tested with the following software:

- Ubuntu Linux 16.04.6 LTS
- Python 2.7.18, 3.5.2, 3.9.4
- PAKCS 3.4.1
- ICurry Compiler (Version of 28/07/21)
- SWI Prolog 8.0
- Curry Package Manger 3.1.0
- gcc 7.4.0

Known compatibility problems are discussed below.

PAKCS
-----

The Curry Prelude is obtained from PAKCS.  Sprite relies on the internal
interface of the Prelude, which, unfortunately, is not stable.  Because of
this, Sprite will almost certainly not work with any other version of PAKCS.


ICurry
------

The output of ICurry is historically unstable.  Sprite will not work with older
(and possibly newer) versions of ICurry.


Python
------

Although Python 2 has reached its end-of-life, it is still actively used.
Sprite works with the final version of Python 2, namely 2.7.18.  Older versions
(in particular 2.7.12) fail to build due to incompatibilities with pybind11.


