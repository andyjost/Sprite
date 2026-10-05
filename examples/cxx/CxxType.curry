-- An algebraic model of C++ types.
--
-- The module has six parts:
--
--   * the algebra: the data type Type over the fundamental types of
--     CxxLimits, and the normal form that keeps one term per C++ type;
--   * the traits of <type_traits> as functions on Type;
--   * a printer, showCxx, that writes a type in C++ syntax;
--   * template argument deduction for a call ([temp.deduct.call]) and from a
--     type ([temp.deduct.type]), by unification: a template parameter is a
--     Curry free variable;
--   * the partial ordering of partial specializations ([temp.class.order])
--     and the choice of the most specialized one;
--   * a bounded generator, anyType, that enumerates every well-formed type
--     of the algebra up to a depth, one type per value, for the inverse
--     questions of the examples and for the trait check.
--
-- The model is a simplification of the C++ type system.  It has no
-- enumerations, unions, wide character types, noexcept or ref-qualified
-- functions, no non-type template parameters, no derived-to-base conversion
-- in deduction, and no class layout.
--
-- Non-determinism and failure follow Curry: a trait that C++ leaves undefined
-- (common_type of two class types, sizeof of a function) has no value.  Every
-- top-level function has a type signature.

module CxxType where

import Control.SetFunctions
import Data.List (intercalate)
import CxxLimits

-- The algebra ----------------------------------------------------------------

-- A C++ type.  Class names a class or a class template applied to arguments:
-- Class "Foo" [] is the class Foo, Class "std::vector" [Fund Int] is
-- std::vector<int>.  Arr t n is the array type t[n]; n = 0 stands for an
-- array of unknown bound, t[].  Fun r ps is the function type r(ps).
-- MemPtr c t is a pointer to a member of class c of type t.
data Type = Fund Fund
          | Const Type
          | Volatile Type
          | Ptr Type
          | LRef Type
          | RRef Type
          | Arr Type Int
          | Fun Type [Type]
          | MemPtr Type Type
          | Class String [Type]
  deriving (Eq, Ord, Show)

-- The outermost constructor of a type, for tests that must not narrow.
data Kind = KFund | KConst | KVolatile | KPtr | KLRef | KRRef | KArr | KFun
          | KMemPtr | KClass
  deriving (Eq, Ord, Show)

kind :: Type -> Kind
kind (Fund _)     = KFund
kind (Const _)    = KConst
kind (Volatile _) = KVolatile
kind (Ptr _)      = KPtr
kind (LRef _)     = KLRef
kind (RRef _)     = KRRef
kind (Arr _ _)    = KArr
kind (Fun _ _)    = KFun
kind (MemPtr _ _) = KMemPtr
kind (Class _ _)  = KClass

-- The normal form.  One C++ type has one term:
--
--   * const is outside volatile, and neither repeats;
--   * a cv-qualifier on an array qualifies the element type
--     ([basic.type.qualifier]);
--   * a cv-qualifier on a reference or on a function type is dropped
--     ([dcl.ref], [dcl.fct]);
--   * a reference to a reference collapses ([dcl.ref]);
--   * the parameter types of a function type are adjusted: an array or a
--     function parameter becomes a pointer, and top-level cv-qualifiers are
--     dropped ([dcl.fct]).
--
-- The traits normalize their arguments.  Deduction normalizes the argument
-- type and leaves the parameter pattern as written, because a pattern holds
-- free variables and normalization would narrow them.
norm :: Type -> Type
norm t = case t of
  Fund f      -> Fund f
  Const u     -> qualify True False (norm u)
  Volatile u  -> qualify False True (norm u)
  Ptr u       -> Ptr (norm u)
  LRef u      -> lref (norm u)
  RRef u      -> rref (norm u)
  Arr e n     -> Arr (norm e) n
  Fun r ps    -> Fun (norm r) (map adjustParam ps)
  MemPtr c u  -> MemPtr (norm c) (norm u)
  Class n as  -> Class n (map norm as)

-- Adds the qualifiers (c = const, v = volatile) to a normalized type.
qualify :: Bool -> Bool -> Type -> Type
qualify c v t = case t of
    Const u    -> qualify True v u
    Volatile u -> qualify c True u
    Arr e n    -> Arr (qualify c v e) n
    LRef _     -> t
    RRef _     -> t
    Fun _ _    -> t
    Fund _     -> wrapped
    Ptr _      -> wrapped
    MemPtr _ _ -> wrapped
    Class _ _  -> wrapped
  where
    wrapped = constIf c (volatileIf v t)

