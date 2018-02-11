-- a mail widget to write and send an email with a "search"
-- button to search an email address by querying an address server

import Tk
import Ports
import System

mail_widget =
 TkCol [] [
   TkLabel [TkText "A simple mail composer:"],
   TkMatrix [TkLeft]
    [[TkLabel [TkText "To:"], 
      TkRow [] 
        [TkEntry [TkRef to, TkWidth 30, TkFillX],
         TkButton lookup [TkText "Search for email:"],
         TkEntry [TkRef name, TkText "<name (unique prefix)>", TkCmd lookup, TkFillX]]],
     [TkLabel [TkText "Subject:"],
      TkEntry [TkRef subject, TkWidth 60, TkFillX]]],
   TkTextEdit [TkRef txt, TkBackground "yellow", TkFill],
   TkRow [] [TkButton sendmail [TkText "Send"],
             TkButton tkExit [TkText "Cancel"]]
  ]
 where to,name,subject,txt free

       lookup wp = do name_cont <- tkGetValue name wp
                      ap <- connectPort (serverport++"@"++serverhost)
                      doSend (GetEmail name_cont email) ap
                      tkSetValue to email wp
                   where email free

       sendmail wp =
         do to_cont  <- tkGetValue to wp
            sub_cont <- tkGetValue subject wp
            msg_cont <- tkGetValue txt wp
            writeFile "tmp.mailtext" msg_cont
            system ("Mail -s \""++sub_cont++"\" "++to_cont++" < tmp.mailtext")
            system "rm tmp.mailtext"
            tkExit wp


main = runWidget "Mail Demo" mail_widget



-- the messages of the address server:
data AddrReq = GetName String String | GetKey String String
             | GetNameHtml String String | GetHtmlList String String
             | GetEmail String String
             | Reload | Close

-- the port for communicating with the address server:
serverport = "addr_server"

-- the host machine of the address server:
--serverhost = "margaux.informatik.rwth-aachen.de"
serverhost = "localhost"
