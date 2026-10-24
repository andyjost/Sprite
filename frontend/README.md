# curry-frontend

This directory packages the Curry front end 2.0.0 shipped with PAKCS 3.4.1.
It does not change Sprite's build. The workflow "Curry front end from
source" builds the wheels; the workflow "Release the front end" publishes
the wheels of a green run, on dispatch, through Trusted Publishing.

## Packaging epoch

`2.0.0.post1` is Sprite's first packaging revision of upstream 2.0.0.
Increase the `post` number when the packaging, patches, or build recipe
changes without changing the front end's program version. This is a PEP
440 post release, not a PEP 440 `!` epoch. `--numeric-version` must always
print `2.0.0`. The conda package retains its name `curry-frontend` and
upstream version `2.0.0`, and uses build number 1 for this revision.

`2.0.0.post2` (conda build 2) adds the two source compatibility patches
established by CI run 1. The upstream version remains `2.0.0`.

`2.0.0.post3` (conda build 3) adds the `Curry.Syntax.Utils` imports found
in run 2, verifies static linkage, and builds/bundles in manylinux 2.28
containers on the Ubuntu 24.04 hosts. Dynamic bundles use the container's
GMP and retain its RPM license notices. The program version stays `2.0.0`.

`2.0.0.post4` (conda build 4) adds the two compatibility patches found in
run 3. Both targets now request dynamic system linkage in manylinux 2.28,
vendoring its GMP with `$ORIGIN`. The Haskell tools share a writable home
under the workspace. The program version remains `2.0.0`.

`2.0.0.post5` gives the wheel the description of its PyPI page
(`README.pypi.md`, the `readme` of `pyproject.toml`), which the release
workflow's strict `twine check` requires. The conda package is unchanged
(build 4). The program version remains `2.0.0`.

## Scripts

* `fetch.py --output DIR` checks the PAKCS download page, tries its source
  archive links for 3.4.1 and the expected `pakcs-3.4.1-src.tar.gz`, then
  falls back to the Kiel GitLab project's exact 2.0.0 tag. It retains the
  page, archive, checksums, and tag/commit metadata. A reviewed URL and
  checksum can be passed with `--url URL --sha256 HASH`. The workflow now
  pins the archive URL and SHA-256 established on both targets in run 1.
* `bash frontend/build.sh SOURCE OUTPUT` prints the toolchain and source
  manifests, applies named patches, and links dynamically against the
  container's system libraries. x86-64 uses the source's `lts-16.9`
  snapshot with GHC 8.8.3;
  aarch64 starts at GHC 9.6 with Cabal's dependency bounds relaxed. Solver
  and compiler errors, linker commands, and ELF linkage are retained in
  both the job log and artifact logs. CI run 3 established that AlmaLinux
  8 lacks a GMP archive; the workflow accepts the dynamic route instead
  of fetching another source dependency to build GMP.
* `collect-logs.py --source SOURCE --output DIR` retains ghcup, Cabal,
  and Stack logs, including project build logs, in the uploaded artifacts
  even if toolchain setup or compilation fails.
* `package.py --binary BINARY --licenses LICENSES --output DIR` copies the
  binary, vendors dynamically required GMP beside it with `$ORIGIN`,
  records linkage and the glibc symbol floor of **both** files, and builds
  an offline wheel. It needs `setuptools>=68`, `wheel`, `pip`, `readelf`,
  `ldd`, and, for dynamic GMP, `patchelf` and the distributor's GMP notices
  at `/usr/share/doc/libgmp10/copyright` (Debian) or under
  `/usr/share/licenses/gmp*` (RPM). It never downloads a dependency.
  The source build's license directory overrides the checked-in copies.
* `tag-wheel.py WHEEL --info INFO --output DIR` first tries auditwheel for
  manylinux 2.28. If auditwheel refuses the native package data, the script
  checks the recorded glibc requirement and uses `wheel tags`. It fails
  rather than applying a 2.28 tag to an executable or vendored GMP requiring
  newer glibc. The original Linux wheel and metadata remain artifacts.
