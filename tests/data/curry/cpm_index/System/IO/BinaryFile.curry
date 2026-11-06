-- Minimal interface for CPM binary-file primitive regression tests.
module System.IO.BinaryFile where
import System.IO (Handle, IOMode)

openBinaryFile :: String -> IOMode -> IO Handle
openBinaryFile filename mode = (prim_openBinaryFile $## filename) $# mode
prim_openBinaryFile :: String -> IOMode -> IO Handle
prim_openBinaryFile external

hGetByte :: Handle -> IO Int
hGetByte h = prim_hGetByte $# h
prim_hGetByte :: Handle -> IO Int
prim_hGetByte external

hPutByte :: Handle -> Int -> IO ()
hPutByte h byte = (prim_hPutByte $# h) $## byte
prim_hPutByte :: Handle -> Int -> IO ()
prim_hPutByte external
