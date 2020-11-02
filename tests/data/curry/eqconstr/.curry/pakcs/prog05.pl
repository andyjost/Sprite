%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog05).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog05.f',f,0,'prog05.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog05.main',main,0,'prog05.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog05.f'(_G486029,_G486030,_G486031):-freeze(_G486030,'blocked_prog05.f'(_G486029,_G486030,_G486031)).
'blocked_prog05.f'('Prelude.True',_G486070,_G486070).

'prog05.main'(_G486444,_G486445,_G486446):-freeze(_G486445,'blocked_prog05.main'(_G486444,_G486445,_G486446)).
'blocked_prog05.main'(_G486562,_G486565,_G486568):-hnf('Prelude.=:='('Prelude.True','prog05.f'),_G486562,_G486565,_G486568).

:-costCenters(['']).




%%%%% Number of shared variables: 0
