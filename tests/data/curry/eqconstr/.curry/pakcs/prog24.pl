%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog24).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog24.fwd',fwd,1,'prog24.fwd',nofix,'FuncType'(_G472861,_G472861)).
functiontype('prog24.main',main,0,'prog24.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog24.fwd'(_G486064,_G486065,_G486066,_G486067):-freeze(_G486066,'blocked_prog24.fwd'(_G486064,_G486065,_G486066,_G486067)).
'blocked_prog24.fwd'(_G486102,_G486109,_G486112,_G486115):-hnf(_G486102,_G486109,_G486112,_G486115).

'prog24.main'(_G486495,_G486496,_G486497):-freeze(_G486496,'blocked_prog24.main'(_G486495,_G486496,_G486497)).
'blocked_prog24.main'(_G486653,_G486656,_G486659):-hnf('Prelude.=:='('prog24.fwd'('Prelude.True'),'Prelude.False'),_G486653,_G486656,_G486659).

:-costCenters(['']).




%%%%% Number of shared variables: 0
