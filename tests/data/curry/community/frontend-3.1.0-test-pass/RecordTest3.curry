--- Internal error in record parsing
--- Redmine - curry-frontend - bug #9

module RecordTest3 where

data Options = Opts { optHelp :: Bool }

options :: [Options -> Options]
options = []

parseOpts :: Options
parseOpts = foldl (flip ($)) Opts { optHelp = False } opts
  where opts = options
