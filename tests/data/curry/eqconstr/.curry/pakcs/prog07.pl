%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog07).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog07.f',f,0,'prog07.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog07.main',main,0,'prog07.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog07.f'(_G486088,_G486089,_G486090):-freeze(_G486089,'blocked_prog07.f'(_G486088,_G486089,_G486090)).
'blocked_prog07.f'('Prelude.True',_G486129,_G486129).

'prog07.main'(_G486503,_G486504,_G486505):-freeze(_G486504,'blocked_prog07.main'(_G486503,_G486504,_G486505)).
'blocked_prog07.main'(_G486621,_G486624,_G486627):-hnf('Prelude.=:='('Prelude.False','prog07.f'),_G486621,_G486624,_G486627).

:-costCenters(['']).




%%%%% Number of shared variables: 0
