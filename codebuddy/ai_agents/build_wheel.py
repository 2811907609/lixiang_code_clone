#!/usr/bin/env python3
"""
Build script that creates a self-contained wheel with local dependencies.
"""
import shutil
import subprocess
from pathlib import Path

def main():
    # Copy local packages as top-level packages (not under ai_agents)
    local_packages = [
        "../../packages/externalapis/externalapis",
        "../../packages/sysutils/sysutils",
        "../../packages/commonlibs/commonlibs",
        "../../packages/repoutils/repoutils"
    ]

    # Copy each package to project root as top-level package
    copied_packages = []
    for package_path in local_packages:
        src = Path(package_path)
        if src.exists():
            package_name = src.name
            dst = Path(package_name)  # Copy to project root, not under ai_agents
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            copied_packages.append(dst)
            print(f"Copied {src} -> {dst}")

    # Build the wheel
    _ = subprocess.run(["uv", "build"], check=True)

    # Clean up copied packages
    for dst in copied_packages:
        if dst.exists():
            shutil.rmtree(dst)
            print(f"Cleaned up {dst}")

    print("Wheel built successfully!")

if __name__ == "__main__":
    main()
