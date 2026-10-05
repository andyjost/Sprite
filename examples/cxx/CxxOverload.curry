-- Overload resolution as search over the type algebra of CxxType.
--
-- The module has four parts:
--
--   * the standard conversion sequences of [conv] and [over.ics.scs]: the
--     function convert gives the rank of the sequence that converts an
--     argument type to a parameter type.  It has one rule per conversion.
--     The rules are alternatives, and a pair of types that no rule covers
--     has no sequence;
--   * the viable candidates of a call ([over.match.viable]): viable picks a
--     candidate and a sequence for each argument non-deterministically, and
--     a set function collects every viable candidate with its ranks;
--   * the comparison of sequences ([over.ics.rank]) and of candidates
--     ([over.match.best]), and the resolution of a call;
--   * printers for candidates, ranks, viable sets and resolutions.
--
-- The model is a simplification of overload resolution in C++.  A candidate
-- is a function with a fixed number of parameters.  A parameter is passed
-- by value, or it is a reference to const, which binds the converted
-- argument; a candidate with another reference parameter is never viable.
-- An argument type written as a reference is an lvalue or an xvalue of the
-- referenced type, and the lvalue transformations turn it into a prvalue,
-- unless the parameter is a reference to const of array or function type,
-- which binds the lvalue directly.
-- Left out: user-defined conversions, default arguments and ellipses,
-- templates, argument-dependent lookup, member functions and their object
-- parameter, pointer-to-member conversions, and the reference bindings of
-- [over.ics.ref] beyond the reference to const.

module CxxOverload where

import Control.SetFunctions
import Data.List (intercalate)
import CxxLimits
import CxxType

-- Candidates and calls --------------------------------------------------------

-- A candidate function: its name and its parameter types.
type Candidate = (String, [Type])

-- A class hierarchy: the pairs (derived, base) of the direct bases.
type Hierarchy = [(String, String)]

-- Whether the class d derives, directly or indirectly, from the class b.
derives :: Hierarchy -> String -> String -> Bool
derives h d b = any (\(x, y) -> x == d && (y == b || derives h y b)) h

-- The rank of a standard conversion sequence ([over.ics.scs], Table 19).
-- A smaller rank is a better rank.
data Rank = Exact | Promotion | Conversion
  deriving (Eq, Ord, Show)

-- The prvalue type of an argument.  The lvalue transformations
-- ([conv.lval], [conv.array], [conv.func]) drop a reference, turn an array
-- into a pointer to its first element and a function into a pointer to it,
-- and drop the top-level cv-qualifiers.
prvalue :: Type -> Type
prvalue a = decay a

-- The type an argument is converted to.  For a parameter by value it is the
-- parameter type after the adjustments of [dcl.fct]: an array or function
-- parameter becomes a pointer, and the top-level cv-qualifiers are dropped.
-- For a parameter T const& it is T: the reference binds the converted
-- argument, or a temporary that holds it ([dcl.init.ref]).  A reference to
-- a function type, which no cv-qualifier can qualify, binds a function
-- lvalue directly, and its target is the function type.  Another reference
-- parameter has no target.
target :: Type -> Type
target p
  | k == KLRef = constReferee (referee q)
  | k == KRRef = failed
  | otherwise  = adjustParam q
  where
    q = norm p
    k = kind q

-- The referenced type of a reference to const, without its qualifiers, or
-- of a reference to a function.
constReferee :: Type -> Type
constReferee u | is_const u && not (is_volatile u) = remove_cv u
constReferee u | is_function u                     = u

-- Conversions -----------------------------------------------------------------

-- The rank of the standard conversion sequence from the argument type a to
-- the parameter type p ([over.ics.scs]).  The sequence is a lvalue
-- transformation, then at most one promotion or conversion, then at most
-- one qualification conversion.  No value when there is no sequence.
convert :: Hierarchy -> Type -> Type -> Rank
convert h a p = standard h (source a p) (target p)

-- The type the conversion starts from.  A parameter by value takes the
-- prvalue of the argument.  So does a reference to const, which binds a
-- temporary that holds the converted argument, unless its referee is an
-- array or a function type: such a reference binds directly to an lvalue
-- of that type ([dcl.init.ref]), with no lvalue transformation, and the
-- argument type counts without its reference and its qualifiers.  So
-- int[3] binds to int const (&)[3] with the identity conversion, and
-- int[4] does not bind to it at all.
source :: Type -> Type -> Type
source a p
  | kind q == KLRef && (is_array r || is_function r) = remove_cvref a
  | otherwise                                        = prvalue a
  where
    q = norm p
    r = referee q

-- The second and third conversions of a sequence, from a prvalue type to a
-- target.  Each rule is one conversion of [conv].  The rules are
-- alternatives, and each applies to one case, so a pair of types has at
-- most one sequence.
standard :: Hierarchy -> Type -> Type -> Rank
-- The identity conversion.
standard _ a p | a == p = Exact
-- A qualification conversion ([conv.qual]): int* to int const*.
standard _ a p | a /= p && qualifies a p = Exact
-- The integral promotions and the floating-point promotion.
standard _ a p | promotes a p = Promotion
-- An integral, floating-point or floating-integral conversion
-- ([conv.integral], [conv.double], [conv.fpint]): between two arithmetic
-- types other than bool, when the pair is not a promotion.
standard _ a p
  | is_arithmetic a && is_arithmetic p && p /= Fund Bool && a /= p
    && not (promotes a p)
  = Conversion
