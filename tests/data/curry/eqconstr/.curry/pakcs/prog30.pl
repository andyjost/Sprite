%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog30).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog30.fwd',fwd,1,'prog30.fwd',nofix,'FuncType'(_G476343,_G476343)).
functiontype('prog30.f',f,0,'prog30.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog30.main',main,0,'prog30.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog30.fwd'(_G495008,_G495009,_G495010,_G495011):-freeze(_G495010,'blocked_prog30.fwd'(_G495008,_G495009,_G495010,_G495011)).
'blocked_prog30.fwd'(_G495046,_G495053,_G495056,_G495059):-hnf(_G495046,_G495053,_G495056,_G495059).

'prog30.f'(_G495385,_G495386,_G495387):-freeze(_G495386,'blocked_prog30.f'(_G495385,_G495386,_G495387)).
'blocked_prog30.f'('Prelude.True',_G495426,_G495426).

'prog30.main'(_G495800,_G495801,_G495802):-freeze(_G495801,'blocked_prog30.main'(_G495800,_G495801,_G495802)).
'blocked_prog30.main'(_G495958,_G495961,_G495964):-hnf('Prelude.=:='('Prelude.False','prog30.fwd'('prog30.f')),_G495958,_G495961,_G495964).

:-costCenters(['']).




%%%%% Number of shared variables: 0
