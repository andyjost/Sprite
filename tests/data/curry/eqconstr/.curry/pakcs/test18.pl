%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test18).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test18.main',main,0,'test18.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test18.main'(_G474639,_G474640,_G474641):-freeze(_G474640,'blocked_test18.main'(_G474639,_G474640,_G474641)).
'blocked_test18.main'(_G474770,_G474773,_G474776):-hnf('Prelude.=:='(_G474675,_G474684),_G474770,_G474773,_G474776).

:-costCenters(['']).




%%%%% Number of shared variables: 0
