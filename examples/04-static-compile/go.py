from __future__ import print_function
import curry

curry.path.insert(0, '.')

print('Loading and compiling wildcard_matching.curry')
wildcard_matching = curry.import_('wildcard_matching')

print('Saving program to wildcard_matching.py')
curry.save(wildcard_matching, 'wildcard_matching.py')


