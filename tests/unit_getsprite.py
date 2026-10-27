'''The user installers and container recipes, without network access.'''
import cytest # from ./lib; must be first
import os, pathlib, pty, shlex, shutil, subprocess, tempfile, tomllib, unittest

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCRIPTS = ['getsprite', 'getsprite-i']
PYTHON = 'cpython>=3.11.4,<3.16'


class TestGetSprite(unittest.TestCase):
  def setUp(self):
    self.tmp = pathlib.Path(tempfile.mkdtemp(prefix='getsprite-'))
    self.addCleanup(shutil.rmtree, self.tmp)
    self.home = self.tmp / 'home with spaces'
    self.bin = self.tmp / 'bin'
    self.home.mkdir()
    self.bin.mkdir()
    self.calls = self.tmp / 'calls'
    self.env = dict(os.environ)
    for key in list(self.env):
      if key.startswith('UV_') or key == 'GETSPRITE_FIND_LINKS':
        del self.env[key]
    self.env.update(HOME=str(self.home), PATH=str(self.bin) + ':/usr/bin:/bin',
                    LC_ALL='C.UTF-8', CALLS=str(self.calls))
    self.uv_body = '''printf '%s\\n' uv "$UV_TOOL_BIN_DIR" "$@" >> "$CALLS"
exit "${FAIL_UV:-0}"
'''
    for name in ['curl', 'sudo', 'apt-get', 'python', 'python3', 'pip']:
      self.fake(name, 'printf "unexpected %s\\n" >> "$CALLS"; exit 91\n' % name)

  def fake(self, name, body):
    path = self.bin / name
    path.write_text('#!/bin/sh\n' + body)
    path.chmod(0o755)
    return path

  def bootstrap(self):
    self.env['FAKE_UV'] = str(self.fake('fake-uv', self.uv_body))
    self.fake('curl', '''printf '%s\\n' curl "$@" >> "$CALLS"
cat <<'INSTALLER'
set -eu
test "$UV_NO_MODIFY_PATH" = 1
mkdir -p "$UV_INSTALL_DIR"
cp "$FAKE_UV" "$UV_INSTALL_DIR/uv"
INSTALLER
''')

  def run_script(self, name='getsprite', *args, answers=None, piped=False):
    cmd = ['/bin/sh', str(ROOT / name), *args]
    kwds = {}
    if answers is not None:
      master, slave = pty.openpty()
      self.addCleanup(os.close, master)
      self.addCleanup(os.close, slave)
      os.write(master, answers.encode())
      kwds['stdin'] = slave
      if piped:
        import fcntl, termios
        def terminal():
          os.setsid()
          fcntl.ioctl(0, termios.TIOCSCTTY, 0)
        kwds['preexec_fn'] = terminal
        cmd = ['/bin/sh', '-c', 'cat %s | sh' % shlex.quote(str(ROOT / name))]
    else:
      kwds['stdin'] = subprocess.DEVNULL
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True, env=self.env, timeout=10, **kwds)

  def assertOK(self, proc):
    self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
    self.assertEqual(proc.stderr, '')

  def log(self):
    return self.calls.read_text().splitlines() if self.calls.exists() else []

  def expected_uv(self):
    return ['uv', str(self.home / '.local/bin'), 'tool', 'install', '--upgrade',
            '--managed-python', '--python', PYTHON, '--no-build',
            '--with-executables-from', 'curry-frontend', 'curry']

  def test_posix_syntax(self):
    for name in SCRIPTS + ['scripts/getsprite-check.sh']:
      with self.subTest(script=name):
        path = ROOT / name
        self.assertTrue(path.read_text().startswith('#!/bin/sh\n'))
        self.assertTrue(os.access(path, os.X_OK))
        self.assertOK(subprocess.run(['/bin/sh', '-n', str(path)],
                                     capture_output=True, text=True))

  def test_dry_run(self):
    for existing in [False, True]:
      if existing:
        self.fake('uv', self.uv_body)
      for name in SCRIPTS:
        with self.subTest(script=name, existing_uv=existing):
          proc = self.run_script(name, '--dry-run')
          self.assertOK(proc)
          for part in ['curl -LsSf https://astral.sh/uv/install.sh | sh',
                       'managed CPython 3.11.4', PYTHON, 'curry-frontend',
                       'uv tool install --upgrade', '--with-executables-from curry-frontend curry',
                       'export PATH="$HOME/.local/bin:$PATH"']:
            self.assertIn(part, proc.stdout)
          self.assertEqual(self.log(), [])
          self.assertEqual(list(self.home.iterdir()), [])

  def test_help_and_invalid_option(self):
    for name in SCRIPTS:
      proc = self.run_script(name, '--help')
      self.assertOK(proc)
      self.assertIn('--dry-run', proc.stdout)
      self.assertIn('GETSPRITE_FIND_LINKS', proc.stdout)
      proc = self.run_script(name, '--bogus')
      self.assertEqual(proc.returncode, 2)
      self.assertIn('Unknown option', proc.stderr)
    self.assertEqual(self.log(), [])

  def test_install_and_upgrade_with_existing_uv(self):
    self.fake('uv', self.uv_body)
    for _ in range(2):
      self.assertOK(self.run_script())
    self.assertEqual(self.log(), self.expected_uv() * 2)
    self.assertEqual(list(self.home.iterdir()), [])

  def test_uv_in_home_off_path(self):
    bindir = self.home / '.local/bin'
    bindir.mkdir(parents=True)
    uv = bindir / 'uv'
    uv.write_text('#!/bin/sh\n' + self.uv_body)
    uv.chmod(0o755)
    self.assertOK(self.run_script())
    self.assertEqual(self.log(), self.expected_uv())

  def test_bootstrap(self):
    self.bootstrap()
    self.assertOK(self.run_script())
    self.assertEqual(self.log(), ['curl', '-LsSf',
                     'https://astral.sh/uv/install.sh'] + self.expected_uv())
    self.assertTrue((self.home / '.local/bin/uv').exists())

  def test_bootstrap_failure(self):
    self.fake('curl', 'exit 22\n')
    proc = self.run_script()
    self.assertNotEqual(proc.returncode, 0)
    self.assertIn('did not install uv', proc.stderr)
    self.assertNotIn('Sprite installed.', proc.stdout)
    self.assertEqual(list(self.home.iterdir()), [])

  def test_uv_failure(self):
    self.fake('uv', self.uv_body)
    self.env['FAIL_UV'] = '17'
    proc = self.run_script()
    self.assertEqual(proc.returncode, 17)
    self.assertNotIn('Sprite installed.', proc.stdout)

  def test_wheel_locations_are_single_arguments(self):
    self.fake('uv', self.uv_body)
    for links in ['a wheel directory; $(exit 99)', 'https://example.org/wheels/']:
      self.env['GETSPRITE_FIND_LINKS'] = links
      self.calls.unlink(missing_ok=True)
      self.assertOK(self.run_script())
      self.assertEqual(self.log(), self.expected_uv() + ['--find-links', links])
      self.calls.unlink()
      for name in SCRIPTS:
        proc = self.run_script(name, '--dry-run')
        self.assertOK(proc)
        self.assertIn('--find-links', proc.stdout)
        self.assertIn(links, proc.stdout)
      self.assertEqual(self.log(), [])

  def test_interactive_decline_before_bootstrap(self):
    self.bootstrap()
    proc = self.run_script('getsprite-i', answers='n\n')
    self.assertEqual(proc.returncode, 1)
    self.assertIn('Install uv?', proc.stdout)
    self.assertEqual(self.log(), [])
    self.assertEqual(list(self.home.iterdir()), [])

  def test_interactive_decline_before_sprite(self):
    self.bootstrap()
    proc = self.run_script('getsprite-i', answers='y\nn\n')
    self.assertEqual(proc.returncode, 1)
    self.assertIn('Install or upgrade Sprite', proc.stdout)
    self.assertEqual(self.log(), ['curl', '-LsSf',
                                 'https://astral.sh/uv/install.sh'])

  @cytest.linux_only('the piped run makes the pty the controlling terminal with TIOCSCTTY, which hangs the read from /dev/tty on macOS')
  def test_interactive_accept_from_terminal_and_pipe(self):
    for piped in [False, True]:
      with self.subTest(piped=piped):
        self.bootstrap()
        self.calls.unlink(missing_ok=True)
        shutil.rmtree(self.home / '.local', ignore_errors=True)
        proc = self.run_script('getsprite-i', answers='y\ny\n', piped=piped)
        self.assertOK(proc)
        self.assertEqual(self.log(), ['curl', '-LsSf',
                         'https://astral.sh/uv/install.sh'] + self.expected_uv())

  def test_interactive_existing_uv_needs_one_confirmation(self):
    self.fake('uv', self.uv_body)
    proc = self.run_script('getsprite-i', answers='y\n')
    self.assertOK(proc)
    self.assertNotIn('Install uv?', proc.stdout)
    self.assertEqual(self.log(), self.expected_uv())

  def test_runtime_dependency(self):
    with (ROOT / 'pyproject.toml').open('rb') as stream:
      project = tomllib.load(stream)['project']
    self.assertIn('curry-frontend>=3.1.0', project['dependencies'])
    self.assertFalse(any(dep.split('>')[0] == 'uv'
                         for dep in project['dependencies']))

  def test_container_commands(self):
    self.fake('docker', '''printf '%s\\n' "$@" > "$CALLS"
cat > "$CALLS.recipe"
''')
    wheels = self.tmp / 'wheel files'
    wheels.mkdir()
    for image in ['ubuntu:22.04', 'ubuntu:24.04']:
      self.env['GETSPRITE_FIND_LINKS'] = str(wheels)
      self.assertOK(self.run_script('scripts/getsprite-check.sh', image))
      args = self.log()
      self.assertIn(image, args)
      self.assertIn('type=bind,src=%s,dst=/wheels,readonly' % wheels, args)
      self.assertIn('GETSPRITE_FIND_LINKS=/wheels', args)
      recipe = pathlib.Path(str(self.calls) + '.recipe').read_text()
      self.assertIn('su -s /bin/sh sprite', recipe)
      self.assertIn('set -- curl ca-certificates', recipe)
      self.assertIn('sprite-make --so Smoke.curry', recipe)


if __name__ == '__main__':
  unittest.main()
