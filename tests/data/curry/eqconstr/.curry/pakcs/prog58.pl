%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog58).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog58.main',main,0,'prog58.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog58.main'(_G483125,_G483126,_G483127):-freeze(_G483126,'blocked_prog58.main'(_G483125,_G483126,_G483127)).
'blocked_prog58.main'(_G483635,_G483638,_G483641):-makeShare(_G483161,_G483697),makeShare(_G483170,_G483707),hnf('Prelude.&>'('Prelude.&'('Prelude.=:='('Prelude.True',_G483697),'Prelude.&'('Prelude.=:='(_G483707,'Prelude.False'),'Prelude.=:='(_G483707,_G483697))),_G483697),_G483635,_G483638,_G483641).

:-costCenters(['']).




%%%%% Number of shared variables: 2