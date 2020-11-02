%PAKCS2.1 swi7 VARIABLESHARING

:-noSingletonWarnings.
:-noRedefineWarnings.
:-noDiscontiguousWarnings.

:-importModule('Prelude').

:-curryModule(prog11).


%%%%%%%%%%%% function types %%%%%%%%%%%%%%%%%%%
:-multifile functiontype/6.
:-dynamic functiontype/6.
functiontype('prog11.main',main,0,'prog11.main',nofix,'TCons'('Prelude.Bool',[])).

%%%%%%%%%%%% constructor types %%%%%%%%%%%%%%%%%%%
:-multifile constructortype/7.
:-dynamic constructortype/7.

%%%%%%%%%%%% function definitions %%%%%%%%%%%%%%%%%%%
'prog11.main'(_G477188,_G477189,_G477190):-freeze(_G477189,'blocked_prog11.main'(_G477188,_G477189,_G477190)).
'blocked_prog11.main'(_G477438,_G477441,_G477444):-hnf('Prelude.=:='('Prelude.?'(0,1),'Prelude.?'(0,1)),_G477438,_G477441,_G477444).

:-costCenters(['']).




%%%%% Number of shared variables: 0
