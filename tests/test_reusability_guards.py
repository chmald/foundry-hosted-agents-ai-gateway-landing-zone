import os
import re
import subprocess
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

# Internal authoring-tool names and sales/process jargon have no meaning for readers outside
# the original authoring team, so they must not appear in any published file.
INTERNAL_TERMS=re.compile(
    r"demo-pattern-authoring|azure-architecture-diagrams|daily[_ ]?driver|MCAPS|\bMCEM\b|\bMSX\b|\bTPID\b|\bCSAM\b"
    r"|hard[- ]rules?\s*#|authoring gate|Copilot CLI session|\bSolution Engineers?\b|\bsellers?\b|\baccount team\b"
    r"|hands-on-keyboard|Technical Close Plan|\bwin plan\b|\bsolution play\b|\bMACC\b|Azure Consumed Revenue"
    r"|consumption uplift|Tech Elevate|Cloud Accelerate Factory|Viva Engage|\bSeismic\b|microsoft\.sharepoint\.com"
    r"|\binternal[- ]only\b|Microsoft[- ]internal|not for customer distribution|\btalk track\b",
    re.IGNORECASE)
TRACKED_SUFFIXES={".py",".json",".md",".txt",".yaml",".yml",".ps1",".ini",".bicep",".drawio",".xml",".kql",".html"}
def test_no_internal_terminology():
    listed=subprocess.run(["git","-C",str(ROOT),"ls-files","-z"],capture_output=True,check=False)
    paths=[ROOT/p for p in listed.stdout.decode("utf-8").split("\0") if p] if listed.returncode==0 else list(ROOT.rglob("*"))
    offenders=[]
    for path in paths:
        if path.resolve()==Path(__file__).resolve() or not path.is_file() or path.suffix.lower() not in TRACKED_SUFFIXES: continue
        for lineno,line in enumerate(path.read_text(encoding="utf-8",errors="ignore").splitlines(),1):
            offenders+=[f"{path.relative_to(ROOT)}:{lineno}: {m.group(0)}" for m in INTERNAL_TERMS.finditer(line)]
    assert not offenders, "Rewrite internal terminology for an external reader"
