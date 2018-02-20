-- a one-pass assembler:
-- translate arbitrary jump-instructions into machine code
-- use logical variables to resolve forward jump addresses

-- we consider only two assembler instructions: jumps and labels
data Instruction = Jump LabelId | Label LabelId

-- we consider only a few number of label identifiers (could also be strings):
data LabelId = L0 | L1 | L2 | L3 | L4 | L5 | L6 | L7 | L8 | L9


-- implementation of the symbol table:
-- list of pairs consisting of labelids and codeaddresses
type SymTab = [(LabelId,Int)]

assembler :: [Instruction] -> SymTab -> Int -> [Int]

assembler [] _ _ = []
assembler (Jump l : ins) st a 
  | lookupST l st label st1  = 9:label:assembler ins st1 (a+2)
  where label,st1 free
assembler (Label l : ins) st a 
  | st1 =:= insertST l a st   = assembler ins st1 a
  where st1 free

-- insert an address of a labelid in a symboltable:
insertST l a []  = [(l,a)]
insertST l a ((l1,a1):st) | (l==l1)=:=True & a=:=a1 = (l1,a1):st
insertST l a ((l1,a1):st) | (l==l1)=:=False         = (l1,a1):(insertST l a st)

-- lookup an address of a labelid in a symboltable:
lookupST l [] a st1  = st1=:=[(l,a)]
lookupST l ((l1,a1):st) a st1 =
  if l==l1 then a=:=a1 & st1=:=(l1,a1):st
           else let st2 free in lookupST l st a st2 & st1=:=(l1,a1):st2


-- Goal:

goal = assembler [Label L0, Jump L1, Jump L0, Label L1] [] 0

-----> Result: [9,4,9,0]
