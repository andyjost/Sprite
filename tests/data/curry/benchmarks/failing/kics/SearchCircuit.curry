import CLPR -- Constraints for Floats

type Voltage = Float
type Current = Float
data Circuit = Res Float           -- Resistance
             | Seq Circuit Circuit -- Sequence
             | Par Circuit Circuit -- Parallel

circuit :: Circuit -> Voltage -> Current -> Success
circuit (Res r)     u i = u =:= r *. i
circuit (Seq c1 c2) u i = circuit c1 u1 i
                        & circuit c2 u2 i
                        & u1 +. u2 =:= u
                        where u1, u2 free
circuit (Par c1 c2) u i = circuit c1 u i1
                        & circuit c2 u i2
                        & i1 +. i2 =:= i
                        where i1, i2 free

c :: Circuit
c = Seq (Res 180.0) (Res 470.0)

main | circuit c 5.0 i = i where i free
