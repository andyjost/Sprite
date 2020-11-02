%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test00).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test00.main',main,0,'test00.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test00.main'(_G474613,_G474614,_G474615):-freeze(_G474614,'blocked_test00.main'(_G474613,_G474614,_G474615)).
'blocked_test00.main'(_G474717,_G474720,_G474723):-hnf('Prelude.=:='(0,0),_G474717,_G474720,_G474723).

:-costCenters(['']).




%%%%% Number of shared variables: 0
