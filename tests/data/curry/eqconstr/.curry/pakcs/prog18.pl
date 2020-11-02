%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog18).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog18.main',main,0,'prog18.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog18.main'(_G474636,_G474637,_G474638):-freeze(_G474637,'blocked_prog18.main'(_G474636,_G474637,_G474638)).
'blocked_prog18.main'(_G474767,_G474770,_G474773):-hnf('Prelude.=:='(_G474672,_G474681),_G474767,_G474770,_G474773).

:-costCenters(['']).




%%%%% Number of shared variables: 0
