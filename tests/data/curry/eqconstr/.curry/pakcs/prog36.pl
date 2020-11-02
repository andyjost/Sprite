%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog36).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog36.fwd',fwd,1,'prog36.fwd',nofix,'FuncType'(_G471115,_G471115)).
functiontype('prog36.main',main,0,'prog36.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog36.fwd'(_G484318,_G484319,_G484320,_G484321):-freeze(_G484320,'blocked_prog36.fwd'(_G484318,_G484319,_G484320,_G484321)).
'blocked_prog36.fwd'(_G484356,_G484363,_G484366,_G484369):-hnf(_G484356,_G484363,_G484366,_G484369).

'prog36.main'(_G484749,_G484750,_G484751):-freeze(_G484750,'blocked_prog36.main'(_G484749,_G484750,_G484751)).
'blocked_prog36.main'(_G484915,_G484918,_G484921):-hnf('Prelude.=:='('prog36.fwd'(_G484785),'Prelude.False'),_G484915,_G484918,_G484921).

:-costCenters(['']).




%%%%% Number of shared variables: 0
