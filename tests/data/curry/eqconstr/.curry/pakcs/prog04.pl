%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog04).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog04.f',f,0,'prog04.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog04.main',main,0,'prog04.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog04.f'(_G485838,_G485839,_G485840):-freeze(_G485839,'blocked_prog04.f'(_G485838,_G485839,_G485840)).
'blocked_prog04.f'('Prelude.True',_G485879,_G485879).

'prog04.main'(_G486253,_G486254,_G486255):-freeze(_G486254,'blocked_prog04.main'(_G486253,_G486254,_G486255)).
'blocked_prog04.main'(_G486371,_G486374,_G486377):-hnf('Prelude.=:='('prog04.f','prog04.f'),_G486371,_G486374,_G486377).

:-costCenters(['']).




%%%%% Number of shared variables: 0
