# PAKCS front-end references

`2.0.0/` and `3.1.0/` contain the FlatCurry (`.fcy`), interfaces (`.fint`)
and translated ICurry (`.icy`) of all 30 current `curry/lib` modules. They
were generated offline from clean source copies by the installed front ends
of PAKCS 3.4.1 and 3.10.0 respectively, then translated with Sprite's
rewriter and translator. Every Curry invocation used a timeout. No staged
library products or compiler cache were used as input.

Each manifest records the binary digest, upstream version, PAKCS version,
flags and source/product digests. The matching Sprite installation supplied
the CPP macro (304 or 310) and frontend directory (pakcs-3.4.1 or
pakcs-3.10.0) through sysconfig. `parity.py` selects the directory by the
binary's numeric version and rejects mismatched configuration or stale
sources/products. Regeneration is explicit:

```sh
SPRITE_HOME=install timeout 600 install/bin/python frontend/parity.py \
  --binary install/tools/curry-frontend --output frontend-work/reference \
  --write-reference frontend/reference
```

Only the trusted PAKCS binary should generate the baseline. Source-built
wheels on both architectures compare with these references in CI, including
the unmodified FlatCurry and interfaces. The `.icy` files reflect Sprite's
rewrite passes and translation; `.fcy` and `.fint` remain front-end output. This checks each build against PAKCS of the same version,
not parity between different front-end versions.

The unversioned 23 `.fint` files and their manifest are retained unchanged
as historical 2.0.0 provenance. They described the earlier library and do
not cover the base 3.4.0 refresh; normal runs use the versioned directory.
The old comparison with eight committed ICurry files is replaced by
complete versioned products, since those files alone do not cover the
current library. Notices remain in `curry/lib/LICENSE` and
`curry/lib/NOTICE`.
