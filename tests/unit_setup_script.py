'''
Tests scripts/setup-dev-machine.sh, the setup script of a development
machine, without a network and without an installation.

The tests run the script with --dry-run against a temporary prefix and check
the printed plan: the pinned PAKCS archive and its checksum, the conda
environment, the configure flags, make stage, the smoke test on both
backends, and the next steps.  A dry run must write nothing.  One test runs
the script for real with a dpkg-query that reports every package as missing:
the script must print the apt command, stop with status 1, and write
nothing.  The tools the plan depends on (dpkg-query, apt-cache, micromamba,
swipl) are stand-ins on PATH, so the plan is the same on every machine.
'''
import cytest # from ./lib; must be first
import os, re, subprocess, tempfile, unittest

ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
  )
SCRIPT = os.path.join(ROOT, 'scripts', 'setup-dev-machine.sh')
ENV_FILE = os.path.join(ROOT, 'conda', 'dev-environment.yml')
DOC_FILE = os.path.join(ROOT, 'docs', 'source', 'DeveloperSetup.rst')
TIMEOUT = 60  # seconds for one run of the script

PAKCS_URL = 'https://www.curry-lang.org/pakcs/download/pakcs-3.4.1-amd64-Linux.tar.gz'
PAKCS_SHA256 = 'd17d8b3c30564200d5f4ee3a4ee9882fbca5ed66b77b9317050e1f71ba955db2'
CLEAN_ENV = 'env -i PATH=/usr/local/bin:/usr/bin:/bin HOME='
APT_PACKAGES = [
    'git', 'swi-prolog-nox', 'g++', 'make', 'curl', 'ccache', 'time'
  , 'linux-tools-common'
  ]

# The stand-ins.  dpkg-query answers "installed" for every package unless a
# test replaces it; apt-cache knows no package, so perf comes from the
# generic linux-tools package; micromamba and swipl only need to exist.
FAKES = {
    'dpkg-query': 'printf installed\n'
  , 'apt-cache': 'exit 1\n'
  , 'micromamba': 'exit 0\n'
  , 'swipl': 'exit 0\n'
  }


class SetupScriptTestCase(unittest.TestCase):
  '''Runs the script in a temporary directory with stand-in tools.'''

  def setUp(self):
    self.tmp = tempfile.mkdtemp(prefix='setup-script-')
    self.bin = os.path.join(self.tmp, 'bin')
    self.home = os.path.join(self.tmp, 'home')
    os.mkdir(self.bin)
    os.mkdir(self.home)
    for name, body in FAKES.items():
      self.fake(name, body)
    self.prefix = os.path.join(self.tmp, 'prefix')
    self.repo = os.path.join(self.tmp, 'repo')

  def tearDown(self):
    # A dry run writes nothing, so the tree is small.  Remove it by hand so
    # that a test which did write something still cleans up.
    for dirpath, dirnames, filenames in os.walk(self.tmp, topdown=False):
      for name in filenames:
        os.unlink(os.path.join(dirpath, name))
      for name in dirnames:
        path = os.path.join(dirpath, name)
        if os.path.islink(path):
          os.unlink(path)
        else:
          os.rmdir(path)
    os.rmdir(self.tmp)

  def fake(self, name, body):
    '''Writes a stand-in tool into the bin directory of the test.'''
    path = os.path.join(self.bin, name)
    with open(path, 'w') as stream:
      stream.write('#!/bin/sh\n' + body)
    os.chmod(path, 0o755)

  def run_script(self, *args, env=None):
    '''Runs the script with the stand-ins first on PATH and a fresh HOME.'''
    environ = dict(os.environ, LC_ALL='C.UTF-8', HOME=self.home)
    environ['PATH'] = self.bin + os.pathsep + environ.get('PATH', '/usr/bin:/bin')
    environ.pop('PAKCS_VERSION', None)
    environ.pop('ICURRY_VERSION', None)
    environ.pop('SPRITE_SETUP_CLEAN_PATH', None)
    if env:
      environ.update(env)
    return subprocess.run(
        ['bash', SCRIPT] + list(args), capture_output=True, encoding='utf-8'
      , errors='replace', env=environ, timeout=TIMEOUT
      )

  def dry_run(self, *args, **kwds):
    '''A dry run that must succeed and write nothing.'''
    proc = self.run_script('--dry-run', '--prefix', self.prefix, *args, **kwds)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stderr, '')
    self.assertNothingWritten()
    return proc.stdout

  def assertNothingWritten(self):
    '''The temporary directory holds only the stand-ins and the empty HOME.'''
    self.assertEqual(sorted(os.listdir(self.tmp)), ['bin', 'home'])
    self.assertEqual(os.listdir(self.home), [])
    self.assertEqual(sorted(os.listdir(self.bin)), sorted(FAKES))

  def assertInOrder(self, text, *parts):
    '''Each part occurs in the text, after the part before it.'''
    position = 0
    for part in parts:
      found = text.find(part, position)
      self.assertNotEqual(found, -1, 'not found after position %d: %r' % (position, part))
      position = found + len(part)


