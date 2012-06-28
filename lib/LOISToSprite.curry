module LOISToSprite(translate, translateMain) where

import Char(isAlphaNum)
import CompactFlatCurry
import List
import Maybe
import qualified FlatCurryToLOIS
import qualified LOIS
import qualified ShowLOIS
import Sort 
import System 
import IO
import Util

{-
    Mangles a name.

    In C++, names beginning with an underscore followed by a capital letter and
    names containing double-underscores are illegal.  Moreover, identifiers
    must contain only alphanumeric characters and underscores, whereas many
    other symbols are allowed in Curry.

    This mangling scheme encodes a Curry identifier as a valid C++ identifier.
    It consists of a prefix followed by the length of the unmangled name
    followed by an escaped version of the unmangled name.  The prefix is m_
    (modules), op_ (operations), c_ (constructors) or h_ (H-functions).  All
    non-alphnumeric characters (including underscores) are escaped by
    replacement with _xNx where N is the ascii character code of the original
    character.
  -}
mangle prefix str = prefix ++ (show $ length str) ++ (concat $ map aux str)
    where aux ch = if (isAlphaNum ch) then [ch] else "_x" ++ (show $ ord ch) ++ "x"

moduleName :: String -> String
moduleName s = mangle "m_" s

ctorName :: String -> String
ctorName s = mangle "c_" s

ctorLabelName :: String -> String
ctorLabelName s = mangle "cl_" s

operName :: String -> String
operName s = mangle "op_" s

hfuncName :: String -> String
hfuncName s = mangle "h_" s

fullCtorName :: LOIS.QName -> String
fullCtorName (m,s) = (moduleName m) ++ "::" ++ (ctorName s)

fullOperName :: LOIS.QName -> String
fullOperName (m,s) = (moduleName m) ++ "::" ++ (operName s)

{-
    Generates the path to a variable in a definitional tree.  The path returned
    uses zero-based indexing, i.e., the first child has index 0.  Since the
    definitional tree uses a one-based index, we subtract one internally
    (below).
 -}
getPath :: LOIS.DefinitionalTree -> Int -> Maybe [Int]
getPath dtree var = aux dtree
    where
        aux (LOIS.Branch pat id _ tree) =
            let elem = checkPat pat var in
            if (isJust elem) then elem else
                let path = listToMaybe (catMaybes (map aux tree)) in
                let this = checkPat pat id in -- must succeed
                if (isNothing path) then Nothing else Just (fromJust this ++ fromJust path)
        aux (LOIS.Rule pat _) = checkPat pat var
        aux (LOIS.Exempt pat) = checkPat pat var
        aux (LOIS.BuiltIn _) = Nothing

        -- Check the pattern for an instance of the target variable.
        checkPat (LOIS.NodePattern _ vars) var' =
            let idx = elemIndex var' vars in
            if (isJust idx) then Just [fromJust idx] else Nothing
        checkPat (LOIS.LitPattern _) _ = Nothing

{-
    Gets a path (exactly like getPath) but formats it for output to the Sprite
    C++ code as a sequence initialization.
 -}
fmtPathForInit :: LOIS.DefinitionalTree -> Int -> String
fmtPathForInit dtree var =
  let path = getPath dtree var in
  "(" ++ (mkString ")(" (map show (fromJust path))) ++ ")"

{-
    Gets a path (exactly like getPath) but formats it for output to the Sprite
    C++ code as a node lookup expression (relative to root).
 -}
fmtPathForLookup :: LOIS.DefinitionalTree -> Int -> String -> String
fmtPathForLookup dtree var root =
  let path = getPath dtree var in
  foldl aux root (fromJust path)
    where
        aux x i = x ++ "[" ++ (show i) ++ "]"

-- Returns an symbol name.
symName modname (LOIS.OperationSym (q,n)) =
    qualifyName modname q "->" (operName n)
symName modname (LOIS.ConstructorSym (q,n)) =
    qualifyName modname q "::" (ctorName n)

-- Qualify a symbol name (the symbol is already mangled, so mangle the module
-- name and prepend it).
qualifyName modname mod sep sym
    | modname == mod = sym
    | True           = (moduleName mod) ++ sep ++ sym

