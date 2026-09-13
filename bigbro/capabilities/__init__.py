"""Capability system.

A Capability is one thing BigBro can do (read a file, run a build, scaffold a project...).
Built-ins live in this package; the owner's custom capabilities live in <project>/capabilities.
Both directories are scanned at startup — any module exposing a CAPABILITIES list is loaded.
"""

import importlib.util
from pathlib import Path

BUILTIN_DIR = Path(__file__).resolve().parent
USER_DIR = BUILTIN_DIR.parent.parent / "capabilities"


def load_capabilities(workspace, user_dir=None):
    """Instantiate every capability class from built-in + user directories."""
    caps = []
    seen = set()
    directories = [BUILTIN_DIR, Path(user_dir) if user_dir is not None else USER_DIR]

    for directory in directories:
        if not directory or not directory.exists():
            continue
        for f in sorted(directory.glob("*.py")):
            if f.name.startswith("_"):
                continue
            try:
                spec = importlib.util.spec_from_file_location(f"bigbro_cap_{f.stem}", f)
                if spec is None or spec.loader is None:
                    continue
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print(f"[bigbro] failed to load capability module {f.name}: {e}")
                continue
            for item in getattr(mod, "CAPABILITIES", []):
                if isinstance(item, type):
                    cap = item(workspace)
                else:
                    cap = item
                    cap.workspace = Path(workspace).resolve()
                if cap.name in seen:
                    print(f"[bigbro] capability '{cap.name}' skipped (duplicate name)")
                    continue
                seen.add(cap.name)
                caps.append(cap)
    return caps
