#!/usr/bin/env python3
"""Explicit local mesh verification; never installs, deploys, or invokes Actions."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys


def blob(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("required input is absent or is a symlink")
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def owned(root, relative):
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("manifest path escapes repository")
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("manifest path resolves outside repository")
    return path


def structure(root):
    manifest = json.loads((root / "automation/retired-actions.json").read_text())
    if manifest.get("schema_version") != 1 or not manifest.get("workflows"):
        raise ValueError("missing retirement manifest")
    active = root / ".github/workflows"
    if active.exists() and any(p.is_file() and p.suffix in (".yml", ".yaml")
                               for p in active.rglob("*")):
        raise ValueError("active Actions workflow found")
    archives = set()
    for entry in manifest["workflows"]:
        archive = entry["archive"]
        if archive in archives or not archive.startswith("automation/archived-workflows/"):
            raise ValueError("invalid or duplicate archive entry")
        archives.add(archive)
        if blob(owned(root, archive)) != entry["git_blob"]:
            raise ValueError("archived workflow changed")
    for entry in manifest["runtime_inputs"]:
        if blob(owned(root, entry["path"])) != entry["git_blob"]:
            raise ValueError("runtime input changed; requalify the migration manifest")
    return {"archived_workflows": len(archives), "active_workflows": 0,
            "preserved_runtime_inputs": len(manifest["runtime_inputs"])}


def verify(root, structure_only=False):
    receipt = {"structure": "PASS", **structure(root), "runtime": "NOT_RUN"}
    if structure_only:
        return receipt, 0
    package = json.loads((root / "package.json").read_text())
    declared = {**package.get("dependencies", {}), **package.get("devDependencies", {})}
    blockers = []
    if "vitest" not in declared:
        blockers.append("package test command names Vitest but Vitest is not declared")
    test_paths = [p for folder in ("test", "tests", "src")
                  for p in (root / folder).rglob("*") if p.is_file()
                  and any(mark in p.name for mark in (".test.", ".spec."))]
    if not test_paths:
        blockers.append("no application test corpus in test/, tests/ or src/")
    required = ("typescript/bin/tsc", "vitest/vitest.mjs", "hono/package.json")
    for path in required:
        if not (root / "node_modules" / path).is_file():
            blockers.append("installed local dependency missing: " + path.split("/")[0])
    node = shutil.which("node")
    if not node:
        blockers.append("Node.js unavailable")
    if blockers:
        receipt.update(runtime="BLOCKED", blockers=blockers)
        return receipt, 2
    commands = [[node, "node_modules/typescript/bin/tsc", "--noEmit"],
                [node, "node_modules/vitest/vitest.mjs", "run"]]
    receipt["commands"] = []
    for command in commands:
        result = subprocess.run(command, cwd=root, timeout=300, check=False,
                                stdout=sys.stderr, stderr=sys.stderr)
        receipt["commands"].append({"argv": command, "exit": result.returncode})
        if result.returncode:
            receipt["runtime"] = "FAIL"
            return receipt, 1
    # Refuse attribution if the observed source/archives changed during checks.
    structure(root)
    receipt["runtime"] = "PASS"
    return receipt, 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--structure-only", action="store_true",
                        help="validate retirement; explicitly leaves runtime NOT_RUN")
    args = parser.parse_args(argv)
    try:
        receipt, code = verify(args.root.resolve(), args.structure_only)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        receipt, code = {"structure": "FAIL", "runtime": "NOT_RUN",
                         "reason": str(exc)}, 1
    print(json.dumps(receipt, sort_keys=True))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