-- A boolean conversion ([conv.bool]): an arithmetic type, a pointer or a
-- pointer to member to bool.  std::nullptr_t converts to bool in a
-- direct-initialization only, and the initialization of a parameter is
-- not one, so f(bool) is not viable for a std::nullptr_t argument.
standard _ a p
  | p == Fund Bool && a /= p
    && (is_arithmetic a || is_pointer a || is_member_pointer a)
  = Conversion
-- A pointer conversion to void* ([conv.ptr]/2): a pointer to an object type
-- to a pointer to void that is at least as qualified.  The pointer
-- conversion and the qualification conversion that may follow it are one
-- sequence of rank Conversion.
standard _ a p
  | pointerTo is_object a && pointerTo is_void p && cvLeq (pointee a) (pointee p)
  = Conversion
-- A derived-to-base conversion of a pointer ([conv.ptr]/3): Derived* to
-- Base*, or to a Base* that is at least as qualified.
standard h a p
  | pointerTo is_class a && pointerTo is_class p
    && derives h (className (pointee a)) (className (pointee p))
    && cvLeq (pointee a) (pointee p)
  = Conversion
-- A null pointer conversion ([conv.ptr]/1): std::nullptr_t to any pointer
-- or pointer to member.
standard _ a p
  | is_null_pointer a && (is_pointer p || is_member_pointer p)
  = Conversion
-- A derived-to-base conversion of a class by value ([over.best.ics]/6).
standard h a p
  | is_class a && is_class p && derives h (className a) (className p)
  = Conversion

-- An integral promotion ([conv.prom]) or the floating-point promotion
-- ([conv.fpprom]): bool, char, signed char, unsigned char, short and
-- unsigned short promote to int; float promotes to double.
promotes :: Type -> Type -> Bool
promotes a p = is_integral a && a /= p && p == Fund (promoted (fundOf a))
               || a == Fund Float && p == Fund Double

-- Whether a converts to b by a qualification conversion ([conv.qual]): the
-- two are pointer chains of the same length over the same type, every
-- level of b is at least as qualified as the level of a, and where a level
-- of b is more qualified, every level above it, except the first, is const
-- in b.  So int** converts to int const* const*, but not to int const**.
qualifies :: Type -> Type -> Bool
qualifies a b =
  endA == endB && length la == length lb && levelsOk True la lb
  where
    (la, endA) = chain a
    (lb, endB) = chain b

-- The cv-qualifiers of the levels of a pointer chain, from the outermost
-- pointee inwards, and the type at the end of the chain.
chain :: Type -> ([(Bool, Bool)], Type)
chain t
  | kind t == KPtr = let (c, v, b) = splitCv (pointee t)
                         (rest, end) = chain b
                     in ((c, v) : rest, end)
  | otherwise      = ([], t)

-- The rule of [conv.qual] on the levels of two chains.  allConst tells
-- whether every level above the current one is const in the second chain.
levelsOk :: Bool -> [(Bool, Bool)] -> [(Bool, Bool)] -> Bool
levelsOk _ [] [] = True
levelsOk _ [] (_ : _) = False
levelsOk _ (_ : _) [] = False
levelsOk allConst ((c1, v1) : xs) ((c2, v2) : ys) =
  (not c1 || c2) && (not v1 || v2) && (c1 == c2 && v1 == v2 || allConst)
  && levelsOk (allConst && c2) xs ys

-- Whether the cv-qualifiers of a are a subset of those of b.
cvLeq :: Type -> Type -> Bool
cvLeq a b = (not c1 || c2) && (not v1 || v2)
  where
    (c1, v1, _) = splitCv (norm a)
    (c2, v2, _) = splitCv (norm b)

pointee :: Type -> Type
pointee (Ptr u) = u

-- Whether t is a pointer whose pointee satisfies the test.
pointerTo :: (Type -> Bool) -> Type -> Bool
pointerTo test t = is_pointer t && test (pointee t)

className :: Type -> String
className t = case bare t of
  Class n _ -> n

-- The viable candidates ---------------------------------------------------------

-- A viable candidate and the rank of the conversion of each argument
-- ([over.match.viable]).  The function is non-deterministic: anyOf picks a
-- candidate, and convert picks the sequence of each argument.  A candidate
-- whose arity differs from the call, or with an argument that has no
-- sequence, gives no value.
viable :: Hierarchy -> [Candidate] -> [Type] -> (Candidate, [Rank])
viable h cands args
  | length params == length args = (cand, zipWith (convert h) args params)
  where
    cand = anyOf cands
    params = snd cand

-- Every viable candidate with its ranks, in the order of the candidates.
-- The set function collects the values of viable; a call with no viable
-- candidate gives the empty list.
viables :: Hierarchy -> [Candidate] -> [Type] -> [(Candidate, [Rank])]
viables h cands args = [v | c <- cands, v <- found, fst v == c]
  where
    found = sortValues (set3 viable h cands args)

