%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_012).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_012.main',main,0,'a0_012.main',nofix,'TCons'('a0_012.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_012.A','A',0,'A',0,'TCons'('a0_012.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_012.main'(_G481626,_G481627,_G481628):-freeze(_G481627,'blocked_a0_012.main'(_G481626,_G481627,_G481628)).
'blocked_a0_012.main'(_G481983,_G481986,_G481989):-makeShare(_G481671,_G482039),makeShare(_G481662,_G482049),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482039,'a0_012.A'),'Prelude.=:='(_G482049,_G482039)),_G482049),_G481983,_G481986,_G481989).

:-costCenters(['']).




%%%%% Number of shared variables: 2
