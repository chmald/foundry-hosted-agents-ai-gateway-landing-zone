
from __future__ import annotations
import importlib.util, sys
from pathlib import Path
from types import ModuleType
ROOT=Path(__file__).resolve().parents[1]
def load_module(name: str, path: Path) -> ModuleType:
    for module_name in ["agent", "gateway_auth", "telemetry"]:
        sys.modules.pop(module_name, None)
    sys.path.insert(0, str(path.parent)); spec=importlib.util.spec_from_file_location(name,path); module=importlib.util.module_from_spec(spec); assert spec and spec.loader; sys.modules[name]=module; spec.loader.exec_module(module); return module
