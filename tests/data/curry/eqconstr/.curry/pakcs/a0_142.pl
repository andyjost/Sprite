%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(a0_142).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('a0_142.main',main,0,'a0_142.main',nofix,'TCons'('a0_142.T',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.
constructortype('a0_142.A','A',0,'A',0,'TCons'('a0_142.T',[]),[]).

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'a0_142.main'(_G484033,_G484034,_G484035):-freeze(_G484034,'blocked_a0_142.main'(_G484033,_G484034,_G484035)).
'blocked_a0_142.main'(_G484536,_G484539,_G484542):-makeShare(_G484078,_G484610),makeShare(_G484069,_G484620),hnf('Prelude.?'(_G484610,'Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='('a0_142.A',_G484610),'Prelude.=:='(_G484620,_G484610)),_G484620),_G484620)),_G484536,_G484539,_G484542).

:-costCenters(['']).




%%%%% Number of shared variables: 2
