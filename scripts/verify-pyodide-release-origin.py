#!/usr/bin/env python3
"""Check the pinned Pyodide release mapping and optionally replay saved archives."""

import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import tarfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.source_snapshot import read_file

MANIFEST = "sbom/nested-runtime/pyodide-wasm-release.json"
ASSETS = "sbom/assets/notices.json"
LOCK = "site/package-lock.json"
RECIPE_FILES = (
    ".gitmodules", ".github/workflows/main.yml", ".github/workflows/deploy_release.yml",
    "Makefile", "Makefile.envs", "cpython/Makefile", "emsdk/Makefile",
)
RUNTIME_FILES = {
    "pyodide.asm.wasm", "pyodide.asm.mjs", "pyodide.mjs",
    "pyodide-lock.json", "python_stdlib.zip",
}
SOURCE_ARCHIVE_REVISION = re.compile("[0-9a-f]{40}")
SHA256 = re.compile("[0-9a-f]{64}")
ARCHIVE_LIMIT = 55_000_000
METADATA_LIMIT = 500_000
MEMBER_LIMIT = 12_000_000


def require(ok, reason):
    if not ok:
        raise ValueError(reason)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def no_duplicate_keys(pairs):
    obj = {}
    for key, value in pairs:
        require(key not in obj, "Duplicate JSON field")
        obj[key] = value
    return obj


def read_json(path):
    return json.loads(read_file(path, 8_000_000), object_pairs_hook=no_duplicate_keys)


def tar_members(raw, prefix, names):
    # Scan only the pinned archive in memory. Never create files from member names.
    targets = {prefix + name: name for name in names}
    members = {}
    with tarfile.open(fileobj=io.BytesIO(raw), mode="r:*") as archive:
        for index, entry in enumerate(archive):
            require(index < 16_384, "Tar member count limit")
            if entry.name not in targets:
                continue
            key = targets[entry.name]
            require(entry.isfile() and key not in members, "Duplicate or nonregular selected member")
            require(0 < entry.size <= MEMBER_LIMIT, "Tar member size limit")
            with archive.extractfile(entry) as stream:
                payload = stream.read(entry.size + 1)
            require(len(payload) == entry.size, "Incomplete tar member")
            members[key] = payload
    require(members.keys() == set(names), "Selected archive members missing")
    return members


def checked_manifest():
    manifest = read_json(ROOT / MANIFEST)
    require(manifest.keys() == {"format", "pyodide_version", "python_version", "emscripten_version",
                                "pyodide_commit", "pyodide_build_commit", "emscripten_commit",
                                "archives", "recipe_hashes", "runtime_members"},
            "Release manifest fields changed")
    version = manifest["pyodide_version"]
    python = manifest["python_version"]
    emscripten = manifest["emscripten_version"]
    require(
        manifest["format"] == "ai-trust-id-pyodide-wasm-release/v1"
        and all(isinstance(x, str) and re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", x)
                for x in (version, python, emscripten)),
        "Unsupported release manifest",
    )
    revisions = [manifest[key] for key in ("pyodide_commit", "pyodide_build_commit", "emscripten_commit")]
    require(all(SOURCE_ARCHIVE_REVISION.fullmatch(rev) for rev in revisions), "Malformed upstream revision")
    pyodide_commit, build_commit, emscripten_commit = revisions
    archives = manifest["archives"]
    expected = {
        "npm.tgz": f"https://registry.npmjs.org/pyodide/-/pyodide-{version}.tgz",
        "core.tar.bz2": f"https://github.com/pyodide/pyodide/releases/download/{version}/pyodide-core-{version}.tar.bz2",
        "source.tar.gz": f"https://codeload.github.com/pyodide/pyodide/tar.gz/{pyodide_commit}",
        "build.tar.gz": f"https://codeload.github.com/pyodide/pyodide-build/tar.gz/{build_commit}",
        "cpython.tgz": f"https://www.python.org/ftp/python/{python}/Python-{python}.tgz",
        "emscripten.tar.gz": f"https://codeload.github.com/emscripten-core/emscripten/tar.gz/{emscripten_commit}",
    }
    require(archives.keys() == expected.keys(), "Archive selections changed")
    for name, url in expected.items():
        row = archives[name]
        require(
            row.keys() == {"url", "bytes", "sha256"} and row["url"] == url
            and type(row["bytes"]) is int and 0 < row["bytes"] <= ARCHIVE_LIMIT
            and SHA256.fullmatch(row["sha256"]),
            "Unpinned archive",
        )
    assets = read_json(ROOT / ASSETS)
    locked = read_json(ROOT / LOCK)["packages"]["node_modules/pyodide"]
    require(
        assets["runtime_origin"] == {"version": locked["version"], "resolved": locked["resolved"],
                                     "integrity": locked["integrity"], "artifact_sha256": archives["npm.tgz"]["sha256"]}
        and locked["version"] == version and locked["resolved"] == expected["npm.tgz"],
        "Pyodide lock or artifact changed",
    )
    runtime = {row["name"]: {"sha256": row["sha256"], "bytes": row["bytes"]} for row in assets["runtime_members"]}
    require(len(assets["runtime_members"]) == len(RUNTIME_FILES) and runtime.keys() == RUNTIME_FILES
            and runtime == manifest["runtime_members"], "Runtime member evidence changed")
    recipes = manifest["recipe_hashes"]
    require(recipes.keys() == set(RECIPE_FILES) and all(SHA256.fullmatch(x) for x in recipes.values()),
            "Build recipe selections changed")
    return manifest, locked