class TestScriptText(SetupScriptTestCase):
  '''The file itself.'''

  def test_syntax(self):
    proc = subprocess.run(
        ['bash', '-n', SCRIPT], capture_output=True, encoding='utf-8', timeout=TIMEOUT
      )
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertTrue(os.access(SCRIPT, os.X_OK))
    with open(SCRIPT) as stream:
      text = stream.read()
    self.assertTrue(text.startswith('#!/bin/bash\n'))
    self.assertIn('\nset -euo pipefail\n', text)

  def test_help(self):
    proc = self.run_script('--help')
    self.assertEqual(proc.returncode, 0, proc.stderr)
    for option in [
        '--prefix', '--repo', '--repo-url', '--branch', '--jobs', '--dry-run'
      , '--skip-apt', '--icurry', '--smoke-file', '--cap-kb', '--timeout'
      , '--cc', '--cxx', '--reconfigure'
      ]:
      self.assertIn(option, proc.stdout)

  def test_usage_errors(self):
    proc = self.run_script()
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn('--prefix is required', proc.stderr)
    proc = self.run_script('--prefix', self.prefix, '--bogus')
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn('unknown option: --bogus', proc.stderr)
    for option, value in [
        ('--jobs', '0'), ('--jobs', 'many'), ('--cap-kb', '-1'), ('--timeout', 'x')
      ]:
      proc = self.run_script('--prefix', self.prefix, option, value)
      self.assertNotEqual(proc.returncode, 0, option)
      self.assertIn(option, proc.stderr)
    self.assertNothingWritten()

  def test_never_runs_sudo(self):
    '''sudo appears in printed text and comments only.'''
    with open(SCRIPT) as stream:
      for number, line in enumerate(stream, 1):
        if 'sudo' not in line:
          continue
        stripped = line.strip()
        self.assertTrue(
            stripped.startswith('#') or 'printf' in line or 'note ' in line
                or stripped.startswith('installed by the script')
          , 'line %d runs sudo: %r' % (number, line)
          )

  def test_no_machine_specific_text(self):
    '''The committed files name no machine, user, or company.'''
    pattern = re.compile(r'/home/|/scratch/')
    for filename in [SCRIPT, ENV_FILE, DOC_FILE]:
      with open(filename) as stream:
        text = stream.read()
      match = pattern.search(text)
      self.assertIsNone(match, '%s: %r' % (filename, match and match.group(0)))

  def test_environment_file(self):
    '''The conda environment holds only what Sprite needs.'''
    with open(ENV_FILE) as stream:
      lines = [line.rstrip() for line in stream]
    self.assertIn('name: sprite-dev', lines)
    section = None
    sections = {}
    for line in lines:
      if not line or line.lstrip().startswith('#'):
        continue
      if not line.startswith(' '):
        section = line.rstrip(':')
        sections[section] = []
      elif line.startswith('  - '):
        sections[section].append(line[4:].split('#')[0].strip())
    self.assertEqual(sections['channels'][0], 'conda-forge')
    self.assertEqual(
        sorted(sections['dependencies'])
      , ['numpy', 'pip', 'python=3.14.*', 'sphinx', 'sphinx_rtd_theme']
      )


