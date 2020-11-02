%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_173).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_173.main',main,0,'a0_173.main',nofix,'TCons'('a0_173.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_173.A','A',0,'A',0,'TCons'('a0_173.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_173.main'(_G484039,_G484040,_G484041):-freeze(_G484040,'blocked_a0_173.main'(_G484039,_G484040,_G484041)).
'blocked_a0_173.main'(_G484542,_G484545,_G484548):-makeShare(_G484084,_G484610),makeShare(_G484075,_G484620),hnf('Prelude.?'(_G484610,'Prelude.?'(_G484620,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G484610,'a0_173.A'),'Prelude.=:='(_G484620,_G484610)),_G484610))),_G484542,_G484545,_G484548).

:-costCenters(['']).




%%%%% Number of shared variables: 2
