#!/bin/bash
# Rebuilds auto-generated content in this directory.

echo '.. code-block:: text'                       >  configure-usage.rst
echo ''                                           >> configure-usage.rst
../../../configure -h | perl -ple '$_ = "    $_"' >> configure-usage.rst