constIf :: Bool -> Type -> Type
constIf c t = if c then Const t else t

volatileIf :: Bool -> Type -> Type
volatileIf v t = if v then Volatile t else t

-- Splits a normalized type into its qualifiers and the unqualified type.  The
-- qualifiers of an array are those of its elements.
splitCv :: Type -> (Bool, Bool, Type)
splitCv t = case t of
    Const u    -> let (_, v, b) = splitCv u in (True, v, b)
    Volatile u -> let (c, _, b) = splitCv u in (c, True, b)
    Arr e n    -> let (c, v, b) = splitCv e in (c, v, Arr b n)
    Fund _     -> plain
    Ptr _      -> plain
    LRef _     -> plain
    RRef _     -> plain
    Fun _ _    -> plain
    MemPtr _ _ -> plain
    Class _ _  -> plain
  where
    plain = (False, False, t)

-- Reference collapsing: & + & = &, & + && = &, && + & = &, && + && = &&.
-- The argument is normalized, so its outermost constructor tells whether
-- it is a reference.
lref :: Type -> Type
lref t = if headIsReference t then LRef (referee t) else LRef t

rref :: Type -> Type
rref t = if headIsReference t then t else RRef t

-- The type a reference refers to.
referee :: Type -> Type
referee (LRef u) = u
referee (RRef u) = u

-- The element type of an array.
element :: Type -> Type
element (Arr e _) = e

-- The fundamental type of a type whose unqualified type is fundamental.
fundOf :: Type -> Fund
fundOf t = theFund (bare t)

theFund :: Type -> Fund
theFund (Fund f) = f

-- A parameter type of a function type, adjusted as in [dcl.fct].
adjustParam :: Type -> Type
adjustParam p = if k == KArr then Ptr (element q)
                else if k == KFun then Ptr q
                else remove_cv q
  where
    q = norm p
    k = kind q

-- The unqualified type, normalized.
bare :: Type -> Type
bare t = let (_, _, b) = splitCv (norm t) in b

isFund :: Type -> Bool
isFund t = kind (bare t) == KFund

-- The traits ------------------------------------------------------------------
--
-- Each trait takes the role of the alias or the constant of <type_traits> of
-- the same name: remove_const t is std::remove_const_t<t>, is_void t is
-- std::is_void_v<t>.

remove_const :: Type -> Type
remove_const t = let (_, v, b) = splitCv (norm t) in qualify False v b

remove_volatile :: Type -> Type
remove_volatile t = let (c, _, b) = splitCv (norm t) in qualify c False b

remove_cv :: Type -> Type
remove_cv t = bare t

remove_reference :: Type -> Type
remove_reference t = if is_reference n then referee n else n
  where n = norm t

remove_cvref :: Type -> Type
remove_cvref t = remove_cv (remove_reference t)

add_const :: Type -> Type
add_const t = qualify True False (norm t)

add_volatile :: Type -> Type
add_volatile t = qualify False True (norm t)

add_cv :: Type -> Type
add_cv t = qualify True True (norm t)

-- add_pointer: a pointer to the referenced type of a reference, otherwise a
-- pointer to the type.
add_pointer :: Type -> Type
add_pointer t = Ptr (remove_reference t)

-- add_lvalue_reference and add_rvalue_reference collapse references.  void
-- stays void.
add_lvalue_reference :: Type -> Type
add_lvalue_reference t = if is_void t then norm t else lref (norm t)

add_rvalue_reference :: Type -> Type
add_rvalue_reference t = if is_void t then norm t else rref (norm t)

-- decay: the type of a by-value parameter.  An array becomes a pointer to its
-- element type, a function a pointer to the function, a reference is removed
-- and so are the top-level cv-qualifiers.
decay :: Type -> Type
decay t = if k == KArr then Ptr (element u)
          else if k == KFun then Ptr u
          else remove_cv u
  where
    u = remove_reference t
    k = kind u

-- Primary type categories.
is_void :: Type -> Bool
is_void t = bare t == Fund Void

is_null_pointer :: Type -> Bool
is_null_pointer t = bare t == Fund NullptrT

is_integral :: Type -> Bool
is_integral t = isFund t && isIntegral (fundOf t)

is_floating_point :: Type -> Bool
is_floating_point t = isFund t && isFloating (fundOf t)

is_array :: Type -> Bool
is_array t = kind (bare t) == KArr

is_pointer :: Type -> Bool
is_pointer t = kind (bare t) == KPtr

is_lvalue_reference :: Type -> Bool
is_lvalue_reference t = kind (norm t) == KLRef

