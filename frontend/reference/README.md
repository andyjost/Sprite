# FlatCurry interface references

These 23 `.fint` files were generated from the checkout's `curry/lib`
sources by the existing pinned PAKCS 3.4.1 x86-64 binary, whose
`--numeric-version` prints `2.0.0`. They contain no build paths. The
front-end executable digest, the flags, and the source and interface
digests are recorded in `manifest.json`.

Generation used `frontend/parity.py` without `--baseline`, under the
staged Sprite Python. Its translation of the same FlatCurry matched all
eight committed ICurry files byte for byte. The PAKCS binary distribution
is checksum-pinned in `conda/curry-frontend/meta.yaml`; that archive was
not fetched again during fixture generation in the networkless sandbox.

Both CI architectures compare against these files, never against their
own output. Review these references with the workflow; regenerate only
with the pinned front end after an intentional library change. The
library's notices are in `curry/lib/LICENSE` and `curry/lib/NOTICE`.
