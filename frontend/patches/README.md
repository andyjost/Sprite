# Source patches

No source patches have been established locally: the source and GHC are
unavailable in the sandbox. The build applies `*.patch` files here in name
order with `patch --batch --forward -p1` from the front-end source root.
Each future patch must name the failing GHC version, the error, and why the
change preserves the 2.0.0 program. Dependency bound relaxation on aarch64
is a Cabal command-line option, not a source patch.
