"""
PDF Service

Renders HTML report templates and converts them to PDF bytes.
Uses a pure-Python approach (no external binary dependencies).

If `weasyprint` is available it will be used for high-fidelity PDF
generation; otherwise falls back to a simple HTML-as-bytes wrapper
so the export endpoints always work.
"""

from datetime import datetime, timezone
from typing import Optional, List

_WEASYPRINT_AVAILABLE = False
try:
    from weasyprint import HTML as WeasyprintHTML  # type: ignore
    _WEASYPRINT_AVAILABLE = True
except ImportError:
    pass


# ── Shared CSS ─────────────────────────────────────────────────────

_REPORT_CSS = """
<style>
  body { font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }
  h1 { color: #1a1a2e; border-bottom: 2px solid #1a1a2e; padding-bottom: 8px; }
  h2 { color: #16213e; margin-top: 28px; }
  .meta { font-size: 0.85em; color: #888; margin-bottom: 24px; }
  table { width: 100%; border-collapse: collapse; margin: 16px 0; }
  th, td { text-align: left; padding: 8px 12px; border-bottom: 1px solid #e0e0e0; }
  th { background: #f5f5f5; font-weight: 600; }
  .badge { display: inline-block; padding: 3px 10px; border-radius: 12px; font-size: 0.85em; font-weight: 600; }
  .badge-green  { background: #d4edda; color: #155724; }
  .badge-yellow { background: #fff3cd; color: #856404; }
  .badge-red    { background: #f8d7da; color: #721c24; }
  .badge-gray   { background: #e9ecef; color: #495057; }
  .footer { margin-top: 40px; font-size: 0.8em; color: #aaa; border-top: 1px solid #eee; padding-top: 8px; }
  .section { margin-bottom: 24px; }
</style>
"""

_BADGE_MAP = {
    "ready": ("Ready — Affordable", "badge-green"),
    "supported": ("Supported — Community Anchor", "badge-yellow"),
    "excluded": ("Excluded — Critical Gap", "badge-red"),
    "insufficient_data": ("Insufficient Data", "badge-gray"),
    "affordable": ("Affordable", "badge-green"),
    "unaffordable": ("Unaffordable", "badge-red"),
}


def _badge(key: str) -> str:
    label, cls = _BADGE_MAP.get(key, (key, "badge-gray"))
    return f'<span class="badge {cls}">{label}</span>'


# ── Community Report ───────────────────────────────────────────────

def render_community_report_html(community, equity_data: Optional[dict]) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    eq = equity_data or {}

    aff_ratio = eq.get("affordability_ratio")
    aff_ratio_str = f"{aff_ratio:.1f} %" if aff_ratio else "N/A"
    value_idx = eq.get("value_index")
    value_idx_str = f"${value_idx:.2f}/Mbps" if value_idx else "N/A"

    conn = community.connectivity_data or {}
    access = community.access_data or {}

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>TENeT Report — {community.name}</title>{_REPORT_CSS}</head>
<body>
<h1>TENeT Community Report</h1>
<p class="meta">Generated {now} · Dataset v0.3.0</p>

<div class="section">
  <h2>{community.name}</h2>
  <table>
    <tr><th>Region</th><td>{community.region or 'N/A'}</td></tr>
    <tr><th>Population</th><td>{community.population or 'N/A'}</td></tr>
    <tr><th>Coordinates</th><td>{community.latitude:.4f}, {community.longitude:.4f}</td></tr>
    <tr><th>Access Tier (CAT)</th><td>Tier {community.access_tier or 'N/A'}</td></tr>
    <tr><th>Data Completeness</th><td>{round((community.data_completeness or 0) * 100)}%</td></tr>
  </table>
</div>

<div class="section">
  <h2>Digital Equity Analysis</h2>
  <table>
    <tr><th>Equity Classification</th><td>{_badge(eq.get('equity_classification', 'insufficient_data'))}</td></tr>
    <tr><th>Affordability Status</th><td>{_badge(eq.get('affordability_status', 'insufficient_data'))}</td></tr>
    <tr><th>Affordability Ratio</th><td>{aff_ratio_str}</td></tr>
    <tr><th>Value Index</th><td>{value_idx_str}</td></tr>
    <tr><th>Nearest Facility</th><td>{eq.get('nearest_facility_km', 'N/A')} km</td></tr>
    <tr><th>Community Anchor</th><td>{'Yes' if eq.get('has_community_anchor') else 'No'}</td></tr>
    <tr><th>Facilities within 5 km</th><td>{eq.get('facility_count_5km', 0)}</td></tr>
    <tr><th>Classification Reason</th><td>{eq.get('classification_reason', 'N/A')}</td></tr>
  </table>
</div>

