%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_093).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_093.main',main,0,'a0_093.main',nofix,'TCons'('a0_093.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_093.A','A',0,'A',0,'TCons'('a0_093.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_093.main'(_G482822,_G482823,_G482824):-freeze(_G482823,'blocked_a0_093.main'(_G482822,_G482823,_G482824)).
'blocked_a0_093.main'(_G483252,_G483255,_G483258):-makeShare(_G482858,_G483320),makeShare(_G482867,_G483330),hnf('Prelude.?'(_G483320,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G483330,'a0_093.A'),'Prelude.=:='(_G483320,_G483330)),_G483330)),_G483252,_G483255,_G483258).

:-costCenters(['']).




%%%%% Number of shared variables: 2