def replay(directory, manifest, locked):
    def archive(name):
        meta = manifest["archives"][name]
        raw = read_file(directory / name, meta["bytes"])
        require(len(raw) == meta["bytes"] and digest(raw) == meta["sha256"], "Archive digest or length mismatch")
        return raw

    npm = archive("npm.tgz")
    lock_integrity = "sha512-" + base64.b64encode(hashlib.sha512(npm).digest()).decode("ascii")
    require(lock_integrity == locked["integrity"], "npm integrity mismatch")
    bundled = tar_members(npm, "package/", RUNTIME_FILES)
    core = tar_members(archive("core.tar.bz2"), "pyodide/", RUNTIME_FILES)
    for name, raw in bundled.items():
        expected = manifest["runtime_members"][name]
        require(raw == core[name] and {"bytes": len(raw), "sha256": digest(raw)} == expected,
                "Release core or bundled runtime member differs")
    info = json.loads(bundled["pyodide-lock.json"], object_pairs_hook=no_duplicate_keys)["info"]
    require(info["arch"] == "wasm32" and info["python"] == manifest["python_version"]
            and info["platform"] == "emscripten_" + manifest["emscripten_version"].replace(".", "_"),
            "Runtime metadata contradicts recipe")
    recipes = tar_members(archive("source.tar.gz"), "pyodide-" + manifest["pyodide_commit"] + "/", RECIPE_FILES)
    require({name: digest(raw) for name, raw in recipes.items()} == manifest["recipe_hashes"],
            "Pyodide build recipe bytes changed")
    require(len(recipes["Makefile.envs"]) < METADATA_LIMIT, "Recipe metadata limit")
    make_env = recipes["Makefile.envs"].decode("utf-8")
    for name, value in (
        ("PYVERSION", manifest["python_version"]),
        ("PYODIDE_EMSCRIPTEN_VERSION", manifest["emscripten_version"]),
        ("PYTHON_ARCHIVE_SHA256", manifest["archives"]["cpython.tgz"]["sha256"]),
    ):
        values = re.findall(rf"^export {name} *\??= *([^ \t\r\n]+)$", make_env, re.M)
        require(values == [value], "Recipe source pin mismatch")
    for name in ("cpython.tgz", "build.tar.gz", "emscripten.tar.gz"):
        archive(name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-dir", type=Path, help="Existing directory holding the six named archives")
    args = parser.parse_args()
    try:
        manifest, lock = checked_manifest()
        if args.replay_dir is not None:
            replay(args.replay_dir, manifest, lock)
        print(json.dumps({
            "pass": True,
            "manifest": MANIFEST,
            "release": manifest["pyodide_version"],
            "archives_replayed": 6 if args.replay_dir is not None else 0,
            "runtime_members_compared": len(RUNTIME_FILES) if args.replay_dir is not None else 0,
            "upstream_recipe_files_checked": len(RECIPE_FILES) if args.replay_dir is not None else 0,
            "wasm_rebuilt_from_source": False,
            "full_dependency_coverage": False,
            "permission_cleared": False,
        }))
        return 0
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError) as error:
        print(f"Pyodide release verification failed ({type(error).__name__}).", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
