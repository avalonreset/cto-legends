"""Prove every installed managed module resolves its canonical recipe."""
import argparse
from pathlib import Path
from cto_legends.discovery import handoff
from cto_legends.manager import read_state

p = argparse.ArgumentParser()
p.add_argument('--home', type=Path, required=True)
args = p.parse_args()
for key in read_state(args.home)['active']:
    result = handoff(key, args.home)
    if not result['instructions'] or result['missing_instructions']:
        raise SystemExit(f"{key}: missing recipe files {result['missing_instructions']}")
    print(key + ': canonical recipe resolved')
