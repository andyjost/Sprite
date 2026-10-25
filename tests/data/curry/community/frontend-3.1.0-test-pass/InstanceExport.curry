module InstanceExport where

import InstanceExport.M
import InstanceExport.O
import InstanceExport.P

-- Import structure: (Exported types and classes are annotated)

--                         -> O (D)
--                        /        \
--    M (T, C) -> N (U, D) -> P (U) -> InstanceExport
--            \____________________/

-- The instances C U, C Bool and D T U are all defined in N.

-- Instance C U from N should be in scope, as it should be "bundled" with U,
-- which is imported through P (the instance is not bundled with C, as C is not
-- defined in N).
f1 :: U
f1 = methodC

-- Instance C Bool from N should be in scope, as it's an orphan instance and
-- these should be imported through both O and P, which both import N.
f2 :: Bool
f2 = methodC

-- Instance D T U from N should be in scope, as it should be "bundled" with D,
-- which is imported through O.
f3 :: Bool
f3 = methodD T U
