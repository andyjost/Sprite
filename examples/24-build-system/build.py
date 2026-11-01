# build.py: builds demo in project/ from the rules of Build.curry, or says
# what a changed file rebuilds.
#   python build.py            build demo
#   python build.py shape.h    the targets a change to shape.h rebuilds
import os, subprocess, sys
import curry
here = os.path.dirname(os.path.abspath(__file__))
curry.path.insert(0, here)         # Curry's sys.path, which lacks the cwd
from curry.lib import Build        # Build.curry, the rules
os.chdir(os.path.join(here, 'project'))   # the C files; commands run here

def stale(target, inputs):
    return not os.path.exists(target) or any(
        os.path.getmtime(f) > os.path.getmtime(target) for f in inputs)

def build(target):
    # needs has one value for a target and none for a source: the loop is an if
    for inputs in curry.eval(Build.needs(target)):
        for f in inputs:
            build(f)
        if stale(target, inputs):
            command = curry.eval(Build.command(target)).one()
            print(*command, flush=True)
            subprocess.run(command, check=True)

if len(sys.argv) == 1:
    build('demo')
else:
    changed = sys.argv[1]
    if not os.path.exists(changed):
        sys.exit(f'{changed}: no such file')
    # the same rules, asked backwards; two paths reach demo, and set keeps one
    targets = sorted(set(curry.eval(Build.touches(changed))))
    print(f'touch {changed}: rebuild', *(targets or ['nothing']))
