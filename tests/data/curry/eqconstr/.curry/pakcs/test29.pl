%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(test29).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('test29.fwd',fwd,1,'test29.fwd',nofix,'FuncType'(_G476289,_G476289)).
functiontype('test29.f',f,0,'test29.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('test29.main',main,0,'test29.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'test29.fwd'(_G494954,_G494955,_G494956,_G494957):-freeze(_G494956,'blocked_test29.fwd'(_G494954,_G494955,_G494956,_G494957)).
'blocked_test29.fwd'(_G494992,_G494999,_G495002,_G495005):-hnf(_G494992,_G494999,_G495002,_G495005).

'test29.f'(_G495331,_G495332,_G495333):-freeze(_G495332,'blocked_test29.f'(_G495331,_G495332,_G495333)).
'blocked_test29.f'('Prelude.True',_G495372,_G495372).

'test29.main'(_G495746,_G495747,_G495748):-freeze(_G495747,'blocked_test29.main'(_G495746,_G495747,_G495748)).
'blocked_test29.main'(_G495904,_G495907,_G495910):-hnf('Prelude.=:='('Prelude.True','test29.fwd'('test29.f')),_G495904,_G495907,_G495910).

:-costCenters(['']).




%%%%% Number of shared variables: 0
