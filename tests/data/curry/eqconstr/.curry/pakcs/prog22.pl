%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog22).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog22.main',main,0,'prog22.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog22.main'(_G478156,_G478157,_G478158):-freeze(_G478157,'blocked_prog22.main'(_G478156,_G478157,_G478158)).
'blocked_prog22.main'(_G478452,_G478455,_G478458):-hnf('Prelude.=:='(['Prelude.True'|_G478201],[_G478192|_G478210]),_G478452,_G478455,_G478458).

:-costCenters(['']).




%%%%% Number of shared variables: 0