is_rvalue_reference :: Type -> Bool
is_rvalue_reference t = kind (norm t) == KRRef

is_member_pointer :: Type -> Bool
is_member_pointer t = kind (bare t) == KMemPtr

is_class :: Type -> Bool
is_class t = kind (bare t) == KClass

is_function :: Type -> Bool
is_function t = kind (norm t) == KFun

-- Composite type categories.
is_reference :: Type -> Bool
is_reference t = is_lvalue_reference t || is_rvalue_reference t

is_arithmetic :: Type -> Bool
is_arithmetic t = is_integral t || is_floating_point t

is_fundamental :: Type -> Bool
is_fundamental t = is_arithmetic t || is_void t || is_null_pointer t

is_compound :: Type -> Bool
is_compound t = not (is_fundamental t)

is_object :: Type -> Bool
is_object t = not (is_function t || is_reference t || is_void t)

is_scalar :: Type -> Bool
is_scalar t = is_arithmetic t || is_pointer t || is_member_pointer t
              || is_null_pointer t

-- Type properties.
is_const :: Type -> Bool
is_const t = let (c, _, _) = splitCv (norm t) in c

is_volatile :: Type -> Bool
is_volatile t = let (_, v, _) = splitCv (norm t) in v

is_same :: Type -> Type -> Bool
is_same a b = norm a == norm b

is_signed :: Type -> Bool
is_signed t = is_arithmetic t && isSigned (fundOf t)

is_unsigned :: Type -> Bool
is_unsigned t = is_arithmetic t && not (isSigned (fundOf t))

-- make_signed and make_unsigned keep the cv-qualifiers.  They have no value
-- for bool and for the types that are not integral, as in C++.
make_signed :: Type -> Type
make_signed t | is_integral t && fundOf t /= Bool
              = requalify t (Fund (signedOf (fundOf t)))

make_unsigned :: Type -> Type
make_unsigned t | is_integral t && fundOf t /= Bool
                = requalify t (Fund (unsignedOf (fundOf t)))

-- u with the cv-qualifiers of t.
requalify :: Type -> Type -> Type
requalify t u = let (c, v, _) = splitCv (norm t) in qualify c v u

-- The promotions ([conv.prom], [conv.fpprom]).  A promotion yields a
-- prvalue, so the result carries no cv-qualifiers.
integral_promotion :: Type -> Type
integral_promotion t = if is_integral t then Fund (promoted (fundOf t)) else bare t

floating_promotion :: Type -> Type
floating_promotion t = if bare t == Fund Float then Fund Double else bare t

-- common_type of two arithmetic types ([meta.trans.other]): the type of
-- the conditional operator over the two, after both are decayed.  Two
-- operands of one type keep that type, so common_type<T, T> is decay_t<T>,
-- and common_type<short, short const&> is short.  Two different types go
-- through the usual arithmetic conversions ([expr.arith.conv]), so
-- common_type<char, short> is int.  Other pairs have no value; the model
-- has no conditional operator over class types.
common_type :: Type -> Type -> Type
common_type a b
  | is_arithmetic da && is_arithmetic db
  = if da == db then da else Fund (usualArithmetic (fundOf da) (fundOf db))
  where
    da = decay a
    db = decay b

usualArithmetic :: Fund -> Fund -> Fund
usualArithmetic x y
  | isFloating x || isFloating y = higherRank x y
  | otherwise                    = usualIntegral (promoted x) (promoted y)

-- Two promoted integral types.
usualIntegral :: Fund -> Fund -> Fund
usualIntegral x y
  | x == y                   = x
  | isSigned x == isSigned y = higherRank x y
  | isSigned x               = mixedSign x y
  | otherwise                = mixedSign y x

-- s is signed and u is unsigned.
mixedSign :: Fund -> Fund -> Fund
mixedSign s u
  | rank u >= rank s     = u
  | digits s >= digits u = s
  | otherwise            = unsignedOf s

higherRank :: Fund -> Fund -> Fund
higherRank x y = if rank x >= rank y then x else y

-- sizeof and alignof, in bytes, under the data model of CxxLimits.  A
-- reference counts as the address it holds, as in a member layout; the C++
-- operator sizeof applied to a reference type gives the size of the
-- referenced type instead.  A pointer to a member function is two words in
-- the Itanium ABI, a pointer to a data member one.  A function type has no
-- size; neither has void, nor an array of unknown bound, which is an
-- incomplete type.  A class has no layout in this model.
sizeof_ :: Type -> Int
sizeof_ t = case norm t of
  Fund f      -> sizeofF f
  Const u     -> sizeof_ u
  Volatile u  -> sizeof_ u
  Ptr _       -> 8
  LRef _      -> 8
  RRef _      -> 8
  Arr e n     -> if n == 0 then failed else n * sizeof_ e
  Fun _ _     -> failed
  MemPtr _ u  -> if is_function u then 16 else 8
  Class _ _   -> failed

