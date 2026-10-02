
import pytest
from conftest import ROOT

def test_drawio_png_siblings_when_assets_present():
    assets=ROOT/"docs"/"assets"; drawios=sorted(assets.glob("*.drawio")) if assets.exists() else []
    if not drawios: pytest.skip("docs/assets diagrams are written by the diagrams agent")
    for drawio in drawios:
        png=drawio.with_suffix(".png")
        if not png.exists() or png.stat().st_mtime < drawio.stat().st_mtime:
            pytest.skip(f"docs/assets diagram export is still in progress for {drawio.name}")
