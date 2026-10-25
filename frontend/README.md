# curry-frontend

The package supports front end 2.0.0 with PAKCS 3.4.1 (the default) and
front end 3.1.0 with PAKCS 3.10.0 (advisory CI until two reviewed green
runs). Sprite's default dependency stays on 2.0.0 until upgrade stage G.
Nothing is published by a push: the owner dispatches the protected release
workflow after reviewing the source-build artifacts.

## Source and compiler pins

| Program | Package | Source | Stack resolver | GHC |
| --- | --- | --- | --- | --- |
| 2.0.0 | 2.0.0.post6 | PAKCS 3.4.1 source archive | lts-16.9 on Linux x86-64 | 8.8.3; Cabal with 9.6.7 on aarch64/macOS |
| 3.1.0 | 3.1.0.post1 | cau-placc/curry-frontend tag v3.1.0 on GitHub | lts-23.19 on both Linux architectures | 9.8.4 expected; Stack must confirm against the locked snapshot |

`fetch.py` pins the URLs and SHA-256 values for both sources. The 3.1.0
archive pin is `13d68be89369a3fdfd1ef2d6e8d4657ab286876f9063bb0b27332de54c6be75c`.
There is no Hackage 3.x source release. The source's `stack.yaml.lock`
pins snapshot SHA-256
`296a7960c37efa382432ab497161a092684191815eb92a608c5d6ea5f894ace3`
(size 683835) and set-extra 1.4.2. The snapshot bytes were unavailable
offline: the compiler patch version and availability of suitable ghcup
bindists on both architectures need confirmation in CI. The workflow
selects GHC 9.8.4; `--system-ghc --no-install-ghc` refuses a mismatch.

The 3.1.0 Cabal bounds are retained: base ^>=4.19, transformers ^>=0.6,
mtl ^>=2.3, bytestring ^>=0.12 and time ^>=1.12. Both targets use Stack;
there is no `--allow-newer` on this route. All five old patches are dropped
for 3.1.0 following the source audit in [patches/README.md](patches/README.md).
The 2.0.0 recipe still applies all five patches, on both architectures.

Both Linux builds use manylinux 2.28 images and dynamic system linkage,
with GMP vendored beside the executable using `$ORIGIN`. The distribution
target is glibc 2.28, not an inference from the GHC version. The downloaded GHC
bindist's requirements and the resulting executable must be checked on
each architecture; an exact bindist floor was not established offline. A binary
or vendored GMP requiring newer symbols fails `tag-wheel.py`. The local
PAKCS binary's measured floor is not a source-build portability result.
Mach-O bundling retains the maximum deployment target of executable and
vendored GMP, `@loader_path` relocation and ad hoc signing. No new macOS
source-build lane is added for 3.1.0.

`2.0.0.post6` adds the two macOS wheels (issue #162, step 3): the job
`macos` of the workflow builds the same source on `macos-15` (Apple
Silicon) and `macos-15-intel` with GHC 9.6.7 and Cabal from ghcup, vendors
the GMP of Homebrew beside the executable with `@loader_path`
(`package.py`), and tags the wheel with the floor of its files
(`tag-wheel.py`), the macOS of the Homebrew bottle, 15.0 on those runners.
Parity runs on both architectures. The release workflow expects four
wheels. The conda package is unchanged.

## Scripts

* `fetch.py --version VERSION --output DIR` downloads and verifies the
  selected pin before extraction. `--archive FILE` verifies staged bytes
  offline. Reviewed overrides require `--url URL --sha256 HASH` together.
  Source, archive, notices and provenance metadata are retained.
* `bash frontend/build.sh SOURCE OUTPUT [VERSION]` defaults to 2.0.0,
  checks the source resolver, prints manifests/toolchain/linkage, and
  verifies the numeric version. The 2.0.0 aarch64/macOS route uses Cabal
  with relaxed bounds; the other routes use the source's Stack resolver.
* `package.py --binary BINARY --licenses LICENSES --output DIR` detects
  either program version and builds its corresponding packaging version.
  `--bundle-only` writes bin/, licenses/ and build-info.json for conda.
  It requires existing setuptools, wheel, pip and binary inspection tools;
  it fetches no dependencies. ELF dependencies are restricted to the system
  allowlist and GMP; both files' glibc symbol requirements are recorded.
  GMP distributor notices and upstream notices are kept verbatim.
* `tag-wheel.py WHEEL --info INFO --output DIR` tries auditwheel, then
  validates the recorded ELF floor before a data-only manylinux fallback.
  On macOS it tags with the measured minimum OS and architecture.
* `parity.py --binary BINARY --output DIR` selects `reference/VERSION/`
  by the binary's numeric version and requires a matching Sprite
  installation. Flags and intermediate directory names come from that
  installation's sysconfig. Clean library copies are compiled without
  caches and compared with trusted PAKCS FlatCurry, interfaces and the
  translated ICurry. Source and product digests detect stale references.
  `--write-reference frontend/reference` generates a versioned baseline;
  use only a trusted PAKCS binary. Historical unversioned 2.0.0 references
  remain as provenance; versioned references cover the current library.
* `collect-logs.py` retains partial ghcup, Cabal and Stack logs after failure.

The native payload installs in platlib as `py3-none-PLATFORM`, with a Python
console script that replaces its process with the executable. Direct
`setup.py` builds default to 2.0.0.post6; `CURRY_FRONTEND_VERSION=3.1.0`
selects 3.1.0.post1. `package.py` sets it from the validated binary.
Packaging revisions increment `.postN`; the program's `--numeric-version`
stays 2.0.0 or 3.1.0 respectively.

## Validation and release

```sh
python frontend/package.py --binary frontend-work/build/curry-frontend \
  --licenses frontend-work/fetch/licenses --output frontend-work/wheels
python -m venv frontend-work/smoke
frontend-work/smoke/bin/python -m pip install --no-index --no-deps frontend-work/wheels/*.whl
timeout 30 frontend-work/smoke/bin/curry-frontend --numeric-version
```

`frontend.yml` builds both versions on x86-64 and aarch64, uploads separately
named artifacts, and leaves 3.1.0 advisory. Default artifacts start with
`frontend-2.0.0-`; current artifacts start with `curry-frontend-3.1.0-`,
so the existing Sprite wheel workflow continues selecting only 2.0.0. Review source pins, compiler
logs, ELF floors, versioned byte parity and wheel smoke results twice.
`release-frontend.yml` takes a source run id, version (default 2.0.0), and
index. It collects the tagged wheels of that version (four for 2.0.0, the
macOS wheels included; two for 3.1.0), checks metadata, installs the
manylinux x86-64 wheel and checks its numeric version before the
protected `pypi` environment permits Trusted Publishing. Publishing is
always the owner's dispatch.

For conda, make a bundle with `package.py --bundle-only`, set
`SPRITE_FRONTEND_ARTIFACT` to its absolute directory, and render
`conda/curry-frontend`. Set `SPRITE_FRONTEND_VERSION=3.1.0` for the current
pair in both recipes; omit it for 2.0.0/3.4.1. A missing artifact uses the
checksum-pinned PAKCS x86-64 binary repack. The artifact mode supports
linux-64 and linux-aarch64, verifies version and architecture, and uses
conda's GMP with `$ORIGIN/../lib`. Conda builds remain reviewer work.