* `parity.py --binary BINARY --output DIR [--baseline PRODUCTS]` runs under
  the staged Sprite Python (`install/bin/python`). It compiles a clean
  copy of all 23 library modules, with Sprite's flags and translator. It
  compares all eight committed `.icy` files and, with a baseline, all
  `.fint` files. Every module's output, logs, expected side, and unified
  diff survive a failure. No frontend/ICurry/product cache is consulted.

The package contains `curry_frontend`, the executable as package data, and
the `curry-frontend` console script. The script replaces its process with
the executable, preserving the argument vector and exit status. The wheel
is `py3-none-PLATFORM`, installed in platlib; it has no Python extension.
The raw upstream PAKCS and front-end notices are included both with the
payload and in wheel metadata. Dynamic bundles also include the GMP notice.

Run 2 again passed x86-64 parity and the wheel smoke test. Its executable
required GLIBC 2.34 and its vendored Ubuntu GMP required GLIBC 2.38, so the
manylinux 2.28 gate correctly failed. The static-link transcript was
incomplete; it does not establish the cause of that attempt's failure.
On aarch64 both existing patches applied, and the next errors were missing
`liftM2` and `liftM3` imports, addressed by patch 0003.

Run 3 uses `quay.io/pypa/manylinux_2_28_x86_64` and
`quay.io/pypa/manylinux_2_28_aarch64` as job containers, including packaging
and parity. The workflow installs GHC/Cabal with verbose ghcup commands in
an isolated writable prefix, and Stack on x86-64. It selects the image's
CPython 3.14. The image tag, OS, library/tool versions, bootstrap checksum,
linker commands, actual ELF linkage and glibc requirements remain visible.
A dynamic wheel requiring newer glibc still fails the tagging gate.

Run 3 failed before linking on both targets. Stack 2.15.7 rejected
`--no-shared`, then refused the dynamic retry's root under the container's
default home because its parent belonged to another user. ARM reported
the missing `Alternative (Either String)` instance and the `when` import;
patches 0004 and 0005 address both. Run 4 puts `HOME`, `STACK_ROOT`,
`CABAL_DIR`, and `GHCUP_INSTALL_BASE_PREFIX` under `frontend-work/home`
at job scope, including log collection after failure. It drops the static
attempt and the unavailable `gmp-static` RPM probe on both targets.

## Local packaging

With the packaging dependencies already installed:

```sh
python frontend/package.py --binary install/tools/curry-frontend --output /tmp/frontend-wheel
python -m venv /tmp/frontend-smoke
/tmp/frontend-smoke/bin/python -m pip install --no-index --no-deps /tmp/frontend-wheel/*.whl
/tmp/frontend-smoke/bin/curry-frontend --numeric-version
```

## Conda

Prepare the **same source-built executable** as a bundle, then point the
recipe at that directory. Use an absolute artifact path so conda-build's
working directory cannot change its meaning:

```sh
python frontend/package.py --binary frontend-work/build/curry-frontend \
  --licenses frontend-work/fetch/licenses --bundle-only --output /tmp/frontend-artifact
export SPRITE_FRONTEND_ARTIFACT=/tmp/frontend-artifact
conda render conda/curry-frontend
# Publication/build is a separate reviewer action:
# conda build conda/curry-frontend
```

The artifact includes `bin/`, `licenses/`, and `build-info.json`. The recipe
checks the architecture and numeric version. It installs `pakcs-frontend`
and the `curry-frontend` alias. For dynamic artifacts conda's GMP supplies
the library; the installed executable gets `$ORIGIN/../lib`. The metadata
records the artifact's glibc floor as a run dependency. Build number 4
supports `linux-64` and `linux-aarch64` with a native artifact for each.

For compatibility with the existing conda build driver, omitting
`SPRITE_FRONTEND_ARTIFACT` retains the old checksum-pinned PAKCS x86-64
binary repack. That mode cannot build an aarch64 package. The new workflow
uses the source-built artifact mode explicitly. Existing measurements in
`conda/README.md` describe the earlier binary repack, not the source build.
