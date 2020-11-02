%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog55).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog55.main',main,0,'prog55.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog55.main'(_G483125,_G483126,_G483127):-freeze(_G483126,'blocked_prog55.main'(_G483125,_G483126,_G483127)).
'blocked_prog55.main'(_G483635,_G483638,_G483641):-makeShare(_G483161,_G483697),makeShare(_G483170,_G483707),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='(_G483697,'Prelude.True'),'Prelude.&'('Prelude.=:='('Prelude.False',_G483707),'Prelude.=:='(_G483697,_G483707))),_G483697),_G483635,_G483638,_G483641).

:-costCenters(['']).




%%%%% Number of shared variables: 2
