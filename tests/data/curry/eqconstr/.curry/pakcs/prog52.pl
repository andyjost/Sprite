%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog52).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog52.main',main,0,'prog52.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog52.main'(_G484345,_G484346,_G484347):-freeze(_G484346,'blocked_prog52.main'(_G484345,_G484346,_G484347)).
'blocked_prog52.main'(_G484928,_G484931,_G484934):-makeShare(_G484381,_G484996),makeShare(_G484390,_G485006),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G484996,'Prelude.True'),'Prelude.&'('Prelude.=:='(_G485006,_G484996),'Prelude.=:='(_G485006,'Prelude.False'))),_G484996),_G484996),_G484928,_G484931,_G484934).

:-costCenters(['']).




%%%%% Number of shared variables: 2
