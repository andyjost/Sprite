%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_009).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_009.main',main,0,'a0_009.main',nofix,'TCons'('a0_009.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_009.A','A',0,'A',0,'TCons'('a0_009.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_009.main'(_G481641,_G481642,_G481643):-freeze(_G481642,'blocked_a0_009.main'(_G481641,_G481642,_G481643)).
'blocked_a0_009.main'(_G481998,_G482001,_G482004):-makeShare(_G481686,_G482048),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482048,_G481677),'Prelude.=:='(_G482048,'a0_009.A')),_G482048),_G481998,_G482001,_G482004).

:-costCenters(['']).




%%%%% Number of shared variables: 1
