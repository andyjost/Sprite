--- Parsing error for operator definitions which directly follow an import
--- statement
--- Redmine - curry-frontend - bug #494

import Prelude

($) :: (a -> b) -> a -> b
($) f x = f x
