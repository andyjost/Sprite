%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog23).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog23.fwd',fwd,1,'prog23.fwd',nofix,'FuncType'(_G472844,_G472844)).
functiontype('prog23.main',main,0,'prog23.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog23.fwd'(_G486047,_G486048,_G486049,_G486050):-freeze(_G486049,'blocked_prog23.fwd'(_G486047,_G486048,_G486049,_G486050)).
'blocked_prog23.fwd'(_G486085,_G486092,_G486095,_G486098):-hnf(_G486085,_G486092,_G486095,_G486098).

'prog23.main'(_G486478,_G486479,_G486480):-freeze(_G486479,'blocked_prog23.main'(_G486478,_G486479,_G486480)).
'blocked_prog23.main'(_G486636,_G486639,_G486642):-hnf('Prelude.=:='('prog23.fwd'('Prelude.True'),'Prelude.True'),_G486636,_G486639,_G486642).

:-costCenters(['']).




%%%%% Number of shared variables: 0