alignof_ :: Type -> Int
alignof_ t = case norm t of
  Fund f      -> alignofF f
  Const u     -> alignof_ u
  Volatile u  -> alignof_ u
  Ptr _       -> 8
  LRef _      -> 8
  RRef _      -> 8
  Arr e _     -> alignof_ e
  Fun _ _     -> failed
  MemPtr _ _  -> 8
  Class _ _   -> failed

-- The printer ------------------------------------------------------------------

-- A type in C++ syntax, with the cv-qualifiers after the type they qualify:
-- "int const*", "char const* const", "int (&)[3]", "void (*)(int, double)",
-- "int Foo::*", "Foo* Foo::*", "std::vector<int*>&&".  A function type is
-- written as "void (int)", an array of unknown bound as "int[]".
showCxx :: Type -> String
showCxx t = declare (norm t) ""

-- The declaration of the declarator d with the type t.  A declarator is
-- built inside out: the declarator of a pointer to t is "*" ++ d, of an
-- array of t is d ++ "[n]".  A pointer or reference declarator in front of
-- an array or function suffix needs parentheses: "int (*)[3]".  With a
-- name as the declarator, declare writes a declaration:
-- declare (Ptr (Const Char)) "payload" is "char const* payload", and
-- declare (Arr (Fund Int) 3) "a" is "int a[3]".  The type is not
-- normalized here; showCxx normalizes.
declare :: Type -> String -> String
declare t d = case t of
  Fund f     -> join (spelling f) d
  Class n as -> join (showClass n as) d
  Const u    -> declareCv "const" u d
  Volatile u -> declareCv "volatile" u d
  Ptr u      -> declare u (prefix u "*" d)
  LRef u     -> declare u (prefix u "&" d)
  RRef u     -> declare u (prefix u "&&" d)
  Arr e n    -> declare e (d ++ showBound n)
  Fun r ps   -> declare r (d ++ "(" ++ intercalate ", " (map showCxx ps) ++ ")")
  MemPtr c u -> declare u (prefix u (showCxx c ++ "::*") d)

-- The declaration of d with the type "t q", where q is a cv-qualifier.
declareCv :: String -> Type -> String -> String
declareCv q t d = case t of
  Const u    -> declareCv (q ++ " const") u d
  Volatile u -> declareCv (q ++ " volatile") u d
  Fund f     -> join (spelling f ++ " " ++ q) d
  Class n as -> join (showClass n as ++ " " ++ q) d
  Ptr u      -> declare u (prefix u ("* " ++ q) d)
  MemPtr c u -> declare u (prefix u (showCxx c ++ "::* " ++ q) d)
  Arr e n    -> declareCv q e (d ++ showBound n)
  LRef _     -> declare t d
  RRef _     -> declare t d
  Fun _ _    -> declare t d

-- The declarator op ++ d in front of a type u.  A space separates the
-- operator from a parenthesis, a name or a member-pointer declarator:
-- "int* (*)[3]", "char* payload", "Foo* Foo::*".
prefix :: Type -> String -> String -> String
prefix u op d = if k == KArr || k == KFun then "(" ++ op ++ d ++ ")"
                else op ++ gap d
  where
    k = kind u
    gap s = case s of
      []      -> s
      (c : _) -> if c == '(' || isAlphaNum c || c == '_' then " " ++ s else s

-- A type specifier followed by a declarator.  No space before "*", "&" and
-- "[": "int*", "int[3]", "int (*)[3]", "void (int)".
join :: String -> String -> String
join base d = case d of
  []      -> base
  (c : _) -> if c `elem` "*&[" then base ++ d else base ++ " " ++ d

showClass :: String -> [Type] -> String
showClass n as = case as of
  []      -> n
  (_ : _) -> n ++ "<" ++ intercalate ", " (map showCxx as) ++ ">"

showBound :: Int -> String
showBound n = if n == 0 then "[]" else "[" ++ showNat n ++ "]"

-- The decimal digits of a non-negative Int, by arithmetic.  The printer does
-- not use show: on the Python backend, show does not finish on an Int inside
-- a term that unification bound to a free variable, as in a deduced array
-- type, whereas arithmetic on it does.
showNat :: Int -> String
showNat n = if n < 10 then [digit n] else showNat (n `div` 10) ++ [digit (n `mod` 10)]

