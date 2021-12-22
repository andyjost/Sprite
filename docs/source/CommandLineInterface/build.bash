#!/bin/bash
# Rebuilds auto-generated content in this directory.

# sprite-make (usage)
echo '.. code-block:: text'                                     >  sprite-make-usage.rst
echo ''                                                         >> sprite-make-usage.rst
../../../install/bin/sprite-make -h | perl -ple '$_ = "    $_"' >> sprite-make-usage.rst

# sprite-make (man)
../../../install/bin/sprite-make --man --no-header --with-rst   >  sprite-make-man.rst


# sprite-exec (usage)
echo '.. code-block:: text'                                     >  sprite-exec-usage.rst
echo ''                                                         >> sprite-exec-usage.rst
../../../install/bin/sprite-exec -h | perl -ple '$_ = "    $_"' >> sprite-exec-usage.rst
