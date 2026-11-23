#!/usr/bin/env python3
"""Clones the locked git sources of Ath12kWifi (tools/source-lock.json: linux, freebsd) as pattern-mode sparse checkouts, then
runs the module's own fetch for the rest (the supplicant archive).

Ath12kWifi's tools/fetch-sources.py clones them with `git clone --sparse` and then always runs `git sparse-checkout add` with
root-anchored patterns ("/drivers/net/wireless/ath/"). A git that starts sparse checkouts in cone mode (the macOS runner's)
refuses those patterns. Fetch the locked commits directly so moving branches do not change the source.
The pattern-mode checkouts pass the module's revision and content checks. Existing checkouts are left alone.

usage: prefetch-ath12k-sources.py ATH12K_WIFI_DIR
"""
import json
import subprocess
import sys
from pathlib import Path


def git(*args):
    subprocess.run(['git', *args], check=True)


def main():
    root = Path(sys.argv[1]).resolve()
    lock = json.loads((root / 'tools/source-lock.json').read_text())
    if lock.get('schema') != 1:
        raise SystemExit('unsupported Ath12kWifi source-lock schema')
    (root / 'deps').mkdir(exist_ok=True)
    for name in ('linux', 'freebsd'):
        source, directory = lock[name], root / 'deps' / name
        if directory.exists():
            print(f'ok    {name}: {directory} exists')
            continue
        git('init', '-q', str(directory))
        git('-C', str(directory), 'remote', 'add', 'origin', source['url'])
        git('-C', str(directory), 'fetch', '--depth', '1', '--filter=blob:none', 'origin', source['commit'])
        git('-C', str(directory), 'sparse-checkout', 'set', '--no-cone', *source['paths'])
        git('-C', str(directory), 'checkout', '--quiet', '--detach', 'FETCH_HEAD')
        head = subprocess.run(['git', '-C', str(directory), 'rev-parse', 'HEAD'], check=True, capture_output=True, text=True).stdout.strip()
        if head != source['commit']:
            raise SystemExit(f'{name}: checked out {head}, the lock expects {source["commit"]}')
        missing = [path for path in source['required'] if not (directory / path).is_file()]
        if missing:
            raise SystemExit(f'{name}: missing after checkout: {", ".join(missing)}')
        print(f'fetch {name}: {source["ref"]} {head}, {len(source["required"])} required files present')
    # Then the module's own fetch: the wpa_supplicant release archive (hash-checked and unpacked) and the identity check of every
    # source. The payload's runtime builds the supplicant (build-wifi-userspace.py, its prepare-supplicant.py only checks) before
    # the kernel build would run this through build-ath12k-wifi.py.
    subprocess.run([sys.executable, str(root / 'tools/fetch-sources.py')], check=True)


if __name__ == '__main__':
    main()