digit :: Int -> Char
digit d = chr (ord '0' + d)

-- Deduction for a call -------------------------------------------------------
--
-- A function parameter is passed by value, by lvalue reference or by rvalue
-- reference.  The type of a parameter is a pattern: it holds the template
-- parameters, which deduction binds.  An argument type encodes the value
-- category of the argument as well: LRef t is an lvalue of type t, RRef t
-- an xvalue, and a bare t a prvalue.
--
-- There are two entry points.  deduceCall, below the named templates, takes
-- the names of the template parameters, and a pattern refers to one as the
-- class of its name.  It is exact, and it is the one that knows every rule.
-- deduce takes a pattern over free variables: deduce (ByValue p) a holds
-- when p unifies with the decayed argument type a, and deduce (ByLRef p) a
-- strips a reference from the argument and unifies p with it.  A
-- cv-qualifier at the top of a by-reference pattern is taken off the
-- pattern, and off the argument when the argument has it
-- ([temp.deduct.call]/4), so the pattern T const deduces T = int from int
-- and from int const, and T = int[3] from int const[3], whose const is the
-- const of its elements.
--
-- A rule of deduce inspects the pattern one constructor deep and no deeper,
-- and each constructor has one rule, so the rules do not overlap.  A pattern
-- whose top is a free variable, as in T&, narrows into every rule: the
-- rule of the argument's own constructor binds T to the argument type, as
-- C++ does, and the rules for const and volatile bind T to a qualified
-- type, the bindings with an extra qualifier that [temp.deduct.call]/4
-- permits but a compiler never picks.  The forwarding reference and the
-- qualification conversion of a pointer pattern look below the reference
-- or the pointer, which would narrow a free variable there, so deduce
-- leaves them to deduceCall: deduce (ByRRef p) a is deduce (ByLRef p) a.
data Param = ByValue Type | ByLRef Type | ByRRef Type
  deriving (Eq, Show)

deduce :: Param -> Type -> Bool
deduce (ByValue p) a = p =:= decay a
deduce (ByLRef p) a  = deduceRef p (remove_reference a)
deduce (ByRRef p) a  = deduceRef p (remove_reference a)

deduceRef :: Type -> Type -> Bool
deduceRef (Const p) a      = p =:= remove_const a
deduceRef (Volatile p) a   = p =:= remove_volatile a
deduceRef (Fund f) a       = Fund f =:= a
deduceRef (Ptr p) a        = Ptr p =:= a
deduceRef (LRef p) a       = LRef p =:= a
deduceRef (RRef p) a       = RRef p =:= a
deduceRef (Arr e n) a      = Arr e n =:= a
deduceRef (Fun r ps) a     = Fun r ps =:= a
deduceRef (MemPtr c u) a   = MemPtr c u =:= a
deduceRef (Class n as) a   = Class n as =:= a

-- Deduction of every parameter of a call.  The parameters share their free
-- variables, so a template parameter that occurs twice must deduce to the
-- same type.
deduceAll :: [Param] -> [Type] -> Bool
deduceAll ps as = length ps == length as && and (zipWith deduce ps as)

-- Named templates -------------------------------------------------------------------
--
-- A pattern with free variables cannot be copied: Curry has no primitive
-- that lists the free variables of a term, and a function that inspects a
-- term narrows them.  The partial ordering needs copies, because it
-- instantiates one pattern and deduces another from the result, several
-- times over the same patterns.  So a template names its parameters, and
-- its pattern refers to them as classes of those names: Class "T" [] in
-- Template ["T"] (Ptr (Class "T" [])) is the parameter T.  instantiate
-- replaces the names; freshen replaces them by fresh free variables.
data Template = Template [String] Type
  deriving (Eq, Show)

-- A substitution: the type of each named template parameter.
type Subst = [(String, Type)]

-- Replaces the named parameters of a pattern.
instantiate :: Subst -> Type -> Type
instantiate env t = case t of
  Fund f     -> Fund f
  Const u    -> Const (instantiate env u)
  Volatile u -> Volatile (instantiate env u)
  Ptr u      -> Ptr (instantiate env u)
  LRef u     -> LRef (instantiate env u)
  RRef u     -> RRef (instantiate env u)
  Arr e n    -> Arr (instantiate env e) n
  Fun r ps   -> Fun (instantiate env r) (map (instantiate env) ps)
  MemPtr c u -> MemPtr (instantiate env c) (instantiate env u)
  Class n as -> case lookup n env of
                  Just v  -> v
                  Nothing -> Class n (map (instantiate env) as)

