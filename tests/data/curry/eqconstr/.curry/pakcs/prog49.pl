%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog49).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog49.main',main,0,'prog49.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog49.main'(_G481672,_G481673,_G481674):-freeze(_G481673,'blocked_prog49.main'(_G481672,_G481673,_G481674)).
'blocked_prog49.main'(_G482097,_G482100,_G482103):-makeShare(_G481708,_G482141),hnf('Prelude.?'('Prelude.&>'('Prelude.&'('Prelude.=:='(_G482141,'Prelude.True'),'Prelude.=:='(_G482141,'Prelude.True')),_G482141),_G482141),_G482097,_G482100,_G482103).

:-costCenters(['']).




%%%%% Number of shared variables: 1