-- Returns the symbol info for rewriting (or creating).
symRewriteHead modname (LOIS.OperationSym qn@(q,n)) = aux
    where
        aux | qn == ("Prelude","+") = "OP_INT_ADD"
            | qn == ("Prelude","-") = "OP_INT_SUB"
            | qn == ("Prelude","*") = "OP_INT_MUL"
            | qn == ("Prelude","div") = "OP_INT_DIV"
            | qn == ("Prelude","mod") = "OP_INT_MOD"
            | qn == ("Prelude","<") = "OP_LT"
            | qn == ("Prelude","<=") = "OP_LE"
            | qn == ("Prelude","==") = "OP_EQ"
            | qn == ("Prelude","/=") = "OP_NE"
            | qn == ("Prelude",">=") = "OP_GE"
            | qn == ("Prelude",">") = "OP_GT"
            | True = qualifyName modname q "->" (operName n)

symRewriteHead modname (LOIS.ConstructorSym qn@(q,n)) = aux
    where
        aux | qn == ("Prelude","(,)") = "C_TUPLE2, CL_TUPLE2"
            | qn == ("Prelude","(,,)") = "C_TUPLE3, CL_TUPLE3"
            | qn == ("Prelude","(,,,)") = "C_TUPLE4, CL_TUPLE4"
            | qn == ("Prelude","(,,,,)") = "C_TUPLE5, CL_TUPLE5"
            | qn == ("Prelude","(,,,,,)") = "C_TUPLE6, CL_TUPLE6"
            | qn == ("Prelude","(,,,,,,)") = "C_TUPLE7, CL_TUPLE7"
            | qn == ("Prelude","(,,,,,,,)") = "C_TUPLE8, CL_TUPLE8"
            | qn == ("Prelude","(,,,,,,,,)") = "C_TUPLE9, CL_TUPLE9"
            | qn == ("Prelude",":") = "C_CONS, CL_CONS"
            | qn == ("Prelude","[]") = "C_NIL, CL_NIL"
            | True = qualifyName modname q "::" (ctorName n) ++ ", " ++
                     qualifyName modname q "->" (ctorLabelName n)

-- Looks up a symbol name.
symLookup modname (LOIS.NodePattern p _) = symName modname p
symLookup _ (LOIS.LitPattern (LOIS.LInt x)) = show x
symLookup _ (LOIS.LitPattern (LOIS.LChar x)) = "'" ++ show x ++ "'"
-- Can't case-match a float.
-- symLookup _ (LOIS.LitPattern (LOIS.LFloat x)) = ""