-- A fresh free variable for each name.
freshNames :: [String] -> Subst
freshNames names = map (\n -> let v free in (n, v)) names

-- The pattern of a template over fresh free variables, with the substitution
-- that names them.
freshen :: Template -> (Subst, Type)
freshen (Template names pat) = (env, instantiate env pat)
  where
    env = freshNames names

-- The synthesized class number i, a unique type that matches no pattern but
-- a template parameter.
synth :: Int -> Type
synth i = Class ("__synth" ++ showNat i) []

-- The pattern of a template with its parameters replaced by synthesized
-- classes, numbered from the seed.
synthesize :: Int -> Template -> Type
synthesize seed (Template names pat) =
  instantiate (zip names (map synth [seed ..])) pat

-- Deduction from a type ([temp.deduct.type]): the arguments of a template
-- whose pattern is the target.  The match is exact, so S<T*> does not match
-- int* const.  No value when the pattern does not match.
deduceArgs :: Template -> Type -> Subst
deduceArgs tmpl target | pat =:= norm target = env
  where
    (env, pat) = freshen tmpl

-- Deduction for a call of a function template with named parameters
-- ([temp.deduct.call]).  deduceCall replaces each name by a fresh free
-- variable, deduces every parameter from its argument, and returns the
-- bindings.  The parameters share the variables, so a template parameter
-- that occurs twice must deduce to the same type.  Each pattern is
-- inspected with the names in place, because the rules look into it: a
-- forwarding reference is an rvalue reference to a bare template parameter,
-- and the const of T const* comes off the argument.  A free variable in the
-- pattern would narrow under that inspection.
--
-- The rules.  A parameter by value takes the decayed argument type (array
-- to pointer, function to pointer, top-level cv-qualifiers dropped), and
-- its own pattern is adjusted the same way ([dcl.fct], [temp.deduct.call]/2
-- and /3).  A parameter by reference takes the argument type without its
-- reference ([temp.deduct.call]/3), and the referee pattern may be more
-- cv-qualified than it ([temp.deduct.call]/4).  A forwarding reference, P&&
-- with P a bare template parameter, takes the lvalue reference to the type
-- of an lvalue argument ([temp.deduct.call]/3), so T&& deduces T = int&
-- from an lvalue int and T = int from an rvalue int.  The pointee of a
-- pointer pattern, and the member type of a pointer-to-member pattern, may
-- be more cv-qualified than the pointee of the argument, which is the
-- qualification conversion of [temp.deduct.call]/4; below the first level
-- the extra qualifier needs const at every level above it ([conv.qual]), so
-- T const* deduces T = char from char*, T const* const* deduces T = int
-- from int**, and T const** deduces nothing from int**.  Everything else is
-- unification: the pattern and the argument agree constructor by
-- constructor ([temp.deduct.type]), also inside a class template argument,
-- where no conversion applies.
--
-- Left out: the non-deduced contexts, the derived-to-base conversion of a
-- class argument, the function pointer conversion (the model has no
-- noexcept), default template arguments and explicit template arguments.
deduceCall :: [String] -> [Param] -> [Type] -> Subst
deduceCall names params args
  | length params == length args
    && and (zipWith (deduceParam names env) params args)
  = env
  where
    env = freshNames names

-- One parameter against its argument type.
deduceParam :: [String] -> Subst -> Param -> Type -> Bool
deduceParam names env param a = case param of
    ByValue p -> deducePattern True env (adjustParam p) (decay a)
    ByLRef p  -> deduceReferee env (norm p) (remove_reference a)
    ByRRef p  -> deduceReferee env (norm p) (forwarded names p a)

-- The type a reference parameter deduces from: the argument type without
-- its reference, or the lvalue reference itself when the parameter is a
-- forwarding reference and the argument an lvalue.
forwarded :: [String] -> Type -> Type -> Type
forwarded names p a = if isParameter names p && is_lvalue_reference a
                      then norm a else remove_reference a

-- Whether a pattern is a bare template parameter.
isParameter :: [String] -> Type -> Bool
isParameter names p = p `elem` [Class n [] | n <- names]

-- The referee pattern p of a reference parameter against the argument type
-- a, both normalized.  The qualifiers at the top of the pattern are taken
-- off the argument when it has them; what the argument has beyond them
-- stays, and the rest of the pattern must agree with it.
deduceReferee :: Subst -> Type -> Type -> Bool
deduceReferee env p a = deducePattern True env base rest
  where
    (cp, vp, base) = splitCv p
    (ca, va, ba)   = splitCv a
    rest = qualify (ca && not cp) (va && not vp) ba

