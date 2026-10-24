"""Create a clean source ZIP from this directory. No installed dependencies included."""

from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
out = root.parent / "DebitLens_HackFront_Prototype.zip"
excluded = {
    "node_modules",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "data",
    "local-data",
    "test-results",
    "playwright-report",
    ".git",
}
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if (
            not p.is_file()
            or any(part in excluded for part in rel.parts)
            or p.name == ".env"
            or p.suffix in (".pyc", ".db", ".tsbuildinfo")
        ):
            continue
        z.write(p, Path("DebitLens") / rel)
print(f"{out.name}: {out.stat().st_size:,} bytes")
