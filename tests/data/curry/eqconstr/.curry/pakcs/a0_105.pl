%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_105).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_105.main',main,0,'a0_105.main',nofix,'TCons'('a0_105.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_105.A','A',0,'A',0,'TCons'('a0_105.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_105.main'(_G482822,_G482823,_G482824):-freeze(_G482823,'blocked_a0_105.main'(_G482822,_G482823,_G482824)).
'blocked_a0_105.main'(_G483252,_G483255,_G483258):-makeShare(_G482867,_G483308),hnf('Prelude.?'(_G483308,'Prelude.&>'('Prelude.&'('Prelude.=:='(_G483308,_G482858),'Prelude.=:='(_G483308,'a0_105.A')),_G483308)),_G483252,_G483255,_G483258).

:-costCenters(['']).




%%%%% Number of shared variables: 1
