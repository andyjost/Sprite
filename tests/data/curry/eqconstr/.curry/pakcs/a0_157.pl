%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_157).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_157.main',main,0,'a0_157.main',nofix,'TCons'('a0_157.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_157.A','A',0,'A',0,'TCons'('a0_157.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_157.main'(_G484039,_G484040,_G484041):-freeze(_G484040,'blocked_a0_157.main'(_G484039,_G484040,_G484041)).
'blocked_a0_157.main'(_G484542,_G484545,_G484548):-makeShare(_G484075,_G484622),makeShare(_G484084,_G484632),hnf('Prelude.?'(_G484622,'Prelude.?'(_G484632,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G484632,'a0_157.A'),'Prelude.=:='(_G484622,_G484632)),_G484632))),_G484542,_G484545,_G484548).

:-costCenters(['']).




%%%%% Number of shared variables: 2