-- The pattern p against the argument type a, both normalized and without
-- top-level qualifiers.  The flag tells whether the pointee of a pointer
-- pattern may be more cv-qualified than the pointee of the argument.
deducePattern :: Bool -> Subst -> Type -> Type -> Bool
deducePattern more env p a = case p of
    Ptr q      -> kind a == KPtr && deducePointee more env q (pointee a)
    MemPtr c q -> kind a == KMemPtr && instantiate env c =:= memberClass a
                  && deducePointee more env q (memberOf a)
    Fund _     -> exact
    Const _    -> exact
    Volatile _ -> exact
    LRef _     -> exact
    RRef _     -> exact
    Arr _ _    -> exact
    Fun _ _    -> exact
    Class _ _  -> exact
  where
    exact = instantiate env p =:= a

-- The pointee pattern q against the pointee b of the argument.  When the
-- flag allows, the pattern may have qualifiers that the argument lacks.
-- The qualifiers of the pattern come off the argument, and the rest must
-- agree.  The next level may add a qualifier only when this level is const.
deducePointee :: Bool -> Subst -> Type -> Type -> Bool
deducePointee more env q b =
  (more || not extra) && deducePattern (more && cq) env base rest
  where
    (cq, vq, base) = splitCv q
    (cb, vb, bb)   = splitCv b
    extra = (cq && not cb) || (vq && not vb)
    rest  = qualify (cb && not cq) (vb && not vq) bb

-- The type a pointer points to, and the class and the member type of a
-- pointer to member.
pointee :: Type -> Type
pointee (Ptr u) = u

memberClass :: Type -> Type
memberClass (MemPtr c _) = c

memberOf :: Type -> Type
memberOf (MemPtr _ u) = u

-- Partial ordering ----------------------------------------------------------------

-- Whether a template matches a target type.  The set function encapsulates
-- the free variables of the deduction and turns failure into an empty set.
matches :: Template -> Type -> Bool
matches tmpl target = notEmpty (set2 deduceArgs tmpl target)

-- p is at least as specialized as q when q can be deduced from p with p's
-- parameters replaced by synthesized classes ([temp.class.order],
-- [temp.func.order]).
atLeastAsSpecialized :: Template -> Template -> Bool
atLeastAsSpecialized p q = matches q (synthesize 1 p)

-- The outcome of a choice among partial specializations.  The constructors
-- share no name with those of CxxOverload.Resolution, so that a module can
-- import both modules.
data Choice = Chosen String | Tied [String] | NoMatch
  deriving (Eq, Show)

-- The most specialized of the named templates whose pattern matches the
-- target ([temp.class.spec.match]): Chosen when one match is at least as
-- specialized as every other match, Tied with the maximal matches when
-- there is no such match, NoMatch when nothing matches.  A primary template
-- is listed like a specialization, with the pattern T.
mostSpecialized :: [(String, Template)] -> Type -> Choice
mostSpecialized cands target = case maximal of
    []         -> NoMatch
    (n : rest) -> if null rest then Chosen n else Tied maximal
  where
    matching = [(n, t) | (n, t) <- cands, matches t target]
    maximal  = [n | (n, t) <- matching, not (any (beats t) matching)]
    beats t (_, u) = atLeastAsSpecialized u t && not (atLeastAsSpecialized t u)

-- A bounded generator ----------------------------------------------------------
--
-- Every type of depth at most n, one per value.  The depth of a type is the
-- number of constructors on its longest path, so int has depth 0, int const
-- depth 1 and int const* depth 2.  Depth 0 holds the fundamental types and
-- one class, Foo.  Each further level adds one constructor: const or
-- volatile, a pointer, an lvalue or an rvalue reference, an array of each
-- bound in arrayBounds, a pointer to a member of Foo, or a function type
-- that returns the type and takes each parameter list in paramLists.  There
-- are 18 types of depth at most 0, 194 of depth at most 1, 1245 of depth at
-- most 2 and 7330 of depth at most 3.
--
-- The generator builds only well-formed types in normal form, so that every
-- C++ type appears once.  Left out: references to references ([dcl.ref]),
-- references to cv void, cv-qualified references, pointers to references
-- ([dcl.ptr]), arrays of references, of functions or of cv void
-- ([dcl.array]), pointers to members of reference type or of cv void
-- ([dcl.mptr]), functions that return an array or a function ([dcl.fct]),
-- cv-qualified functions, a repeated qualifier, volatile outside const, and
-- a qualifier on an array: the qualifiers of an array are those of its
-- elements ([basic.type.qualifier]), and the generator qualifies the
-- elements.  The parameter types of a function are adjusted already, so
-- the generator takes them from paramLists.
--
-- The generator is constructive.  A sub-generator per category of types
-- builds each compound from the categories its operand may come from, so no
-- alternative is built and then rejected.  An earlier version tested each
-- compound with a guard on the structure of its operand.  A search over
-- that generator was four times slower at depth 2 and 25 times slower at
-- depth 3, because a rejected alternative is a branch of the search until
-- its guard fails.  The generator calls no trait, so a check of the traits
-- against it examines the traits alone.

