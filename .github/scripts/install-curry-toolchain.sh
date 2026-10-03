#!/bin/bash
# Installs the Curry toolchain for CI: PAKCS (binary distribution), whose
# front end Sprite needs and which the functional tests use as the oracle,
# and the icurry package.  icurry is optional for Sprite; CI configures it in
# some jobs so that the tests compare both routes from Curry to ICurry.
# Everything lands under $HOME so that a CI cache can restore it.  Requires
# swipl, curl, and make.
set -euo pipefail
: "${PAKCS_VERSION:=3.4.1}"
: "${ICURRY_VERSION:=3.1.0}"
export LC_ALL=C.UTF-8
PAKCS_HOME="$HOME/pakcs-$PAKCS_VERSION"

# PAKCS.
cd "$HOME"
curl -fsSL -o pakcs.tar.gz \
  "https://www.curry-lang.org/pakcs/download/pakcs-$PAKCS_VERSION-amd64-Linux.tar.gz"
tar xzf pakcs.tar.gz
rm pakcs.tar.gz
if [ ! -d "$PAKCS_HOME" ]; then
  echo "the PAKCS archive did not unpack to $PAKCS_HOME" >&2
  ls -d "$HOME"/pakcs* >&2 || true
  exit 1
fi
cd "$PAKCS_HOME"
# The distribution sets a stack limit for SWI-Prolog 8 only.  Give 9 the same.
sed -i 's/^\([[:space:]]*\)8 )/\18 | 9 )/' scripts/pakcs-makesavedstate.sh
make SWIPROLOG="$(command -v swipl)"
export PATH="$PAKCS_HOME/bin:$PATH"

# CPM and icurry.  The Kiel mirrors do not answer; use curry-lang.org.
cat > "$HOME/.cpmrc" <<CPMRC
PACKAGEINDEXURL=https://cpm.curry-lang.org/PACKAGES/INDEX.tar.gz
PACKAGETARFILESURL=https://cpm.curry-lang.org/PACKAGES
CPMRC
cypm update
mkdir -p "$HOME/cpm-src"
cd "$HOME/cpm-src"
cypm checkout icurry "$ICURRY_VERSION"
# cypm names the checkout directory after the package; older versions append
# the version.
for dir in icurry "icurry-$ICURRY_VERSION"; do
  if [ -d "$dir" ]; then break; fi
done
cd "$dir"
# cypm install resolves the dependencies and builds the executable.  It has
# been seen to exit 1 after computing the load path; build by hand then.
cypm install || true
if [ ! -x "$HOME/.cpm/bin/icurry" ]; then
  cypm exec pakcs --nocypm :set v1 :load ICurry.Main :save :quit
  mkdir -p "$HOME/.cpm/bin"
  mv ICurry.Main "$HOME/.cpm/bin/icurry"
fi

# Smoke test: compile one module to ICurry.
cd "$(mktemp -d)"
printf 'main :: Int\nmain = 42\n' > Smoke.curry
"$HOME/.cpm/bin/icurry" Smoke
test -s ".curry/pakcs-$PAKCS_VERSION/Smoke.icy"
echo "Curry toolchain ready: $PAKCS_HOME and $HOME/.cpm/bin/icurry"
