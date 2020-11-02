%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog93).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog93.main',main,0,'prog93.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog93.main'(_G483117,_G483118,_G483119):-freeze(_G483118,'blocked_prog93.main'(_G483117,_G483118,_G483119)).
'blocked_prog93.main'(_G483627,_G483630,_G483633):-makeShare(_G483153,_G483689),makeShare(_G483162,_G483699),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483689,_G483699),'Prelude.&'('Prelude.=:='(_G483699,'Prelude.False'),'Prelude.=:='(_G483689,'Prelude.True'))),_G483689),_G483627,_G483630,_G483633).

:-costCenters(['']).




%%%%% Number of shared variables: 2
