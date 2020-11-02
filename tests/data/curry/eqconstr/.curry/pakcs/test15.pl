%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test15).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test15.main',main,0,'test15.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test15.main'(_G475753,_G475754,_G475755):-freeze(_G475754,'blocked_test15.main'(_G475753,_G475754,_G475755)).
'blocked_test15.main'(_G475879,_G475882,_G475885):-hnf('Prelude.=:='('Prelude.True',_G475789),_G475879,_G475882,_G475885).

:-costCenters(['']).




%%%%% Number of shared variables: 0
