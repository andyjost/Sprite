#!/bin/bash
set -eu
# The prerequisite diagnostic replaces the retired configure usage page.
python3 ../../../scripts/check-prereqs.py --help
