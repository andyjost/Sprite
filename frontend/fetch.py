#!/usr/bin/env python3
'''Fetch separately from the build; retain downloads, hashes, and metadata.

The first CI run establishes the source URL/hash, not a reproducibility pin.
Pass --url and --sha256 together once the reviewer has verified them.
'''
import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import shutil
import tarfile
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urljoin
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent
SITE = 'https://www.curry-lang.org/pakcs/download/'
GITLAB = 'https://git-ps.informatik.uni-kiel.de'
PROJECT = 'curry/curry-frontend'


class Links(HTMLParser):
  def __init__(self):
    super().__init__()
    self.links = []

  def handle_starttag(self, tag, attrs):
    if tag == 'a':
      self.links.extend(v for k, v in attrs if k == 'href')


def download(url, path):
  print('Fetching ' + url, flush=True)
  with urlopen(url, timeout=120) as response, path.open('wb') as dest:
    shutil.copyfileobj(response, dest)
  digest = hashlib.sha256(path.read_bytes()).hexdigest()
  print(digest + '  ' + path.name, flush=True)
  path.with_suffix(path.suffix + '.sha256').write_text(digest + '  ' + path.name + '\n')
  return digest


def extract(archive, destination):
  destination.mkdir(parents=True, exist_ok=True)
  # data_filter is available since the minimum supported Python 3.11.4.
  with tarfile.open(archive) as tar:
    tar.extractall(destination, filter='data')


def main():
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument('--output', required=True, type=Path)
  parser.add_argument('--url')
  parser.add_argument('--sha256')
  args = parser.parse_args()
  if bool(args.url) != bool(args.sha256):
    parser.error('--url and --sha256 must be supplied together')
  dest = args.output.resolve()
  dest.mkdir(parents=True, exist_ok=True)
  archive = dest / 'source.tar.gz'
  url = args.url
  origin = 'pinned-url' if url else 'pakcs-3.4.1-source'
  if not url:
    links = Links()
    try:
      # Check the actual page naming on the runner, retaining it for review.
      download(SITE, dest / 'download-page.html')
      links.feed((dest / 'download-page.html').read_text(errors='replace'))
    except (HTTPError, URLError, TimeoutError) as err:
      print('Download page unavailable: ' + str(err), flush=True)
    candidates = [urljoin(SITE, v) for v in links.links
        if re.search(r'pakcs-3\.4\.1[^/]*(?:src|source)[^/]*\.tar\.gz$', v)]
    candidates.append(SITE + 'pakcs-3.4.1-src.tar.gz')
    for candidate in dict.fromkeys(candidates):
      try:
        digest = download(candidate, archive)
        # Reject an HTML error page with HTTP 200.
        with tarfile.open(archive):
          pass
        url = candidate
        break
      except (HTTPError, URLError, TimeoutError, tarfile.TarError) as err:
        print('Source candidate failed: ' + str(err), flush=True)
    if not url:
      origin = 'gitlab-curry-frontend-tag'
      api = GITLAB + '/api/v4/projects/' + quote(PROJECT, safe='')
      # Discover tag spelling; never silently build the default branch.
      download(api + '/repository/tags?per_page=100', dest / 'tags.json')
      tags = json.loads((dest / 'tags.json').read_text())
      tag = next((t for t in tags if t['name'] in ('2.0.0', 'v2.0.0')), None)
      if tag is None:
        raise SystemExit('No 2.0.0 tag found; reviewer must establish upstream tag.')
      url = api + '/repository/archive.tar.gz?sha=' + quote(tag['commit']['id'])
      (dest / 'tag.json').write_text(json.dumps(tag, indent=2) + '\n')
      digest = download(url, archive)
  else:
    digest = download(url, archive)
  if args.sha256 and digest != args.sha256:
    raise SystemExit('Source checksum mismatch: ' + digest)
  extract(archive, dest / 'unpacked')
  cabals = sorted((dest / 'unpacked').rglob('*.cabal'))
  matches = [p for p in cabals if re.search(
      r'^name:\s*curry-frontend\s*$', p.read_text(), re.M | re.I)]
  if len(matches) != 1:
    raise SystemExit('Expected one curry-frontend cabal file; found ' + repr(cabals))
  cabal = matches[0]
  if not re.search(r'^version:\s*2\.0\.0\s*$', cabal.read_text(), re.M | re.I):
    raise SystemExit('Source does not declare curry-frontend version 2.0.0')
  source = cabal.parent
  shutil.copytree(source, dest / 'source')
  licenses = dest / 'licenses'
  shutil.copytree(ROOT / 'licenses', licenses)
  shutil.copy2(source / 'LICENSE', licenses / 'LICENSE.curry-frontend')
  if origin != 'gitlab-curry-frontend-tag':
    # The PAKCS source archive's top-level license takes precedence.
    roots = list((dest / 'unpacked').iterdir())
    if len(roots) == 1 and roots[0].is_dir() and (roots[0] / 'LICENSE').is_file():
      shutil.copy2(roots[0] / 'LICENSE', licenses / 'LICENSE-PAKCS')
  info = dict(url=url, sha256=digest, origin=origin, version='2.0.0')
  (dest / 'source-info.json').write_text(json.dumps(info, indent=2) + '\n')
  print(json.dumps(info, indent=2), flush=True)
  for p in sorted((dest / 'source').glob('*')):
    print(p.name, flush=True)
    if p.suffix in ('.cabal', '.yaml') or p.name in ('Makefile', 'cabal.project'):
      print(p.read_text(), flush=True)


if __name__ == '__main__':
  main()