class TestDryRun(SetupScriptTestCase):
  '''The plan of a dry run.'''

  def test_plan(self):
    out = self.dry_run('--repo', self.repo, '--branch', 'py314', '--jobs', '3')
    prefix, repo = self.prefix, self.repo
    python = prefix + '/conda/env/bin/python'
    # The steps, in order.
    self.assertInOrder(
        out, 'Step 1/9: machine', 'Step 2/9: apt', 'Step 3/9: PAKCS 3.4.1'
      , 'Step 4/9: checkout', 'Step 5/9: conda', 'Step 6/9: configure'
      , 'Step 7/9: make stage', 'Step 8/9: smoke test', 'Step 9/9: next steps'
      , 'dry run complete; no stop expected'
      )
    self.assertIn('jobs: 3', out)
    self.assertNotIn('jobs: auto', out)
    # apt: every package is installed, so no apt command is printed.
    self.assertNotIn('sudo', out)
    for package in APT_PACKAGES + ['linux-tools-generic']:
      self.assertIn(' %s' % package, out)
    # PAKCS: the pinned archive, its checksum, the stack limit of SWI-Prolog
    # 9, and make in the clean environment.
    self.assertInOrder(
        out, 'curl -fsSL -o %s/downloads/pakcs-3.4.1-amd64-Linux.tar.gz %s' % (prefix, PAKCS_URL)
      , PAKCS_SHA256, 'sha256sum -c -'
      , 'tar xzf %s/downloads/pakcs-3.4.1-amd64-Linux.tar.gz -C %s' % (prefix, prefix)
      , 'sed -i', 'pakcs-3.4.1/scripts/pakcs-makesavedstate.sh'
      , '(cd %s/pakcs-3.4.1 && %s' % (prefix, CLEAN_ENV), ' make SWIPROLOG='
      )
    self.assertRegex(out, r' make SWIPROLOG=\S+/swipl\)')
    # conda: created from the environment file under the prefix.
    self.assertIn(
        'env CONDA_PKGS_DIRS=%s/conda/pkgs micromamba create -y -p %s/conda/env -f %s/conda/dev-environment.yml'
            % (prefix, prefix, repo)
      , out
      )
    # The checkout: a clone of the branch, the pybind11 submodule only, and
    # the two links into the prefix.
    self.assertInOrder(
        out, 'git clone --branch py314 https://github.com/andyjost/Sprite.git %s' % repo
      , 'git -C %s submodule update --init extern/pybind11' % repo
      , 'mkdir -p %s/install' % prefix, 'ln -s %s/install %s/install' % (prefix, repo)
      , 'mkdir -p %s/object-root' % prefix, 'ln -s %s/object-root %s/object-root' % (prefix, repo)
      )
    # configure in the clean environment, with the flags of the personal
    # rules; no icurry.
    configure = re.search(r'\+ \(cd %s && (.*configure.*)\)' % re.escape(repo), out)
    self.assertIsNotNone(configure)
    line = configure.group(1)
    self.assertTrue(line.startswith(CLEAN_ENV), line)
    self.assertIn(' LC_ALL=C.UTF-8 ', line)
    # The compiler cache lives under the prefix in every build and test.
    self.assertIn(' CCACHE_DIR=%s/ccache ' % prefix, line)
    self.assertIn(' %s ./configure ' % python, line)
    for flag in [
        '--with-python=' + python, '--with-cc=/usr/bin/gcc', '--with-cxx=/usr/bin/g++'
      , '--with-cxx-postinstall=/usr/bin/g++', '--with-pakcs=%s/pakcs-3.4.1/bin/pakcs' % prefix
      , '--with-icurry='
      ]:
      self.assertIn(' ' + flag, line + ' ')
    self.assertNotIn('--with-icurry=/', line)
    # No checkout yet, so configure --help cannot be probed; the options it
    # may gain later are left out.
    self.assertIn('could not be probed', out)
    self.assertNotIn('--jobs=', line)
    self.assertNotIn('--with-ccache', line)
    # make stage in the clean environment, after configure.
    self.assertInOrder(out, './configure', '(cd %s && %s' % (repo, CLEAN_ENV), ' make stage)')
    self.assertRegex(out, r'CCACHE_DIR=%s/ccache make stage\)' % re.escape(prefix))
    self.assertIn('the flags are recorded in %s/configure-args' % prefix, out)
    # The smoke test: one file on each backend, capped and timed.
    for backend in ['py', 'cxx']:
      smoke = re.search(
          r'\+ \(cd %s/tests && ulimit -v 6291456 && (.*SPRITE_INTERPRETER_FLAGS=backend:%s .*)\)'
              % (re.escape(repo), backend)
        , out
        )
      self.assertIsNotNone(smoke, backend)
      line = smoke.group(1)
      self.assertIn('CCACHE_DIR=%s/ccache' % prefix, line)
      self.assertIn('SPRITE_HOME=%s/install' % prefix, line)
      self.assertIn('PYTHONPATH=%s/tests/lib' % repo, line)
      self.assertIn('CURRYPATH=%s/tests/data/curry' % repo, line)
      self.assertIn(
          ' timeout 600 %s/install/bin/python -B -m unittest discover %s/tests unit_expr.py'
              % (prefix, repo)
        , line
        )
    self.assertInOrder(out, ' make stage)', 'backend:py', 'backend:cxx', 'next steps')
    # The next steps name the calibration, the baseline, and the rules file.
    self.assertIn('Calibrate the test manifest', out)
    self.assertIn('./run_tests -j 1 --backend both --update-manifest', out)
    self.assertIn('./run_benchmarks -b cxx -b py --label baseline -o %s/baseline.jsonl' % prefix, out)
    self.assertIn('./run_benchmarks counters', out)
    self.assertIn('personal rules file', out)
    self.assertIn('python:      ' + python, out)
    self.assertIn('ccache:      %s/ccache (CCACHE_DIR)' % prefix, out)
    self.assertIn('ccache --set-config cache_dir=%s/ccache' % prefix, out)

  def test_budgets_are_parameters(self):
    out = self.dry_run(
        '--repo', self.repo, '--cap-kb', '1234', '--timeout', '7'
      , '--smoke-file', 'unit_plan.py', '--cc', '/opt/cc', '--cxx', '/opt/c++'
      , '--repo-url', 'https://example.invalid/Sprite.git'
      )
    self.assertIn('ulimit -v 1234 && ', out)
    self.assertIn(' timeout 7 ', out)
    self.assertIn(' unit_plan.py)', out)
    self.assertNotIn('unit_expr.py', out)
    self.assertIn('--with-cc=/opt/cc --with-cxx=/opt/c++ --with-cxx-postinstall=/opt/c++', out)
    self.assertIn('git clone https://example.invalid/Sprite.git %s' % self.repo, out)
    self.assertNotIn('--branch', out.split('Step 4/9')[1])
    out = self.dry_run('--repo', self.repo, '--cap-kb', 'unlimited')
    self.assertIn('ulimit -v unlimited && ', out)

  def test_jobs_auto(self):
    '''auto goes to configure as it is; the cores are printed, not baked in.'''
    out = self.dry_run('--repo', self.repo)
    # nproc honours the affinity and the cgroup limits, as
    # os.process_cpu_count does.
    cores = os.process_cpu_count()
    self.assertIn('jobs: auto (one per processor, counted by make; %d now)' % cores, out)
    self.assertIn('cores: %d ' % cores, out)
    self.assertIn('the core count (%d)' % cores, out)
    self.assertNotIn('--jobs=%d' % cores, out)

  def test_other_pakcs_version(self):
    '''A version without a pinned hash gets its size recorded.'''
    out = self.dry_run('--repo', self.repo, env={'PAKCS_VERSION': '3.9.9'})
    self.assertIn('pakcs-3.9.9-amd64-Linux.tar.gz', out)
    self.assertIn('no pinned checksum for PAKCS 3.9.9', out)
    self.assertIn("stat -c '%s bytes  %n'", out)
    self.assertNotIn(PAKCS_SHA256, out)
    self.assertIn('--with-pakcs=%s/pakcs-3.9.9/bin/pakcs' % self.prefix, out)

  def test_icurry(self):
    '''--icurry ports the icurry part of the CI script; HOME has no .cpmrc.'''
    out = self.dry_run('--repo', self.repo, '--icurry')
    prefix = self.prefix
    icurry = prefix + '/cpm/bin/icurry'
    self.assertInOrder(
        out, 'Step 3/9', 'icurry 3.1.0', 'cat > %s/.cpmrc' % self.home
      , 'BININSTALLPATH=%s/cpm/bin' % prefix
      , 'PACKAGEINDEXURL=https://cpm.curry-lang.org/PACKAGES/INDEX.tar.gz'
      , 'cypm update', 'cypm checkout icurry 3.1.0', 'cypm install'
      , ':load ICurry.Main :save :quit', 'mv %s/cpm/src/icurry/ICurry.Main %s' % (prefix, icurry)
      , 'Step 4/9', 'Step 6/9', '--with-icurry=' + icurry, 'icurry:      ' + icurry
      )
    self.assertIn('PATH=%s/pakcs-3.4.1/bin:/usr/local/bin:/usr/bin:/bin' % prefix, out)

  def test_existing_cpmrc_is_kept(self):
    with open(os.path.join(self.home, '.cpmrc'), 'w') as stream:
      stream.write('BININSTALLPATH=%s/elsewhere\n' % self.tmp)
    proc = self.run_script('--dry-run', '--prefix', self.prefix, '--repo', self.repo, '--icurry')
    self.assertEqual(proc.returncode, 0, proc.stderr)
    self.assertIn('.cpmrc exists and is kept', proc.stdout)
    self.assertIn('mv %s/cpm/src/icurry/ICurry.Main %s/elsewhere/icurry' % (self.prefix, self.tmp), proc.stdout)
    self.assertNotIn('cat > ', proc.stdout)
    self.assertEqual(os.listdir(self.home), ['.cpmrc'])

  def test_existing_checkout(self):
    '''An existing checkout is not cloned, and configure --help is probed.'''
    out = self.dry_run('--repo', ROOT, '--skip-apt')
    self.assertIn('present: %s' % ROOT, out)
    self.assertNotIn('git clone', out)
    self.assertIn('skipped (--skip-apt)', out)
    self.assertNotIn('could not be probed', out)
    self.assertIn('(cd %s && %s' % (ROOT, CLEAN_ENV), out)
    # configure of this checkout has --jobs: auto goes through unchanged.
    self.assertIn(' --jobs=auto', self.configure_line(out))
    # The script deletes nothing: a link of the checkout that points
    # elsewhere is reported, not replaced.
    for name in ['install', 'object-root']:
      path = os.path.join(ROOT, name)
      if os.path.islink(path):
        self.assertIn('%s points to' % path, out)
        self.assertNotIn('rm ', out)

  def configure_line(self, out):
    '''The configure command of a plan, or None.'''
    match = re.search(r'\+ \(cd \S+ && (.*\./configure.*)\)', out)
    return None if match is None else match.group(1)

  def test_configure_skipped_when_unchanged(self):
    '''
    configure empties install and object-root.  A run with the flags of
    the last run skips it while Make.config exists; --reconfigure forces it.
    '''
    if not os.path.isfile(os.path.join(ROOT, 'Make.config')):
      self.skipTest('the checkout is not configured')
    out = self.dry_run('--repo', ROOT, '--skip-apt')
    line = self.configure_line(out)
    self.assertIsNotNone(line)
    flags = line.split(' ./configure ')[1].split()
    self.assertTrue(all(flag.startswith('--') for flag in flags), flags)
    # The record of a previous run with the same flags.
    os.mkdir(self.prefix)
    with open(os.path.join(self.prefix, 'configure-args'), 'w') as stream:
      stream.write('\n'.join(flags) + '\n')
    proc = self.run_script('--dry-run', '--prefix', self.prefix, '--repo', ROOT, '--skip-apt')
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertIsNone(self.configure_line(proc.stdout))
    self.assertIn('skipped: Make.config exists and %s/configure-args holds the same flags' % self.prefix, proc.stdout)
    self.assertIn('--reconfigure forces it', proc.stdout)
    # make stage still runs: it is cheap when nothing changed.
    self.assertInOrder(proc.stdout, 'Step 6/9: configure', 'skipped', 'Step 7/9: make stage', ' make stage)')
    proc = self.run_script('--dry-run', '--prefix', self.prefix, '--repo', ROOT, '--skip-apt', '--reconfigure')
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertIsNotNone(self.configure_line(proc.stdout))
    self.assertNotIn('skipped: Make.config', proc.stdout)
    # Other flags: configure runs.
    proc = self.run_script('--dry-run', '--prefix', self.prefix, '--repo', ROOT, '--skip-apt', '--cc', '/opt/cc')
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertIsNotNone(self.configure_line(proc.stdout))
    self.assertEqual(sorted(os.listdir(self.prefix)), ['configure-args'])

  def test_skip_apt_without_dpkg(self):
    '''Without dpkg-query the apt step asks for --skip-apt.'''
    # A PATH of links to every tool of the standard directories, without
    # dpkg-query, so that the script cannot find it.
    farm = os.path.join(self.tmp, 'farm')
    os.mkdir(farm)
    for directory in ['/usr/local/bin', '/usr/bin', '/bin']:
      if not os.path.isdir(directory):
        continue
      for entry in os.scandir(directory):
        link = os.path.join(farm, entry.name)
        if entry.name != 'dpkg-query' and not os.path.lexists(link):
          os.symlink(entry.path, link)
    try:
      proc = self.run_script(
          '--dry-run', '--prefix', self.prefix, '--repo', self.repo
        , env={'PATH': farm}
        )
    finally:
      for name in os.listdir(farm):
        os.unlink(os.path.join(farm, name))
      os.rmdir(farm)
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertIn('not a Debian or Ubuntu system', proc.stdout)
    self.assertIn('a real run stops at: apt: no dpkg', proc.stdout)


class TestRealRunStops(SetupScriptTestCase):
  '''A real run stops at the apt step and runs no sudo.'''

  def test_missing_packages(self):
    self.fake('dpkg-query', 'exit 1\n')
    proc = self.run_script('--prefix', self.prefix, '--repo', self.repo)
    self.assertEqual(proc.returncode, 1)
    self.assertIn(
        'sudo apt-get update && sudo apt-get install -y --no-install-recommends '
            + ' '.join(APT_PACKAGES + ['linux-tools-generic'])
      , proc.stdout
      )
    self.assertIn('The script does not run sudo.', proc.stdout)
    self.assertIn('package(s) missing', proc.stderr)
    self.assertNotIn('Step 3/9', proc.stdout)
    self.assertNothingWritten()


if __name__ == '__main__':
  unittest.main()
