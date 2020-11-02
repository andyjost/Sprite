%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test01).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test01.main',main,0,'test01.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test01.main'(_G474613,_G474614,_G474615):-freeze(_G474614,'blocked_test01.main'(_G474613,_G474614,_G474615)).
'blocked_test01.main'(_G474717,_G474720,_G474723):-hnf('Prelude.=:='(0,1),_G474717,_G474720,_G474723).

:-costCenters(['']).




%%%%% Number of shared variables: 0
