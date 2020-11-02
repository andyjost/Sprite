%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test10).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test10.main',main,0,'test10.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test10.main'(_G475914,_G475915,_G475916):-freeze(_G475915,'blocked_test10.main'(_G475914,_G475915,_G475916)).
'blocked_test10.main'(_G476091,_G476094,_G476097):-hnf('Prelude.=:='('Prelude.?'(0,1),1),_G476091,_G476094,_G476097).

:-costCenters(['']).




%%%%% Number of shared variables: 0
