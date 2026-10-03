-- Programs for unit_io_bind.py.  The goals take the file names they use from
-- the test, or write to the working directory, where the test reads them.
module IOBind where

readLength :: String -> IO Int
readLength f = readFile f >>= return . length

readText :: String -> IO String
readText f = readFile f

getCharOrd :: IO Int
getCharOrd = getChar >>= return . ord

writeThenAppend :: String -> IO ()
writeThenAppend f = writeFile f "ab" >> appendFile f "cd"

-- Two long writes in parallel alternatives, which interrupt each other.
twoWrites :: Int -> IO ()
twoWrites n = writeFile "a.txt" (concat (replicate n "abcd"))
            ? writeFile "b.txt" (concat (replicate n "wxyz"))

-- A choice at the inductive position of a monadic step is an error.
putCharNondet :: IO ()
putCharNondet = putChar ('a' ? 'b')

putStrLnNondet :: IO ()
putStrLnNondet = putStrLn ("one" ? "two")

bindNondet :: IO ()
bindNondet = (return (1 :: Int) ? return 2) >>= print

readFileNondet :: IO String
readFileNondet = readFile ("a.txt" ? "b.txt")

writeNondet :: String -> IO ()
writeNondet f = writeFile f ("ab" ++ ("c" ? "d"))

appendNondet :: String -> IO ()
appendNondet f = appendFile f ("x" ? "y")

-- The choice is met by map and foldr, which are not monadic steps, so it is
-- pull-tabbed to the top and the action forks.
mapMNondet :: String -> IO ()
mapMNondet f = mapM_ (appendFile f . (:[])) ("ab" ? "cd")

-- The handler receives the NondetError value.
catchNondet :: IO ()
catchNondet = catch (putChar ('a' ? 'b')) writeError

-- A function that calls an IO function is monadic, so the choice it
-- evaluates in its guard is an error on the C++ backend.
monadicGuard :: IO ()
monadicGuard = guarded (1 ? (-1))

guarded :: Int -> IO ()
guarded x | x > 0 = putStrLn "pos"
          | otherwise = putStrLn "neg"

-- ioError keeps the IOError value.
catchValue :: IO ()
catchValue = catch (ioError (userError "boom")) writeError

-- Prelude.error sets a message and no value.
catchError :: IO ()
catchError = catch (error "boom") writeError

-- The handler raises an error of its own.
catchTwice :: IO ()
catchTwice = catch (ioError (userError "first"))
                   (\_ -> ioError (userError "second"))

writeError :: IOError -> IO ()
writeError e = writeFile "err.txt" (show e)
