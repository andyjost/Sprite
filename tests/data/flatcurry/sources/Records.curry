module Records where
data Rec = Rec { field :: Int } deriving (Eq,Show)
newtype Box = Box Int
goal = field (Rec 3)
unbox (Box x) = x
