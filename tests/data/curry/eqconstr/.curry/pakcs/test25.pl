%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test25).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test25.fwd',fwd,1,'test25.fwd',nofix,'FuncType'(_G472846,_G472846)).
functiontype('test25.main',main,0,'test25.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test25.fwd'(_G486049,_G486050,_G486051,_G486052):-freeze(_G486051,'blocked_test25.fwd'(_G486049,_G486050,_G486051,_G486052)).
'blocked_test25.fwd'(_G486087,_G486094,_G486097,_G486100):-hnf(_G486087,_G486094,_G486097,_G486100).

'test25.main'(_G486480,_G486481,_G486482):-freeze(_G486481,'blocked_test25.main'(_G486480,_G486481,_G486482)).
'blocked_test25.main'(_G486638,_G486641,_G486644):-hnf('Prelude.=:='('Prelude.True','test25.fwd'('Prelude.True')),_G486638,_G486641,_G486644).

:-costCenters(['']).




%%%%% Number of shared variables: 0
