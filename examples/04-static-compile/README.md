# Session

The script evaluates Hello from lesson 01 and waits for its background
compilation with curry.wait(Hello).  It then compiles a small text module,
holds answer, reloads with new text, catches StaleError from the held term,
and evaluates the rebuilt answer.  reload updates the module in place.

save(M, path) writes a module object; reset starts a fresh session, retains
the search path and leaves Prelude registered; load registers the saved
module.  Loading the same file again returns the registered module.
save(M, path, main=M.answer) writes an executable program that loads its
embedded object and prints that goal's answers.  The script runs it in a
child process.  Both forms belong to the backend that saved them.  All
products live in a temporary directory and are removed on exit.

On Windows, saving with a main goal builds a clang-cl executable linked
against the runtime import library. It embeds the module and uses Python on
PATH to run the shared goal/defaulting protocol. The runtime DLL is copied
beside the executable; keep that DLL with the program. A matching Sprite
installation and Python remain required. On Windows a parent process owns
the lesson's temporary directory and removes it after the evaluating child
exits, when the saved module is no longer mapped.

Text modules can be reloaded with text=.  For a file module, omit text to
read its source again; C++ with interpret off requires a fresh
process, or reset(interpret='new') before importing it.  This lesson uses a
text module for reload so it works under the normal interpret:new setting.

Run "make stage" at the repository root, then "./run" here.  expected.out
records the output, including the stale-term message and the saved
program's 42.  The matching detour has been removed; see
13-regex-nondeterminism for matching and the guide's session-control
section for session rules.
