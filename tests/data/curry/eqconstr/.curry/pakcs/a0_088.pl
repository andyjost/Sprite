%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_088).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_088.main',main,0,'a0_088.main',nofix,'TCons'('a0_088.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_088.A','A',0,'A',0,'TCons'('a0_088.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_088.main'(_G482822,_G482823,_G482824):-freeze(_G482823,'blocked_a0_088.main'(_G482822,_G482823,_G482824)).
'blocked_a0_088.main'(_G483252,_G483255,_G483258):-makeShare(_G482858,_G483314),makeShare(_G482867,_G483324),hnf('Prelude.?'(_G483314,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G483324,_G483314),'Prelude.=:='(_G483324,'a0_088.A')),_G483314)),_G483252,_G483255,_G483258).

:-costCenters(['']).




%%%%% Number of shared variables: 2