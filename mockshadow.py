#!/usr/bin/env python3
"""Generate an isolated source tree using explicit version 2 mock recipes."""
import argparse
from pathlib import Path
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument('--version', action='version', version='Mockshadow 2.0')
    commands = parser.add_subparsers(dest='command', required=True)
    mock = commands.add_parser('mock', help='Generate shadow_output', allow_abbrev=False)
    mock.add_argument('-f', '--force', action='store_true', help='Reapply recipes without the cache')
    mock.add_argument('-v', '--details', action='store_true', help='Show transformation diagnostics')
    audit = commands.add_parser('audit', help='Check recipes without publishing output', allow_abbrev=False)
    audit.add_argument('-r', '--report', type=Path, help='Write a JSON report')
    commands.add_parser('list', help='List recipes and their explicit destinations')
    create = commands.add_parser('create-project', help='Create an empty v2 simulator project')
    create.add_argument('name')
    opening = commands.add_parser('open-mock', help='Find or create a recipe for a target', allow_abbrev=False)
    opening.add_argument('target', help='Path relative to the original project')
    opening.add_argument('--recipe', help='New recipe path relative to mocksDirectory')
    opening.add_argument('--editor', help='Optional editor executable (otherwise print the path)')
    args = parser.parse_args(argv)
    try:
        if args.command == 'create-project':
            import mock_utils
            mock_utils.create_mockshadow_project(args.name)
            return 0
        import runtime
        project = Path(runtime.DIR_MOCK_SHADOW_PROJECT)
        original = Path(runtime.USER_ENV['originalProject']).resolve()
        config = runtime.USER_CONFIGS
        if args.command == 'mock':
            from pipeline import generate
            generate(project, original, config, force=args.force, details=args.details)
        elif args.command == 'audit':
            from audit import run_audit
            return run_audit(project, original, config, args.report)
        elif args.command == 'list':
            from pipeline import prepare_inputs
            _, additions, recipes = prepare_inputs(project, original, config)
            for target, recipe in sorted(recipes.items()):
                print(f'{recipe.path.relative_to(project)} -> {target} ({recipe.mode})')
            for target, path in sorted(additions.items()):
                print(f'{path.relative_to(project)} -> {target} (additional)')
        elif args.command == 'open-mock':
            from open_mock import open_mock
            open_mock(project, original, config, args.target, args.recipe, args.editor)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        print(f'Mockshadow: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
