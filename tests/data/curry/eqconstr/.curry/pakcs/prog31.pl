%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog31).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog31.fwd',fwd,1,'prog31.fwd',nofix,'FuncType'(_G478681,_G478681)).
functiontype('prog31.f',f,0,'prog31.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog31.main',main,0,'prog31.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog31.fwd'(_G497346,_G497347,_G497348,_G497349):-freeze(_G497348,'blocked_prog31.fwd'(_G497346,_G497347,_G497348,_G497349)).
'blocked_prog31.fwd'(_G497384,_G497391,_G497394,_G497397):-hnf(_G497384,_G497391,_G497394,_G497397).

'prog31.f'(_G497723,_G497724,_G497725):-freeze(_G497724,'blocked_prog31.f'(_G497723,_G497724,_G497725)).
'blocked_prog31.f'(_G497841,_G497844,_G497847):-hnf('Prelude.?'('Prelude.True','Prelude.False'),_G497841,_G497844,_G497847).

'prog31.main'(_G498407,_G498408,_G498409):-freeze(_G498408,'blocked_prog31.main'(_G498407,_G498408,_G498409)).
'blocked_prog31.main'(_G498565,_G498568,_G498571):-hnf('Prelude.=:='('prog31.fwd'('prog31.f'),'Prelude.True'),_G498565,_G498568,_G498571).

:-costCenters(['']).




%%%%% Number of shared variables: 0
