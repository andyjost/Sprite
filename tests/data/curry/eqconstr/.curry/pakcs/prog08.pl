%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog08).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog08.f',f,0,'prog08.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog08.main',main,0,'prog08.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog08.f'(_G486085,_G486086,_G486087):-freeze(_G486086,'blocked_prog08.f'(_G486085,_G486086,_G486087)).
'blocked_prog08.f'('Prelude.True',_G486126,_G486126).

'prog08.main'(_G486500,_G486501,_G486502):-freeze(_G486501,'blocked_prog08.main'(_G486500,_G486501,_G486502)).
'blocked_prog08.main'(_G486618,_G486621,_G486624):-hnf('Prelude.=:='('prog08.f','Prelude.False'),_G486618,_G486621,_G486624).

:-costCenters(['']).




%%%%% Number of shared variables: 0
