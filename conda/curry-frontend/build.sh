#!/bin/bash
# Installs the front end binary of the PAKCS distribution.
set -euo pipefail
install -D -m 755 bin/pakcs-frontend "$PREFIX/bin/pakcs-frontend"
ln -s pakcs-frontend "$PREFIX/bin/curry-frontend"
