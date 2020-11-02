%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_006).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_006.main',main,0,'a0_006.main',nofix,'TCons'('a0_006.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_006.A','A',0,'A',0,'TCons'('a0_006.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_006.main'(_G481635,_G481636,_G481637):-freeze(_G481636,'blocked_a0_006.main'(_G481635,_G481636,_G481637)).
'blocked_a0_006.main'(_G481992,_G481995,_G481998):-makeShare(_G481671,_G482048),makeShare(_G481680,_G482058),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482048,_G482058),'Prelude.=:='('a0_006.A',_G482058)),_G482048),_G481992,_G481995,_G481998).

:-costCenters(['']).




%%%%% Number of shared variables: 2
