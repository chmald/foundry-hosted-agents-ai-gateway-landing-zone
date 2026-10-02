
import os
from pathlib import Path
from conftest import ROOT
ALLOWED_PARTS=(str(Path("config")/"profiles"), str(Path("src")/"agents"/"maf"/"profiles"), str(Path("src")/"agents"/"langgraph"/"profiles"), str(Path("src")/"catalog-mcp"/"data"/"profiles"), str(Path("src")/"records-api"/"data"/"profiles"))
def iter_text_files():
    for folder in ["config","src","samples","scripts","tests"]:
        for path in (ROOT/folder).rglob("*"):
            if path.is_file() and path.suffix.lower() in {".py",".json",".md",".txt",".yaml",".yml",".ps1",".ini"}: yield path
def test_runtime_code_uses_profile_not_hardcoded_example_domain():
    forbidden=[t.strip().lower() for t in os.environ.get("REUSABILITY_DENYLIST","").split(",") if t.strip()]
    if not forbidden: return
    offenders=[]
    for path in iter_text_files():
        rel=str(path.relative_to(ROOT))
        if rel.startswith(ALLOWED_PARTS): continue
        text=path.read_text(encoding="utf-8",errors="ignore").lower()
        for term in forbidden:
            if term in text: offenders.append(f"{rel}: {term}")
    assert not offenders
