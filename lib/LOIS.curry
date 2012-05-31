module LOIS where

import qualified FlatCurry

{-
This module defines a data structure that describes a LOIS rewrite system. It is based on simple definitional trees with simple extensions to allow built-in types.

Symbols are identified by a qualified name (QName) to match the curry design. The backend can encode these names in any way it likes when compiling the program.

See also the ShowLOIS module. It pretty prints LOIS programs.
-}

{-
A complete program made up of a list of constructors and operations.

The order of the lists is not important. Forward references and recursion are allowed without any special handling.
-}
data Program = Program [TypeDecl] [OperationDecl]

{-
How we identify local variables.
-}
type VariableID = Int

{-
How we identify global symbols.

FlatCurry.QName is (String, String). The first string is the name of the module that the symbol is defined in and the second is the actual name of the symbol in that module.
-}
type QName = FlatCurry.QName

{-
A symbol from the rewrite system. 

The symbols are tagged with their kind. To match against Symbols without regard to kind see the function symbol (at the bottom of this file).
-}
data Symbol = OperationSym QName
            | ConstructorSym QName 

{-
A declaration of a constructor

In the rest of the IL it is referenced by a ConstructorSym with the same QName as this declaration. The second argument is the constructor's arity. 
-}
data ConstructorDecl = ConstructorDecl QName Int

{-
A declaration of an algabraic data type

The first argument is the name of the type and the second is a list of constructors that are declared in this type.
-}
data TypeDecl = TypeDecl QName [ConstructorDecl]

{-
A declaration of a operation

In the rest of the IL it is referenced by a OperationSym with the same QName as this declaration. The second argument is the operation's arity.
-}
data OperationDecl = OperationDecl QName Int DefinitionalTree

{- 
A Definitional Tree Node. 

The lists of VariableIDs assign IDs to the parts of the expression being matched. This allows the Expr or sub-definitional-trees in the Rule to reference it. Variables can only be referenced from nodes that are decendants of the node that binds them. For example the Expr in a Rule can reference any VariableID above the Rule in the tree. 

Branch:
This declares an induction over a specific variable.

The RulePattern should always be a NodePattern. LitPattern does not make any sense in this context. The VariableID selects the previously bound value that we are inducing on. The variable must have been bound by a parent in the definitional tree. This blurs the line between code and a definitional tree but it is convenient. 

The boolean specifies whether the Branch is complete (in that it has a subtree for every constructor of the type). If this is True then the branch should have a subtree for EVERY value of that type. Any values that are not handled should have Exempt trees. If this is False, then any missing cases should be treated as if their where an Exempt node for them. This is mainly useful for large or infinite types like Integers.

Rule:
This declares a leaf node that specifies a rewrite.

Exempt:
This declares a pattern that may happen but is not handled and should be rewritten as Failure. This is the only way to introduce failure.

BuiltIn:
This tells the system that this operation is not defined using a definitional tree and will be implemented directly in the target language. The string argument will tell the backend what function to call in the target language to handle this operation.

BuiltIn should only be used at the top level.
-}
data DefinitionalTree = Branch RulePattern VariableID Bool [DefinitionalTree]
                      | Rule RulePattern Expr
                      | Exempt RulePattern
                      | BuiltIn String

{-
A pattern for a definitional tree node.

NodePattern:
A pattern matching a constructor node (or operation node at the very root of a definitional tree) and extracting its operands into local variables.

LitPattern:
A pattern matching a specific literal value. It binds no locals because it is matching against an atomic value so the induction variable is the value specified exactly.
-}
data RulePattern = NodePattern Symbol [VariableID]
                 | LitPattern Literal

{-
The right-hand-side of a Rule in the definitional tree. 

This represents both the rewriting or replacement of a node and the creation of new nodes. For example the Rule:

(f 1 2) -> (S (add 1 2))

will cause an f node to be replace or rewritten to be an S node with a single operand that is a new add node with the 2 operands to f as it's 2 operands. So the S node will not be created, it will just exist as a rewrite of the f-node. How this is handled is implementation specific.

Variable:
A reference to a variable bound by a ancestor of the Rule (or the Rule itself) in the definitional tree. This should always be handled by using a reference to the term in the variable (such as a pointer in an operand list or an indirection node). This is important because without it computation can be duplicated under some circumstances.

Node:
A node with a symbol and operands. The symbol can be either an operation or a constructor.

Choice:
A choice node with a fresh ID and with the 2 specified operands. 

LitNode:
A node with a built-in type value in it. The value is specified by the argument.

Generator:
A generator node (aka a free variable).

Partial:
A partial application node. This represents the symbol applied to some number of arguments LESS than it's arity.

-}
data Expr = Variable VariableID
          | Node Symbol [Expr]
          | Choice Expr Expr
          | LitNode Literal
          | Generator
          | Partial Symbol [Expr]

{-
A literal value of a built-in type. These are the 3 built-in types in curry.
-}
data Literal = LInt Int
             | LChar Char
             | LFloat Float

-- Utility functions

{-
A function from a name to a symbol of either kind. This is useful for pattern matching as it works well as a function pattern to extract the name from either kind of symbol. For example: -}

getSymbolName (symbol n) = n

symbol n = OperationSym n
symbol n = ConstructorSym n

pattern pat = Branch pat unknown unknown unknown
pattern pat = Rule pat unknown
pattern pat = Exempt pat

constructors (Program types _) = concatMap (\(TypeDecl _ l) -> l) types

symbolIsHNF (OperationSym _) = False
symbolIsHNF (ConstructorSym _) = True