-- The one class of the generator.  Pointers to members point into it.
theClass :: Type
theClass = Class "Foo" []

-- The array bounds of the generator.  One bound keeps the count of types
-- small; the traits do not look at the bound.
arrayBounds :: [Int]
arrayBounds = [3]

-- The parameter lists of the function types of the generator: no parameter,
-- one, or two.  The traits do not look at the parameters.
paramLists :: [[Type]]
paramLists = [[], [Fund Int], [Fund Int, Fund Double]]

-- Every well-formed type of depth at most n: an object type or cv void,
-- with or without qualifiers, a reference, or a function type.
anyType :: Int -> Type
anyType n = cvType True n ? refType n ? funType n

-- The categories.  Each function yields every type of its category of
-- depth at most n, and nothing when n is below the depth of the smallest.
-- The flag tells whether cv void is in the category: an array element, a
-- referee and the type of a member are never cv void.

-- Neither a reference nor a function: a fundamental type, a class, a
-- pointer, a pointer to member or an array, with or without qualifiers.
cvType :: Bool -> Int -> Type
cvType void n = plainType void n ? qualified void n

-- The unqualified types of cvType.
plainType :: Bool -> Int -> Type
plainType void n = plainNoArr void n ? arrayType n

-- The unqualified types of cvType that are not arrays.
plainNoArr :: Bool -> Int -> Type
plainNoArr void n = leaf void ? deeper
  where
    deeper = if n < 1 then failed
             else Ptr (nonRef (n - 1)) ? MemPtr theClass (memberType (n - 1))

-- The types of depth 0.
leaf :: Bool -> Type
leaf void = Fund (anyOf (if void then funds else nonVoid)) ? theClass
  where
    nonVoid = [f | f <- funds, f /= Void]

-- An array of each bound of an object type other than cv void.
arrayType :: Int -> Type
arrayType n = if n < 1 then failed
              else Arr (cvType False (n - 1)) (anyOf arrayBounds)

-- const, volatile and const volatile on an unqualified type that is not an
-- array: the qualifiers of an array are those of its elements.
qualified :: Bool -> Int -> Type
qualified void n = if n < 1 then failed else Const u ? Volatile u ? both
  where
    u = plainNoArr void (n - 1)
    both = if n < 2 then failed else Const (Volatile (plainNoArr void (n - 2)))

-- Anything but a reference: a pointee.
nonRef :: Int -> Type
nonRef n = cvType True n ? funType n

-- Not a reference and not cv void: a referee, or the type of a member.
memberType :: Int -> Type
memberType n = cvType False n ? funType n

-- An lvalue or an rvalue reference.
refType :: Int -> Type
refType n = if n < 1 then failed else LRef r ? RRef r
  where
    r = memberType (n - 1)

-- A function that takes each parameter list and returns anything but an
-- array or a function.
funType :: Int -> Type
funType n = if n < 1 then failed
            else Fun (returnType (n - 1)) (anyOf paramLists)

returnType :: Int -> Type
returnType n = plainNoArr True n ? qualified True n ? refType n

-- Whether the outermost constructor of a term is a reference, with no
-- normalization.
headIsReference :: Type -> Bool
headIsReference t = kind t == KLRef || kind t == KRRef

-- The depth of a type: the number of constructors on its longest path.
depth :: Type -> Int
depth t = case t of
  Fund _     -> 0
  Class _ as -> maxDepth as
  Const u    -> 1 + depth u
  Volatile u -> 1 + depth u
  Ptr u      -> 1 + depth u
  LRef u     -> 1 + depth u
  RRef u     -> 1 + depth u
  Arr e _    -> 1 + depth e
  Fun r ps   -> 1 + max (depth r) (maxDepth ps)
  MemPtr c u -> 1 + max (depth c) (depth u)

maxDepth :: [Type] -> Int
maxDepth ts = foldr max 0 (map depth ts)
