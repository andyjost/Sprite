notCase x = case x of
  True  -> False
  True  -> False
  False -> True
  v     -> v

notP True  = False
notP True  = False
notP False = True
notP v     = v

notFCase x = fcase x of
  True  -> False
  True  -> False
  False -> True
  v     -> v
