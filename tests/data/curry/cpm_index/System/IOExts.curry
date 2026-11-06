module System.IOExts where
import System.IO
execCmd :: String -> IO (Handle, Handle, Handle)
execCmd command = prim_execCmd $## command
prim_execCmd :: String -> IO (Handle, Handle, Handle)
prim_execCmd external
connectToCommand :: String -> IO Handle
connectToCommand command = prim_connectToCmd $## command
prim_connectToCmd :: String -> IO Handle
prim_connectToCmd external
