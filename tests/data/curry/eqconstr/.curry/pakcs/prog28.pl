%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog28).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog28.fwd',fwd,1,'prog28.fwd',nofix,'FuncType'(_G476343,_G476343)).
functiontype('prog28.f',f,0,'prog28.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog28.main',main,0,'prog28.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog28.fwd'(_G495008,_G495009,_G495010,_G495011):-freeze(_G495010,'blocked_prog28.fwd'(_G495008,_G495009,_G495010,_G495011)).
'blocked_prog28.fwd'(_G495046,_G495053,_G495056,_G495059):-hnf(_G495046,_G495053,_G495056,_G495059).

'prog28.f'(_G495385,_G495386,_G495387):-freeze(_G495386,'blocked_prog28.f'(_G495385,_G495386,_G495387)).
'blocked_prog28.f'('Prelude.True',_G495426,_G495426).

'prog28.main'(_G495800,_G495801,_G495802):-freeze(_G495801,'blocked_prog28.main'(_G495800,_G495801,_G495802)).
'blocked_prog28.main'(_G495958,_G495961,_G495964):-hnf('Prelude.=:='('prog28.fwd'('prog28.f'),'Prelude.False'),_G495958,_G495961,_G495964).

:-costCenters(['']).




%%%%% Number of shared variables: 0
