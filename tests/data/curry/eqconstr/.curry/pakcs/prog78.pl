%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog78).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog78.main',main,0,'prog78.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog78.main'(_G483123,_G483124,_G483125):-freeze(_G483124,'blocked_prog78.main'(_G483123,_G483124,_G483125)).
'blocked_prog78.main'(_G483633,_G483636,_G483639):-makeShare(_G483159,_G483695),makeShare(_G483168,_G483705),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483695,_G483705),'Prelude.&'('Prelude.=:='('Prelude.True',_G483695),'Prelude.=:='(_G483705,'Prelude.False'))),_G483695),_G483633,_G483636,_G483639).

:-costCenters(['']).




%%%%% Number of shared variables: 2
