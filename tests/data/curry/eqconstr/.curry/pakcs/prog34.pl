%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog34).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog34.fwd',fwd,1,'prog34.fwd',nofix,'FuncType'(_G478731,_G478731)).
functiontype('prog34.f',f,0,'prog34.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog34.main',main,0,'prog34.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog34.fwd'(_G497396,_G497397,_G497398,_G497399):-freeze(_G497398,'blocked_prog34.fwd'(_G497396,_G497397,_G497398,_G497399)).
'blocked_prog34.fwd'(_G497434,_G497441,_G497444,_G497447):-hnf(_G497434,_G497441,_G497444,_G497447).

'prog34.f'(_G497773,_G497774,_G497775):-freeze(_G497774,'blocked_prog34.f'(_G497773,_G497774,_G497775)).
'blocked_prog34.f'(_G497891,_G497894,_G497897):-hnf('Prelude.?'('Prelude.True','Prelude.False'),_G497891,_G497894,_G497897).

'prog34.main'(_G498457,_G498458,_G498459):-freeze(_G498458,'blocked_prog34.main'(_G498457,_G498458,_G498459)).
'blocked_prog34.main'(_G498615,_G498618,_G498621):-hnf('Prelude.=:='('Prelude.False','prog34.fwd'('prog34.f')),_G498615,_G498618,_G498621).

:-costCenters(['']).




%%%%% Number of shared variables: 0
