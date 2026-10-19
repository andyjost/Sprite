.. highlight:: bash

Building Documentation
======================

The user guide of ``master`` is published at
https://andyjost.github.io/Sprite/. To build the guide of your checkout,
stage the package and run Sphinx through the wrapper::

    make stage
    python scripts/check-prereqs.py --doc
    make -C docs html

Install Sphinx and sphinx_rtd_theme in the build Python's environment when
the diagnostic reports them missing. The wrapper regenerates the Reference
from the installed package and command help from the staged tools, then
builds HTML with warnings treated as errors. The output is
``object-root/docs/html``. ``make docs`` builds HTML and then PDF (which also needs TeX).

After removing Reference source pages, clear the old output first::

    make -C docs clean
    make -C docs html
