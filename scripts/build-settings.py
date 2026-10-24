#!/usr/bin/env python3
"""Print reusable CMake settings for a new worktree, one argument per line.

Do not copy CMakeCache.txt: it contains the source and build directories.
"""
import sys
from pathlib import Path

KEYS = {
    'Python_EXECUTABLE', 'CMAKE_C_COMPILER', 'CMAKE_CXX_COMPILER'
  , 'CMAKE_BUILD_TYPE', 'WITH_CXX_POSTINSTALL', 'WITH_PAKCS'
  , 'WITH_CURRY_FRONTEND', 'WITH_ICURRY', 'WITH_CCACHE'
  , 'CURRY2ICURRY_TOOL', 'GC', 'TRACE', 'COUNTERS'
  , 'GC_WRITE_COUNTERS', 'JOBS', 'ENABLE_ICURRY_CACHE', 'ENABLE_PARSED_JSON_CACHE'
  }

jobs_only = sys.argv[1] == '--jobs'
cache = Path(sys.argv[2] if jobs_only else sys.argv[1])
settings = {}
for line in (cache.read_text().splitlines() if cache.is_file() or not jobs_only else []):
  if ':' in line and '=' in line and not line.startswith(('#', '//')):
    key, rest = line.split(':', 1)
    settings[key] = rest.split('=', 1)[1]
if jobs_only:
  print(settings.get('JOBS', 'auto'))
  sys.exit(0)
for key, value in settings.items():
  if key not in KEYS:
    continue
  if value == 'AUTO' and key in ('WITH_PAKCS', 'WITH_CURRY_FRONTEND'):
    found = settings.get('SPRITE_PAKCS' if key == 'WITH_PAKCS' else 'SPRITE_FRONTEND', '')
    value = str(Path(found).resolve()) if found and not found.endswith('-NOTFOUND') else ''
  print('-D%s=%s' % (key, value))