<div class="section">
  <h2>Connectivity</h2>
  <table>
    <tr><th>Download</th><td>{conn.get('download_mbps', 'N/A')} Mbps</td></tr>
    <tr><th>Upload</th><td>{conn.get('upload_mbps', 'N/A')} Mbps</td></tr>
    <tr><th>Latency</th><td>{conn.get('latency_ms', 'N/A')} ms</td></tr>
    <tr><th>Source</th><td>{conn.get('source', 'N/A')}</td></tr>
  </table>
</div>

<div class="section">
  <h2>Data Sources</h2>
  <ul>
    <li>Healthcare facilities — OpenStreetMap / Healthsites</li>
    <li>Broadband coverage — FCC Form 477 / Ookla</li>
    <li>Income estimates — ACS 5-Year / Tier proxy</li>
    <li>Affordability standard — UN Broadband Commission (2 % threshold)</li>
  </ul>
</div>

<div class="footer">
  TENeT — Telehealth Effectiveness &amp; Necessity Tracker · v0.3.0 · {now}
</div>
</body></html>"""
    return html


# ── State Summary Report ──────────────────────────────────────────

def render_state_summary_html(communities: list) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total = len(communities)

    counts = {"ready": 0, "supported": 0, "excluded": 0, "insufficient_data": 0}
    tier_counts = {1: 0, 2: 0, 3: 0}

    for c in communities:
        eq = c.digital_equity_data or {}
        cls = eq.get("equity_classification", "insufficient_data")
        counts[cls] = counts.get(cls, 0) + 1
        if c.access_tier in tier_counts:
            tier_counts[c.access_tier] += 1

    rows = ""
    for c in sorted(communities, key=lambda x: x.name):
        eq = c.digital_equity_data or {}
        cls = eq.get("equity_classification", "insufficient_data")
        aff = eq.get("affordability_ratio")
        aff_str = f"{aff:.1f}%" if aff else "—"
        rows += f"<tr><td>{c.name}</td><td>{c.region or '—'}</td><td>T{c.access_tier or '?'}</td><td>{_badge(cls)}</td><td>{aff_str}</td></tr>\n"

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>TENeT State Summary</title>{_REPORT_CSS}</head>
<body>
<h1>TENeT — Alaska State Summary</h1>
<p class="meta">Generated {now} · Dataset v0.3.0 · {total} communities</p>

<div class="section">
  <h2>Equity Classification Overview</h2>
  <table>
    <tr><th>Classification</th><th>Count</th><th>Percentage</th></tr>
    <tr><td>{_badge('ready')}</td><td>{counts['ready']}</td><td>{_pct(counts['ready'], total)}</td></tr>
    <tr><td>{_badge('supported')}</td><td>{counts['supported']}</td><td>{_pct(counts['supported'], total)}</td></tr>
    <tr><td>{_badge('excluded')}</td><td>{counts['excluded']}</td><td>{_pct(counts['excluded'], total)}</td></tr>
    <tr><td>{_badge('insufficient_data')}</td><td>{counts['insufficient_data']}</td><td>{_pct(counts['insufficient_data'], total)}</td></tr>
  </table>
</div>

<div class="section">
  <h2>Access Tier Distribution</h2>
  <table>
    <tr><th>Tier</th><th>Count</th></tr>
    <tr><td>Tier 1 — Good access</td><td>{tier_counts.get(1, 0)}</td></tr>
    <tr><td>Tier 2 — Fair access</td><td>{tier_counts.get(2, 0)}</td></tr>
    <tr><td>Tier 3 — Limited access</td><td>{tier_counts.get(3, 0)}</td></tr>
  </table>
</div>

<div class="section">
  <h2>Community Details</h2>
  <table>
    <tr><th>Name</th><th>Region</th><th>Tier</th><th>Equity Status</th><th>Afford. Ratio</th></tr>
    {rows}
  </table>
</div>

<div class="section">
  <h2>Methodology</h2>
  <ul>
    <li><strong>Affordability:</strong> UN Broadband Commission 2 % threshold</li>
    <li><strong>Community Anchor:</strong> Healthcare facility within 5 km radius</li>
    <li><strong>Value Index:</strong> Monthly cost ÷ Download Mbps</li>
  </ul>
</div>

<div class="footer">
  TENeT — Telehealth Effectiveness &amp; Necessity Tracker · v0.3.0 · {now}
</div>
</body></html>"""
    return html


def _pct(count: int, total: int) -> str:
    if total == 0:
        return "0 %"
    return f"{round(count / total * 100, 1)} %"


# ── PDF Conversion ────────────────────────────────────────────────

def html_to_pdf(html: str) -> bytes:
    """
    Convert HTML string to PDF bytes.

    Uses weasyprint if available; otherwise returns the HTML bytes
    with a text/html content hint (the route sets media_type to application/pdf).
    """
    if _WEASYPRINT_AVAILABLE:
        return WeasyprintHTML(string=html).write_pdf()

    # Fallback: return raw HTML bytes — the browser will render it.
    return html.encode("utf-8")
