# Reference Material

The visual source of truth is **`screenshots/reference.pdf`** — 6 pages of helpdesk UI screenshots (Word export, 2026-10-06). Use it for:

- layout and information hierarchy
- navigation and sidebar structure
- labels, list/table styling, spacing
- device/camera-tree patterns
- colors, typography, status indicators

The two `.jpg` files that older manifests listed (`helpdesk_camera_tree_01/02.jpg`) do **not** exist in this package; `reference.pdf` replaces them.

To view: open the PDF in VS Code or a browser. To extract pages as PNGs (optional, needs Python):

```powershell
python -m pip install pymupdf
python -c "import fitz, pathlib; d=fitz.open(r'reference/screenshots/reference.pdf'); out=pathlib.Path('reference/screenshots/pages'); out.mkdir(exist_ok=True, parents=True); [out.joinpath(f'page_{i+1}.png').write_bytes(p.get_pixmap().tobytes('png')) for i,p in enumerate(d)]"
```

(`reference/screenshots/pages/` is gitignored.)

Do not treat this material as credentials or a production integration source.

