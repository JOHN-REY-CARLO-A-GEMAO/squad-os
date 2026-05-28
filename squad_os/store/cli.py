"""
CLI entry point for Squad OS Agent Store commands.

Usage:
    python -m squad_os.store.cli build ./squad.yaml [--verbose]
    python -m squad_os.store.cli build ./squad.yaml -o ./my-package.sqad
    python -m squad_os.store.cli install-deps <package_id>
"""
import sys
import os
import asyncio
import subprocess
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from squad_os.store.loader import AgentPackageLoader


def print_summary(pkg):
    """Print a summary table of the package contents."""
    print("\n📦 Package Summary")
    print(f"{'='*40}")
    print(f"ID:          {pkg.package_id}")
    print(f"Name:        {pkg.name}")
    print(f"Version:     {pkg.version}")
    print(f"Author:      {pkg.manifest.get('author', 'Unknown')}")
    print(f"Description: {pkg.manifest.get('description', 'N/A')[:50]}...")
    print(f"{'-'*40}")
    print(f"Agents:      {len(pkg.custom_agents)}")
    for a in pkg.custom_agents:
        print(f"  - {a.get('role')}")
    print(f"Tools:       {len(pkg.custom_tools)}")
    for t in pkg.custom_tools:
        print(f"  - {t['module_name']}")
    print(f"Workflows:   {1 if pkg.workflow else 0}")
    print(f"Assets:      {len(pkg.assets)}")
    print(f"Deps:        {len(pkg.dependencies)}")
    for d in pkg.dependencies:
        print(f"  - {d}")
    print(f"{'='*40}\n")


async def install_deps_command(package_id):
    from squad_os.database.session import DB_PATH
    import aiosqlite

    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT version, install_path FROM installed_packages WHERE package_id = ? AND status = 'ACTIVE'", (package_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            print(f"❌ Error: Package '{package_id}' is not installed.")
            return

        version, install_path = row
        req_path = os.path.join(install_path, "requirements.txt")

        if not os.path.exists(req_path):
            print(f"ℹ️ Package '{package_id}' has no requirements.txt.")
            return

        with open(req_path, "r") as f:
            deps = [line.strip() for line in f if line.strip() and not line.startswith("#")]

        if not deps:
            print(f"ℹ️ requirements.txt for '{package_id}' is empty.")
            return

        print(f"📋 Dependencies for {package_id} v{version}:")
        for dep in deps:
            print(f"  - {dep}")

        confirm = input("\nDo you want to install these dependencies? [y/N]: ")
        if confirm.lower() != 'y':
            print("Aborted.")
            return

        print(f"🚀 Installing {len(deps)} dependencies...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + deps)
            print("\n✅ Dependencies installed successfully.")
        except subprocess.CalledProcessError as e:
            print(f"\n❌ Failed to install dependencies: {e}")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return

    command = args[0]

    if command == "build":
        if len(args) < 2:
            print("Usage: python -m squad_os.store.cli build <squad.yaml> [-o <output.sqad>] [--verbose]")
            sys.exit(1)

        yaml_path = args[1]
        output_path = None
        verbose = "--verbose" in args or "-v" in args

        if "-o" in args:
            idx = args.index("-o")
            if idx + 1 < len(args):
                output_path = args[idx + 1]

        if not os.path.exists(yaml_path):
            print(f"Error: {yaml_path} not found.")
            sys.exit(1)

        result_path = AgentPackageLoader.build_sqad_from_yaml(yaml_path, output_path)
        print(f"✅ Built: {result_path}")

        if verbose:
            pkg = AgentPackageLoader.load_sqad(result_path)
            if pkg:
                print_summary(pkg)

    elif command == "install-deps":
        if len(args) < 2:
            print("Usage: python -m squad_os.store.cli install-deps <package_id>")
            sys.exit(1)

        package_id = args[1]
        asyncio.run(install_deps_command(package_id))

    else:
        print(f"Unknown command: {command}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
