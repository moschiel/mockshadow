"""Merge generated release locks into a consumer, preserving other platforms."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project', type=Path)
    parser.add_argument('locks', nargs='+', type=Path)
    args = parser.parse_args()
    destination = args.project / 'mockshadow.lock.json'
    merged = json.loads(destination.read_text()) if destination.exists() else None
    for path in args.locks:
        lock = json.loads(path.read_text())
        if merged is None or merged['version'] != lock['version']:
            merged = {'version': lock['version'], 'assets': {}}
        merged['assets'].update(lock['assets'])
    destination.write_text(json.dumps(merged, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
