-- Example from "A New Functional-Logic Compiler for Curry" (p. 12, journal
-- version, submitted 12/2018)
main = (fst y, snd y) ? (snd y, x) where { y = (not x, x); x free }
