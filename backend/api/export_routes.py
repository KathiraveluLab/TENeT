"""
Export / Report API Routes

Provides PDF report endpoints for individual communities
and state-level summary.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.database import get_db, Community
from app.digital_equity_integration import compute_digital_equity_for_community
from services.pdf_service import render_community_report_html, render_state_summary_html, html_to_pdf

router = APIRouter(prefix="/api", tags=["export"])


@router.get("/communities/{community_id}/report")
async def community_report(
    community_id: str,
    fmt: str = Query("pdf", description="Output format: pdf or html"),
    db: Session = Depends(get_db),
):
    """
    Generate a downloadable report for a single community.

    Contains: name, CAT tier, affordability status, safety net,
    key metrics, data sources, and timestamp.
    """
    community = db.query(Community).filter(Community.community_id == community_id).first()
    if not community:
        raise HTTPException(status_code=404, detail=f"Community '{community_id}' not found")

    # Ensure equity data is fresh
    equity = community.digital_equity_data
    if not equity:
        metrics = compute_digital_equity_for_community(community, db)
        if metrics:
            equity = {
                "affordability_status": metrics.affordability_status.value,
                "affordability_ratio": metrics.affordability_ratio,
                "value_index": metrics.value_index,
                "equity_classification": metrics.equity_classification.value,
                "classification_reason": metrics.classification_reason,
                "nearest_facility_km": metrics.nearest_facility_km,
                "has_community_anchor": metrics.has_community_anchor,
                "facility_count_5km": metrics.facility_count_5km,
            }

    html = render_community_report_html(community, equity)

    if fmt == "html":
        return HTMLResponse(content=html)

    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{community.name.replace(" ", "_")}_report.pdf"'
        },
    )


@router.get("/state-summary/report")
async def state_summary_report(
    fmt: str = Query("pdf", description="Output format: pdf or html"),
    db: Session = Depends(get_db),
):
    """
    Generate a state-wide summary report across all communities.
    """
    communities = db.query(Community).all()
    html = render_state_summary_html(communities)

    if fmt == "html":
        return HTMLResponse(content=html)

    pdf_bytes = html_to_pdf(html)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="TENeT_State_Summary.pdf"'
        },
    )
