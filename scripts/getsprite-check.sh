#!/bin/sh
# Reviewer smoke tests. Run each image separately, with released or local wheels:
# GETSPRITE_FIND_LINKS=dist scripts/getsprite-check.sh ubuntu:22.04
# GETSPRITE_FIND_LINKS=dist scripts/getsprite-check.sh ubuntu:24.04
set -eu

case "${1:-}" in
  ubuntu:22.04|ubuntu:24.04) image=$1 ;;
  *) printf 'Usage: %s ubuntu:22.04|ubuntu:24.04\nGETSPRITE_FIND_LINKS: wheel directory or URL (optional).\n' "$0" >&2; exit 2 ;;
esac
test "$#" = 1 || exit 2
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
links=${GETSPRITE_FIND_LINKS:-}
set -- docker run --rm -i --mount "type=bind,src=$root,dst=/src,readonly"
if [ -n "$links" ] && [ -d "$links" ]; then
  wheels=$(CDPATH= cd -- "$links" && pwd)
  set -- "$@" --mount "type=bind,src=$wheels,dst=/wheels,readonly"
  links=/wheels
fi
set -- "$@" -e "GETSPRITE_FIND_LINKS=$links" "$image" sh -s
"$@" <<'CONTAINER'
set -eu
export LC_ALL=C.UTF-8
. /etc/os-release
apt-get update
set -- curl ca-certificates
if [ "$VERSION_ID" = 24.04 ]; then
  set -- "$@" g++
fi
apt-get install -y --no-install-recommends "$@"
useradd -m -s /bin/sh sprite
# Only container preparation uses root. The installer and checks run as a user.
su -s /bin/sh sprite <<'USER'
set -eu
cd "$HOME"
sh /src/getsprite --dry-run
sh /src/getsprite-i --dry-run
sh /src/getsprite
export PATH="$HOME/.local/bin:$PATH"
# The second run must upgrade the same tool, without conflicts.
sh /src/getsprite
sprite-exec --help
sprite-make --help
test "$(curry-frontend --numeric-version)" = 2.0.0
tool_python="$(uv tool dir)/currylang/bin/python"
"$tool_python" - <<'PY'
import importlib.metadata as metadata
import sys
assert (3, 11, 4) <= sys.version_info < (3, 16)
assert sys.prefix != sys.base_prefix
requirements = metadata.requires('currylang')
assert any(req.startswith('curry-frontend') for req in requirements), requirements
assert not any(req.startswith('uv') for req in requirements), requirements
assert metadata.version('curry-frontend')
print('Isolated Python:', sys.version)
PY
printf 'module Smoke where\nmain :: Int\nmain = 42\n' > Smoke.curry
test "$(sprite-exec -g main Smoke.curry)" = 42
test "$("$tool_python" -m curry -g main Smoke.curry)" = 42
. /etc/os-release
if [ "$VERSION_ID" = 24.04 ]; then
  command -v g++
  sprite-make --so Smoke.curry
  test -n "$(find .curry -name 'Smoke.so' -print -quit)"
  test "$(sprite-exec -g main Smoke.curry)" = 42
else
  ! command -v g++
fi
printf 'getsprite checks passed\n'
USER
CONTAINER
