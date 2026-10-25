-- Compile-only property interface for the community fixtures.
-- Adapters evaluate the original expressions, never these property operations.
-- Keeping this interface local avoids loading the unsupported Test.Prop.Types
-- hierarchy. An accidental property evaluation must fail visibly.
module Test.Prop (Prop, (-=-), (<~>), (<~~>), (~>), (==>), always, failing, is, solutionOf, (<=>)) where

data Prop = PropertyNotExecutable

infix 1 -=-, <~>, <~~>, ~>
infixr 0 ==>

(-=-) :: (Eq a, Show a) => a -> a -> Prop
_ -=- _ = error "community fixture: evaluate the expression, not the property"

(<~>) :: (Eq a, Show a) => a -> a -> Prop
_ <~> _ = error "community fixture: evaluate the expression, not the property"

(<~~>) :: (Eq a, Show a) => a -> a -> Prop
_ <~~> _ = error "community fixture: evaluate the expression, not the property"

(~>) :: (Eq a, Show a) => a -> a -> Prop
_ ~> _ = error "community fixture: evaluate the expression, not the property"

(==>) :: Bool -> Prop -> Prop
_ ==> _ = error "community fixture: evaluate the expression, not the property"

always :: Bool -> Prop
always _ = error "community fixture: evaluate the expression, not the property"

failing :: a -> Prop
failing _ = error "community fixture: evaluate the expression, not the property"

infix 1 `is`, <=>

is :: Show a => a -> (a -> Bool) -> Prop
is _ _ = error "community fixture: evaluate the expression, not the property"

solutionOf :: Data a => (a -> Bool) -> a
solutionOf _ = error "community fixture: evaluate the expression, not the property"

(<=>) :: a -> a -> Prop
_ <=> _ = error "community fixture: evaluate the expression, not the property"
