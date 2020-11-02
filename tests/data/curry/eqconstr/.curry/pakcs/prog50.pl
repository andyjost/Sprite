%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog50).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog50.main',main,0,'prog50.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog50.main'(_G481737,_G481738,_G481739):-freeze(_G481738,'blocked_prog50.main'(_G481737,_G481738,_G481739)).
'blocked_prog50.main'(_G482162,_G482165,_G482168):-makeShare(_G481773,_G482206),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482206,'Prelude.True'),'Prelude.=:='(_G482206,'Prelude.False')),_G482206),_G482206),_G482162,_G482165,_G482168).

:-costCenters(['']).




%%%%% Number of shared variables: 1
