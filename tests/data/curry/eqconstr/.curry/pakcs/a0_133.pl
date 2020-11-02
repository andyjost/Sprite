%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_133).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_133.main',main,0,'a0_133.main',nofix,'TCons'('a0_133.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_133.A','A',0,'A',0,'TCons'('a0_133.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_133.main'(_G484033,_G484034,_G484035):-freeze(_G484034,'blocked_a0_133.main'(_G484033,_G484034,_G484035)).
'blocked_a0_133.main'(_G484536,_G484539,_G484542):-makeShare(_G484078,_G484604),makeShare(_G484069,_G484614),hnf('Prelude.?'(_G484604,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G484614,_G484604),'Prelude.=:='(_G484604,'a0_133.A')),_G484604),_G484614)),_G484536,_G484539,_G484542).

:-costCenters(['']).




%%%%% Number of shared variables: 2
