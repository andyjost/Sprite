%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_175).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_175.main',main,0,'a0_175.main',nofix,'TCons'('a0_175.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_175.A','A',0,'A',0,'TCons'('a0_175.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_175.main'(_G484039,_G484040,_G484041):-freeze(_G484040,'blocked_a0_175.main'(_G484039,_G484040,_G484041)).
'blocked_a0_175.main'(_G484542,_G484545,_G484548):-makeShare(_G484084,_G484610),makeShare(_G484075,_G484620),hnf('Prelude.?'(_G484610,'Prelude.?'(_G484620,'Prelude.&>'('Prelude.&'('Prelude.=:='('a0_175.A',_G484610),'Prelude.=:='(_G484620,_G484610)),_G484610))),_G484542,_G484545,_G484548).

:-costCenters(['']).




%%%%% Number of shared variables: 2
