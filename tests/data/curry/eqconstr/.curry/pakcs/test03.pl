%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test03).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test03.main',main,0,'test03.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test03.main'(_G481341,_G481342,_G481343):-freeze(_G481342,'blocked_test03.main'(_G481341,_G481342,_G481343)).
'blocked_test03.main'(_G481751,_G481754,_G481757):-hnf('Prelude.=:='([0,0],[0,1]),_G481751,_G481754,_G481757).

:-costCenters(['']).




%%%%% Number of shared variables: 0
