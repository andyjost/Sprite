module RecordTest1 where

data Person = Person { firstName :: String, lastName :: String }
            | Agent  { lastName :: String, trueIdentity :: Person }

mike :: Person
mike = Person { firstName = "Mike", lastName = "Smith" }

jim = Person { lastName = "Parson", firstName = "Jim" }

jd :: Person
jd = Agent {}

newId :: Person -> Person -> Person
newId p i = p { trueIdentity = i }
