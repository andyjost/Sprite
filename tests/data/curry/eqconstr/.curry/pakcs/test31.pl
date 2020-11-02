%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test31).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test31.fwd',fwd,1,'test31.fwd',nofix,'FuncType'(_G478683,_G478683)).
functiontype('test31.f',f,0,'test31.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test31.main',main,0,'test31.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test31.fwd'(_G497348,_G497349,_G497350,_G497351):-freeze(_G497350,'blocked_test31.fwd'(_G497348,_G497349,_G497350,_G497351)).
'blocked_test31.fwd'(_G497386,_G497393,_G497396,_G497399):-hnf(_G497386,_G497393,_G497396,_G497399).

'test31.f'(_G497725,_G497726,_G497727):-freeze(_G497726,'blocked_test31.f'(_G497725,_G497726,_G497727)).
'blocked_test31.f'(_G497843,_G497846,_G497849):-hnf('Prelude.?'('Prelude.True','Prelude.False'),_G497843,_G497846,_G497849).

'test31.main'(_G498409,_G498410,_G498411):-freeze(_G498410,'blocked_test31.main'(_G498409,_G498410,_G498411)).
'blocked_test31.main'(_G498567,_G498570,_G498573):-hnf('Prelude.=:='('test31.fwd'('test31.f'),'Prelude.True'),_G498567,_G498570,_G498573).

:-costCenters(['']).




%%%%% Number of shared variables: 0
