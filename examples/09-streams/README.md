# Streams

Streams.curry imports Sprite.Stream (yield).  threeOut yields 1, 2 and 3;
primesOut yields an infinite lazy sieve.  totalsOut threads a running total
through an I/O action, yields 1, 3 and 6, and returns 6.  State and output
stay in Curry; Python pulls the next value when it needs it.

curry.stream returns a lazy Stream.  Its result is None until exhaustion;
threeOut then leaves (), while totalsOut leaves 6.  go.py consumes the
finite stream with list, takes ten primes with itertools.islice, and
closes the paused stream in finally.  An open stream owns its paused run.
This channel requires the C++ runtime, so the test leaves out the reference
backend.  Yielded values and the action must be deterministic; a choice
raises NondetError at the pull that reaches it.

Run "make stage" at the repository root, then "./run" here.  expected.out
records the Python observations followed by the same threeOut action
under "sprite-exec Streams.curry -g threeOut": one yielded value per line,
with no result line for IO ().  The sieve is a teaching algorithm; only a
finite prefix crosses the boundary.  See the guide's io-streams section
and the REPL page for interactive I/O.
