%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_119).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_119.main',main,0,'a0_119.main',nofix,'TCons'('a0_119.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_119.A','A',0,'A',0,'TCons'('a0_119.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_119.main'(_G484033,_G484034,_G484035):-freeze(_G484034,'blocked_a0_119.main'(_G484033,_G484034,_G484035)).
'blocked_a0_119.main'(_G484536,_G484539,_G484542):-makeShare(_G484069,_G484616),makeShare(_G484078,_G484626),hnf('Prelude.?'(_G484616,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G484616,_G484626),'Prelude.=:='('a0_119.A',_G484626)),_G484626),_G484626)),_G484536,_G484539,_G484542).

:-costCenters(['']).




%%%%% Number of shared variables: 2