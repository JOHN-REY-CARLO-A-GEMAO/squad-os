"""
CLI entry point for Squad OS Agent Store commands.

Usage:
    python -m squad_os.store.cli build ./squad.yaml
    python -m squad_os.store.cli build ./squad.yaml -o ./my-package.sqad
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from squad_os.store.loader import AgentPackageLoader


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    command = args[0]

    if command == "build":
        if len(args) < 2:
            print("Usage: python -m squad_os.store.cli build <squad.yaml> [-o <output.sqad>]")
            sys.exit(1)

        yaml_path = args[1]
        output_path = None
        if "-o" in args:
            idx = args.index("-o")
            if idx + 1 < len(args):
                output_path = args[idx + 1]

        if not os.path.exists(yaml_path):
            print(f"Error: {yaml_path} not found.")
            sys.exit(1)

        result = AgentPackageLoader.build_sqad_from_yaml(yaml_path, output_path)
        print(f"✅ Built: {result}")
    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
