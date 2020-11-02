%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog27).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog27.fwd',fwd,1,'prog27.fwd',nofix,'FuncType'(_G476287,_G476287)).
functiontype('prog27.f',f,0,'prog27.f',nofix,'TCons'('Prelude.Bool',[])).
functiontype('prog27.main',main,0,'prog27.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog27.fwd'(_G494952,_G494953,_G494954,_G494955):-freeze(_G494954,'blocked_prog27.fwd'(_G494952,_G494953,_G494954,_G494955)).
'blocked_prog27.fwd'(_G494990,_G494997,_G495000,_G495003):-hnf(_G494990,_G494997,_G495000,_G495003).

'prog27.f'(_G495329,_G495330,_G495331):-freeze(_G495330,'blocked_prog27.f'(_G495329,_G495330,_G495331)).
'blocked_prog27.f'('Prelude.True',_G495370,_G495370).

'prog27.main'(_G495744,_G495745,_G495746):-freeze(_G495745,'blocked_prog27.main'(_G495744,_G495745,_G495746)).
'blocked_prog27.main'(_G495902,_G495905,_G495908):-hnf('Prelude.=:='('prog27.fwd'('prog27.f'),'Prelude.True'),_G495902,_G495905,_G495908).

:-costCenters(['']).




%%%%% Number of shared variables: 0
