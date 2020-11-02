%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog82).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog82.main',main,0,'prog82.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog82.main'(_G483123,_G483124,_G483125):-freeze(_G483124,'blocked_prog82.main'(_G483123,_G483124,_G483125)).
'blocked_prog82.main'(_G483633,_G483636,_G483639):-makeShare(_G483168,_G483701),makeShare(_G483159,_G483711),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483701,_G483711),'Prelude.&'('Prelude.=:='('Prelude.True',_G483711),'Prelude.=:='(_G483701,'Prelude.False'))),_G483711),_G483633,_G483636,_G483639).

:-costCenters(['']).




%%%%% Number of shared variables: 2
