%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog06).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog06.f',f,0,'prog06.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog06.main',main,0,'prog06.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog06.f'(_G486035,_G486036,_G486037):-freeze(_G486036,'blocked_prog06.f'(_G486035,_G486036,_G486037)).
'blocked_prog06.f'('Prelude.True',_G486076,_G486076).

'prog06.main'(_G486450,_G486451,_G486452):-freeze(_G486451,'blocked_prog06.main'(_G486450,_G486451,_G486452)).
'blocked_prog06.main'(_G486568,_G486571,_G486574):-hnf('Prelude.=:='('prog06.f','Prelude.True'),_G486568,_G486571,_G486574).

:-costCenters(['']).




%%%%% Number of shared variables: 0
