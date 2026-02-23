"""
Map Snapshot Service

Generates static PNG map images for embedding in reports.

Strategy:
  Uses `staticmap` library (pip install staticmap) which renders
  tiles + markers to a Pillow Image — no headless browser needed.

If staticmap is not available, returns a placeholder SVG.
"""

import io
from typing import Optional

_STATICMAP_AVAILABLE = False
try:
    import staticmap  # type: ignore
    _STATICMAP_AVAILABLE = True
except ImportError:
    pass


def generate_snapshot(
    communities: list,
    center_lat: float = 64.2,
    center_lon: float = -153.0,
    zoom: int = 5,
    width: int = 800,
    height: int = 600,
    region: Optional[str] = None,
) -> bytes:
    """
    Render a static map snapshot as PNG bytes.

    Args:
        communities: list of Community ORM objects (must have lat/lon and digital_equity_data)
        center_lat / center_lon: map center
        zoom: tile zoom level
        width / height: image dimensions
        region: optional filter – only show communities in this region

    Returns:
        PNG image bytes
    """
    if not _STATICMAP_AVAILABLE:
        return _placeholder_svg(width, height)

    m = staticmap.StaticMap(width, height, url_template="https://a.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png")

    color_map = {
        "ready": "#28a745",
        "supported": "#ffc107",
        "excluded": "#dc3545",
        "insufficient_data": "#9E9E9E",
    }

    for c in communities:
        if region and c.region and region.lower() not in c.region.lower():
            continue
        eq = c.digital_equity_data or {}
        cls = eq.get("equity_classification", "insufficient_data")
        color = color_map.get(cls, "#9E9E9E")

        marker = staticmap.CircleMarker(
            (c.longitude, c.latitude), color, 6
        )
        m.add_marker(marker)

    buf = io.BytesIO()
    image = m.render(zoom=zoom, center=[center_lon, center_lat])
    image.save(buf, format="PNG")
    return buf.getvalue()


def _placeholder_svg(width: int, height: int) -> bytes:
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="#f5f5f5"/>
  <text x="50%" y="50%" text-anchor="middle" fill="#999" font-size="18"
        font-family="Arial, sans-serif">
    Map snapshot unavailable (install staticmap)
  </text>
</svg>"""
    return svg.encode("utf-8")