-- The best viable function -------------------------------------------------------

-- Whether the sequence (r1, t1) is better than the sequence (r2, t2) for
-- the same argument, of prvalue type a, where t1 and t2 are the targets of
-- the two sequences ([over.ics.rank]/3.2).  A better rank wins.  Sequences
-- of the same rank are ordered by tieBreak.
better :: Hierarchy -> Type -> (Rank, Type) -> (Rank, Type) -> Bool
better h a (r1, t1) (r2, t2)
  | r1 /= r2  = r1 < r2
  | otherwise = tieBreak h a t1 t2

-- The order among two sequences of the same rank from the argument a to the
-- targets t1 and t2.  The rules order sequences from a pointer, a pointer
-- to member, std::nullptr_t or a class; two sequences of the same rank from
-- an arithmetic type are indistinguishable.
--
--   * A sequence that does not convert a pointer or a pointer to member to
--     bool is better than one that does ([over.ics.rank]/4.1).
--   * Derived* to Base* is better than Derived* to void* (/4.3).
--   * Derived* to Mid* is better than Derived* to Base* when Mid derives
--     from Base (/4.4), and the same for a class by value.
--   * A sequence is better than the same sequence followed by a
--     qualification conversion (/3.2.1), and among two qualification
--     conversions the one to the less qualified target is better (/3.2.5):
--     int* to int* beats int* to int const*, and Derived* to Base* beats
--     Derived* to Base const*.
tieBreak :: Hierarchy -> Type -> Type -> Type -> Bool
tieBreak h a t1 t2 =
     (is_pointer a || is_member_pointer a) && t1 /= Fund Bool && t2 == Fund Bool
  || is_pointer a && pointerTo is_class t1 && pointerTo is_void t2
  || is_pointer a && pointerTo is_class t1 && pointerTo is_class t2
     && derives h (className (pointee t1)) (className (pointee t2))
  || is_class a && is_class t1 && is_class t2
     && derives h (className t1) (className t2)
  || is_pointer a && t1 /= t2 && qualifies t1 t2

-- Whether the viable candidate v is a better function than w for the call
-- ([over.match.best]/2): v is not worse than w in any argument, and better
-- in at least one.
betterCandidate :: Hierarchy -> [Type] -> (Candidate, [Rank]) -> (Candidate, [Rank])
                -> Bool
betterCandidate h args v w =
  and (zipWith3 notWorse pvs (seqs v) (seqs w))
  && or (zipWith3 (better h) pvs (seqs v) (seqs w))
  where
    pvs = map prvalue args
    seqs (c, rs) = zip rs (map target (snd c))
    notWorse a s1 s2 = not (better h a s2 s1)

-- The outcome of overload resolution.
data Resolution = Unique String [Rank] | Ambiguous [String] | NoViable
  deriving (Eq, Show)

-- The best viable function of a call ([over.match.best]/3): Unique with the
-- candidate that is better than every other viable candidate and its
-- ranks; Ambiguous with the viable candidates that no other candidate
-- beats, when there is no best; NoViable when no candidate is viable.
resolve :: Hierarchy -> [Candidate] -> [Type] -> Resolution
resolve h cands args
  | null vs          = NoViable
  | length best == 1 = Unique (showCandidate (fst (head best)))
                              (snd (head best))
  | otherwise        = Ambiguous [showCandidate c | (c, _) <- maximal]
  where
    vs      = viables h cands args
    best    = [v | v <- vs, all (\w -> w == v || betterCandidate h args v w) vs]
    maximal = [v | v <- vs, not (any (\w -> betterCandidate h args w v) vs)]

-- Whether a call is ambiguous.
isAmbiguous :: Resolution -> Bool
isAmbiguous r = case r of
  Ambiguous _ -> True
  Unique _ _  -> False
  NoViable    -> False

-- Printers --------------------------------------------------------------------

-- A candidate as a declaration without its return type: "f(int, char*)".
showCandidate :: Candidate -> String
showCandidate (n, ps) = n ++ "(" ++ intercalate ", " (map showCxx ps) ++ ")"

showRank :: Rank -> String
showRank Exact      = "exact"
showRank Promotion  = "promotion"
showRank Conversion = "conversion"

-- The ranks of the arguments of a call: "[exact, conversion]".
showRanks :: [Rank] -> String
showRanks rs = "[" ++ intercalate ", " (map showRank rs) ++ "]"

-- The viable candidates with their ranks in one line, or "none".
showViables :: [(Candidate, [Rank])] -> String
showViables vs = case vs of
  []      -> "none"
  (_ : _) -> intercalate ", " [showViable v | v <- vs]

showViable :: (Candidate, [Rank]) -> String
showViable (c, rs) = showCandidate c ++ " " ++ showRanks rs

showResolution :: Resolution -> String
showResolution r = case r of
  Unique n rs  -> n ++ " " ++ showRanks rs
  Ambiguous ns -> "ambiguous: " ++ intercalate ", " ns
  NoViable     -> "no viable function"
