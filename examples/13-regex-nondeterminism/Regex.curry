-- Regular expressions by non-determinism.
--
-- A pattern denotes a set of words.  The function sem returns one word of
-- that set, and every word of the set is one value of sem.  The choice
-- operator ? stands for alternation and for the two cases of a star, ++
-- stands for sequence, and a free Char stands for the wildcard.
--
-- match unifies a word of the pattern with the subject.  grep splits the
-- subject into three free parts and asks the middle part to be a word of
-- the pattern.  The bindings of the free variables say where the hit is.

module Regex where

-- A pattern.  go.py builds these values from the textual pattern syntax.
data RE = Lit Char      -- one character
        | Any           -- any one character: .
        | Alt RE RE     -- one pattern or the other: |
        | Seq RE RE     -- one pattern, then the other
        | Star RE       -- zero or more times: *
        | Plus RE       -- one or more times: +
        | Opt RE        -- zero or one time: ?

-- One word of the language of the pattern.  Each word is one value.
sem :: RE -> String
sem (Lit c)   = [c]
sem Any       = [c] where c free
sem (Alt a b) = sem a ? sem b
sem (Seq a b) = sem a ++ sem b
sem (Star a)  = [] ? (nonEmpty (sem a) ++ sem (Star a))
sem (Plus a)  = sem a ++ sem (Star a)
sem (Opt a)   = [] ? sem a

-- The word itself when it is not empty.  The call fails on the empty word.
-- The recursive case of Star repeats only a non-empty word of its body, so
-- each unfolding consumes at least one character of the subject and the
-- recursion stops when the subject does.  Without this rule a body that
-- matches the empty word, as in (a?)*, would unfold forever.  The language
-- is the same: zero or more words of a set is zero or more of its non-empty
-- words.
nonEmpty :: String -> String
nonEmpty (c:cs) = c : cs

-- True when the whole subject is a word of the pattern.  When it is not,
-- the guard fails and the call has no value.
match :: RE -> String -> Bool
match r s | sem r =:= s = True

-- One hit of the pattern in the subject: the text before the hit, the hit,
-- and the text after it.  Each hit is one value.  The free variables pre,
-- hit and post split the subject, and the second constraint asks the
-- middle part to be a word of the pattern.
grep :: RE -> String -> (String, String, String)
grep r s | pre ++ hit ++ post =:= s & hit =:= sem r = (pre, hit, post)
  where pre, hit, post free
