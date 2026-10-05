-- Programs for unit_cxx_heap.py.
module CxxHeap where

-- A constructor of 70 fields.  Its node takes 568 bytes, more than the
-- largest size class of the block heap, so it lives in a span of its own.
data Big = Big Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int
    Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int
    Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int
    Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int Int

big :: Int -> Big
big n = Big n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n
    n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n n

sumBig :: Big -> Int
sumBig (Big a1 a2 a3 a4 a5 a6 a7 a8 a9 a10 a11 a12 a13 a14 a15 a16 a17 a18 a19
    a20 a21 a22 a23 a24 a25 a26 a27 a28 a29 a30 a31 a32 a33 a34 a35 a36 a37
    a38 a39 a40 a41 a42 a43 a44 a45 a46 a47 a48 a49 a50 a51 a52 a53 a54 a55
    a56 a57 a58 a59 a60 a61 a62 a63 a64 a65 a66 a67 a68 a69 a70)
  = a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 + a14 +
    a15 + a16 + a17 + a18 + a19 + a20 + a21 + a22 + a23 + a24 + a25 + a26 +
    a27 + a28 + a29 + a30 + a31 + a32 + a33 + a34 + a35 + a36 + a37 + a38 +
    a39 + a40 + a41 + a42 + a43 + a44 + a45 + a46 + a47 + a48 + a49 + a50 +
    a51 + a52 + a53 + a54 + a55 + a56 + a57 + a58 + a59 + a60 + a61 + a62 +
    a63 + a64 + a65 + a66 + a67 + a68 + a69 + a70

-- The sums of n large nodes, each dead once summed: [70, 140 ..].
sums :: Int -> [Int]
sums n = map (sumBig . big) [1..n]

-- n large nodes kept in a value.
keep :: Int -> [Big]
keep n = map big [1..n]

-- Builds n large nodes, keeps them alive while a list of m cells is walked,
-- so the spans stay through collections, and sums them afterwards.
keepWhile :: Int -> Int -> Int
keepWhile n m = let bs = keep n
                in foldr seq () bs `seq` (walk m + foldr (+) 0 (map sumBig bs))

walk :: Int -> Int
walk n = lastOf [1..n]

lastOf :: [Int] -> Int
lastOf (x:xs) = if null xs then x else lastOf xs