-- Compiles an operation definition into Sprite C++ code.
compile :: String -> LOIS.OperationDecl -> String
compile modname (LOIS.OperationDecl (_,s) _ dtree) =
    "    void " ++ (hfuncName s) ++ "(Node & root) const \n" ++
    "    {                                               \n" ++
    (aux0 0 dtree) ++
    "    }                                               \n" ++
    ""
    where
        symRewrite (LOIS.OperationSym _) = "rewrite_oper"
        symRewrite (LOIS.ConstructorSym _) = "rewrite_ctor"
        symCreate (LOIS.OperationSym _) = "Node::create<OPER>"
        symCreate (LOIS.ConstructorSym _) = "Node::create<CTOR>"
        -- Flattens a list into a string, placing xs before each element.
        -- E.g., mkStringTrailing ", " ["a", "b"] expands to ", a, b"
        mkStringTrailing xs xss = mkString "" (map (\x -> xs ++ x) xss)
        indent lvl = concat (take (lvl+3) $ repeat "  ")

        switchDelim (LOIS.pattern pat) = case pat of
            (LOIS.LitPattern (LOIS.LInt _))  -> ("SPRITE_VALUE_SWITCH_BEGIN(INT, ","SPRITE_VALUE_SWITCH_END")
            (LOIS.LitPattern (LOIS.LChar _)) -> ("SPRITE_VALUE_SWITCH_BEGIN(CHAR, ","SPRITE_VALUE_SWITCH_END")
            _                                -> ("SPRITE_SWITCH_BEGIN(","SPRITE_SWITCH_END")

        -- Utility for generating a switch statement.
        switch lvl (LOIS.Branch _ id _ tree) =
            let path = fmtPathForInit dtree id in
            let idt = indent lvl in
            let (swBegin,swEnd) = switchDelim (tree!!0) in
            -- DEBUG
            -- idt ++ swBegin ++ "root, parent, inductive, root, " ++ path ++ ")\n" ++
            idt ++ swBegin ++ "root, root, " ++ path ++ ")\n" ++
            mkString "\n" (map (aux0 (lvl+1)) tree) ++ "\n" ++
            idt ++ swEnd ++ "\n"

        -- Utility for generating a case clause.
        caseBegin lvl pat = case lvl of
            0 -> indent lvl
            _ -> indent lvl ++ "case " ++ symLookup modname pat ++ ": { "

        caseEnd lvl = case lvl of
            0 -> "\n"
            _ -> "}"

        {-
            Compiles one node of a definitional tree.  Branches generate a
            switch, and other types generate a case.
          -}
        aux0 lvl r@(LOIS.Branch pat _ _ _) =
            if lvl == 0 then
                -- Declare the local variables and generate a top-level switch.
                -- DEBUG
                -- (indent lvl) ++ "NodePtr parent, *inductive;\n" ++ switch lvl r
                switch lvl r
              else
                -- Generate a nested switch, indented.
                caseBegin lvl pat ++ "\n" ++
                switch (lvl+1) r ++
                caseEnd lvl
        aux0 lvl (LOIS.Rule pat expr) = caseBegin lvl pat ++ aux1 True expr ++ caseEnd lvl
        aux0 lvl (LOIS.Exempt pat) = caseBegin lvl pat ++ "return rewrite_fail(root);" ++ caseEnd lvl
        aux0 lvl (LOIS.BuiltIn name) = indent lvl ++ "return rewrite_oper(root, " ++ aux2 ++ ");\n"
            where
                aux2 | name == "SpritePrelude.failed" = "OP_FAILED"
                     | True = failed

        {-
            Generates C++ code for a rewrite step, according to the given
            expression.  The topmost call (i.e., the head of the expression)
            involves rewriting (or forwarding) a node.  All subsequent calls
            (in the same expression) just create a node.
         -}
        aux1 first (LOIS.Variable id) =
            let body = fmtPathForLookup dtree id "root" in
            if first then
                "return rewrite_fwd(root, " ++ body ++ ");"
              else
                body

        aux1 first (LOIS.Node sym exprs) =
            let body = symRewriteHead modname sym ++ mkStringTrailing ", " (map (aux1 False) exprs) in
            if first then
                "return " ++ (symRewrite sym) ++ "(root, " ++ body ++ ");"
              else
                (symCreate sym) ++ "(" ++ body ++ ")"

        aux1 first (LOIS.Choice lhs rhs) =
            let body = aux1 False lhs ++ ", " ++ aux1 False rhs in
            if first then
                "return rewrite_choice(root, " ++ body ++ ");"
              else
                "Node::create<CHOICE>(" ++ body ++ ")"

        aux1 True (LOIS.LitNode (LOIS.LInt x)) = "return rewrite_int(root, " ++ show x ++ ");"
        aux1 True (LOIS.LitNode (LOIS.LChar x)) = "return rewrite_char(root, " ++ show x ++ ");"
        aux1 True (LOIS.LitNode (LOIS.LFloat x)) = "return rewrite_float(root, " ++ show x ++ ");"

        aux1 False (LOIS.LitNode (LOIS.LInt x)) = "Node::create<INT>(" ++ show x ++ ")"
        aux1 False (LOIS.LitNode (LOIS.LChar x)) = "Node::create<CHAR>(" ++ show x ++ ")"
        aux1 False (LOIS.LitNode (LOIS.LFloat x)) = "Node::create<FLOAT>(" ++ show x ++ ")"

        aux1 _ LOIS.Generator = "Gen"
        aux1 _ (LOIS.Partial _ _) = "Partial"
    
