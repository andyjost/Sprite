--- Missing polymorphism of record labels
--- Redmine - curry-fronted - bug #445

--- I don't know if it's really a bug or I only don't understand records well.
--- The following gives a compiling error:

fun :: a -> Bool
fun _ = True

fun3 :: a -> a -> Bool
fun3 _ _ = False

data Rec a = Rec { a :: a, b :: Bool }

testRecSel1 = a Rec { a = 'c', b = True }

testRecSel2 x y = a Rec { a = fun x, b = fun3 y y }

--- The type of the record used in testRecSel1 somehow propagates
--- to the type of the record used in testRecSel2.
--- If one comments the definition of testRecSel1 then there is no error.
