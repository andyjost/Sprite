%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_019).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_019.main',main,0,'a0_019.main',nofix,'TCons'('a0_019.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_019.A','A',0,'A',0,'TCons'('a0_019.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_019.main'(_G481626,_G481627,_G481628):-freeze(_G481627,'blocked_a0_019.main'(_G481626,_G481627,_G481628)).
'blocked_a0_019.main'(_G481983,_G481986,_G481989):-makeShare(_G481671,_G482033),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('a0_019.A',_G482033),'Prelude.=:='(_G482033,_G481662)),_G482033),_G481983,_G481986,_G481989).

:-costCenters(['']).




%%%%% Number of shared variables: 1
