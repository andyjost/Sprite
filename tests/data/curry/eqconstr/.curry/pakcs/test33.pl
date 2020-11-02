%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test33).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test33.fwd',fwd,1,'test33.fwd',nofix,'FuncType'(_G478683,_G478683)).
functiontype('test33.f',f,0,'test33.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test33.main',main,0,'test33.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test33.fwd'(_G497348,_G497349,_G497350,_G497351):-freeze(_G497350,'blocked_test33.fwd'(_G497348,_G497349,_G497350,_G497351)).
'blocked_test33.fwd'(_G497386,_G497393,_G497396,_G497399):-hnf(_G497386,_G497393,_G497396,_G497399).

'test33.f'(_G497725,_G497726,_G497727):-freeze(_G497726,'blocked_test33.f'(_G497725,_G497726,_G497727)).
'blocked_test33.f'(_G497843,_G497846,_G497849):-hnf('Prelude.?'('Prelude.True','Prelude.False'),_G497843,_G497846,_G497849).

'test33.main'(_G498409,_G498410,_G498411):-freeze(_G498410,'blocked_test33.main'(_G498409,_G498410,_G498411)).
'blocked_test33.main'(_G498567,_G498570,_G498573):-hnf('Prelude.=:='('Prelude.True','test33.fwd'('test33.f')),_G498567,_G498570,_G498573).

:-costCenters(['']).




%%%%% Number of shared variables: 0