-- Generates the C++ code for a Curry module in Sprite.
--
-- Only the definitions qualified by the given named module are generated.
translate fh modname' (LOIS.Program _ types' opers') = do
  -- Select only the relevant definitions.
  let types = filter (\(LOIS.TypeDecl (m,_) _) -> m == modname') types'
  let opers = filter (\(LOIS.OperationDecl (m,_) _ _) -> m == modname') opers'

  -- Generate the symbol definitions for this module.
  hPutStrLn fh  "#pragma once"
  hPutStrLn fh  "#include \"sprite/sprite.hpp\""
  hPutStrLn fh  ""
  hPutStrLn fh ("namespace sprite { namespace user { namespace " ++ modname)
  hPutStrLn fh  "{"

  -- Generate the construtor definitions.
  hPutStrLn fh ("  enum Constructor")
  hPutStrLn fh ("  {")
  hPutStrLn fh ("    " ++ mkString "\n    " (concat (map ctorInit types)))
  hPutStrLn fh (if (length types) == 0 then "    C_EMPTY_CTOR_LIST" else "")
  hPutStrLn fh ("  };")
  hPutStrLn fh  ""

  -- Generate the Module definition.
  hPutStrLn fh ("  struct Module : sprite::Module")
  hPutStrLn fh  "  {"
  hPutStrLn fh ("    static std::string name() { return \"" ++ modname' ++ "\"; }")

  hPutStrLn fh ("    " ++ mkString "\n    " (map operDecl opers))
  hPutStrLn fh ("    " ++ mkString "\n    " (concat (map ctorLabelDecl types)))
  hPutStrLn fh  ""
  hPutStrLn fh  "    typedef user::m_13SpritePrelude::Module Prelude;"
  hPutStrLn fh  "    shared_ptr<Prelude const> m_7Prelude;"
  hPutStrLn fh  ""

  -- Generate the module initialization code.
  hPutStrLn fh ("    Module(Program & pgm) : sprite::Module(pgm)")
  hPutStrLn fh  "    {"
  hPutStrLn fh ("      " ++ mkString "\n      " (map operInstall opers))
  hPutStrLn fh ("      " ++ mkString "\n      " (concat (map ctorInstall types)))
  hPutStrLn fh  "      m_7Prelude = pgm.import<Prelude>();"
  hPutStrLn fh  "    }"
  hPutStrLn fh  ""

  -- Generate the rule definitions.
  hPutStrLn fh  ""
  hPutStrLn fh  "  private:"
  hPutStrLn fh (mkString "\n" (map (\op -> compile modname' op) opers))
  hPutStrLn fh  "  };"
  hPutStrLn fh  "}}}"

      where
          modname = moduleName modname'

          ctorInit (LOIS.TypeDecl _ ctors) =
              map (aux " = CTOR,") (take 1 ctors) ++ map (aux ",") (drop 1 ctors)
              where
                  aux suffix (LOIS.ConstructorDecl (_,s) _) = (ctorName s) ++ suffix

          ctorLabelDecl (LOIS.TypeDecl _ ctors) = map aux ctors
              where
                  aux (LOIS.ConstructorDecl (_,s) _) = "size_t " ++ ctorLabelName s ++ ";"
              

          operDecl (LOIS.OperationDecl (_,s) _ _) = "size_t " ++ operName s ++ ";"

          operInstall (LOIS.OperationDecl (_,s) _ _) = 
              (operName s) ++ " = install_oper(\"" ++ s ++ "\", &Module::" ++ (hfuncName s) ++ ");"

          ctorInstall (LOIS.TypeDecl _ ctors) = map aux ctors
              where
                  aux (LOIS.ConstructorDecl (_,s) _) =
                      ctorLabelName s ++ " = install_ctor(\"" ++ s ++ "\");"

-- Translate the main module file.
translateMain fh modname' = do
  hPutStrLn fh  "#include <iostream>"
  hPutStrLn fh  "#include \"sprite/sprite.hpp\""
  hPutStrLn fh  ""
  hPutStrLn fh ("#include \"" ++ modname' ++ ".hpp\"")
  hPutStrLn fh  ""
  hPutStrLn fh  "using namespace sprite;"
  hPutStrLn fh  ""
  hPutStrLn fh  "int main(int argc, char *argv[])"
  hPutStrLn fh  "{"
  hPutStrLn fh  "  CmdlineOptions const opt = parse_options(argc, argv);"
  hPutStrLn fh  ""
  hPutStrLn fh  "  Program pgm;"
  hPutStrLn fh  "  std::cout << setprogram(pgm);"
  hPutStrLn fh  ""
  hPutStrLn fh ("  typedef user::" ++ modname ++ "::Module MainModule;")
  hPutStrLn fh  "  shared_ptr<MainModule const> main = pgm.import<MainModule>();"
  hPutStrLn fh  ""
  hPutStrLn fh  "  NodePtr goal = Node::create<OPER>(main->op_4main);"
  hPutStrLn fh  "  execute(pgm, *goal, opt.grain, opt.trace);"
  hPutStrLn fh  "  std::cout << setprogram(pgm) << *goal << std::endl;"
  hPutStrLn fh  ""
  hPutStrLn fh  "  return 0;"
  hPutStrLn fh  "}"
      where
          modname = moduleName modname'

ctorQname (LOIS.ConstructorDecl qn _) = qn
operQname (LOIS.OperationDecl qn _ _) = qn

-- Extracts the list of used symbols from a LOIS program.
symbols :: LOIS.Program -> [LOIS.QName]
symbols prog@(LOIS.Program _ _ types) =
    (map ctorQname (LOIS.constructors prog)) ++
    (map operQname types)

-- Extracts a unique list of used modules from a LOIS program.
depends prog = nub $ map fst $ symbols prog

