------------------------------------------------------------------------------
--- A simple "addition" server to test the NamedSocket library.
---
--- @author Michael Hanus
--- @version April 2007
------------------------------------------------------------------------------

import NamedSocket
import IO
import Read(readInt)

-- The symbolic name for the server socket:
socketName = "addserver"

sendTo host msg = do
  h <- connectToSocket (socketName++"@"++host)
  hPutStr h msg
  hClose h

stopServer host = sendTo host "TERMINATE\n"


-- An "addition" server:
addServer = do
  socket <- listenOn socketName
  putStrLn $ "Serving socket: " ++ show socketName
  addServeSocket socket

addServeSocket socket = do
  (chost,stream) <- socketAccept socket
  putStrLn $ "Connection from "++chost
  serverLoop stream
 where
   serverLoop h = do
     l1 <- hGetLine h
     if l1=="TERMINATE"
      then hClose h
      else do l2 <- hGetLine h
              hPutStrLn h (show (readInt l1 + readInt l2))
              hClose h
              addServeSocket socket

addClient host x y = do
  h <- connectToSocket (socketName++"@"++host)
  hPutStr h (unlines (map show [x,y]))
  hFlush h
  answer <- hGetLine h
  putStrLn $ "Answer: "++answer
  hClose h

{-
Test with PAKCS:

:fork addServer
addClient "localhost" 3 4
stopServer "localhost"

-}
