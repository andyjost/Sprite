%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_017).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_017.main',main,0,'a0_017.main',nofix,'TCons'('a0_017.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_017.A','A',0,'A',0,'TCons'('a0_017.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_017.main'(_G481626,_G481627,_G481628):-freeze(_G481627,'blocked_a0_017.main'(_G481626,_G481627,_G481628)).
'blocked_a0_017.main'(_G481983,_G481986,_G481989):-makeShare(_G481671,_G482033),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482033,'a0_017.A'),'Prelude.=:='(_G482033,_G481662)),_G482033),_G481983,_G481986,_G481989).

:-costCenters(['']).




%%%%% Number of shared variables: 1
