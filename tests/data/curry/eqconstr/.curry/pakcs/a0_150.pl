%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_150).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_150.main',main,0,'a0_150.main',nofix,'TCons'('a0_150.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_150.A','A',0,'A',0,'TCons'('a0_150.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_150.main'(_G484039,_G484040,_G484041):-freeze(_G484040,'blocked_a0_150.main'(_G484039,_G484040,_G484041)).
'blocked_a0_150.main'(_G484542,_G484545,_G484548):-makeShare(_G484075,_G484616),makeShare(_G484084,_G484626),hnf('Prelude.?'(_G484616,'Prelude.?'(_G484626,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G484616,_G484626),'Prelude.=:='('a0_150.A',_G484626)),_G484616))),_G484542,_G484545,_G484548).

:-costCenters(['']).




%%%%% Number of shared variables: 2
