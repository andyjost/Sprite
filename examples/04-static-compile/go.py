'''
Compiles a Curry module to a Python script.

Imports wildcard_matching.curry and writes the compiled module to
wildcard_matching.py with curry.save.  The goal main is recorded in the
script, so running the script evaluates main.
'''
import os
import curry

# Find wildcard_matching.curry next to this file, whatever the working
# directory is.
HERE = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, HERE)

print('Loading and compiling wildcard_matching.curry')
wildcard_matching = curry.import_('wildcard_matching')

print('Saving the program to wildcard_matching.py with goal main')
curry.save(wildcard_matching, os.path.join(HERE, 'wildcard_matching.py'), goal='main')
