%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog26).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog26.fwd',fwd,1,'prog26.fwd',nofix,'FuncType'(_G472861,_G472861)).
functiontype('prog26.main',main,0,'prog26.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog26.fwd'(_G486064,_G486065,_G486066,_G486067):-freeze(_G486066,'blocked_prog26.fwd'(_G486064,_G486065,_G486066,_G486067)).
'blocked_prog26.fwd'(_G486102,_G486109,_G486112,_G486115):-hnf(_G486102,_G486109,_G486112,_G486115).

'prog26.main'(_G486495,_G486496,_G486497):-freeze(_G486496,'blocked_prog26.main'(_G486495,_G486496,_G486497)).
'blocked_prog26.main'(_G486653,_G486656,_G486659):-hnf('Prelude.=:='('Prelude.False','prog26.fwd'('Prelude.True')),_G486653,_G486656,_G486659).

:-costCenters(['']).




%%%%% Number of shared variables: 0
