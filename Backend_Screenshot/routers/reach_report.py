"""
Reach Report router
===================
Endpoints:
  POST /reach-report/upload           — upload & validate files (template + bursts)
  POST /reach-report/generate         — parse + generate consolidated report
  GET  /reach-report/download/{fname} — download generated xlsx
  GET  /reach-report/history          — list previously generated reports
  DELETE /reach-report/history/{id}   — delete a saved report

Files are stored in Backend_Screenshot/reach_report_outputs/.
History is persisted in ctr_db (same DB as final_report_store).
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from database.crm_db import crm_engine
from services.reach_parser import parse_campaign_file, parse_filename, parse_template_file
from services.reach_generator import generate_reach_report

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reach-report", tags=["reach-report"])

# ── Output directory ──────────────────────────────────────────────────────────
_REACH_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "reach_report_outputs",
)
os.makedirs(_REACH_DIR, exist_ok=True)

# Temp upload dir (re-use same location)
_UPLOAD_DIR = os.path.join(_REACH_DIR, "_uploads")
os.makedirs(_UPLOAD_DIR, exist_ok=True)


# ── DB helpers ────────────────────────────────────────────────────────────────

def _get_conn():
    return crm_engine.raw_connection()


def _ensure_table():
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS reach_report_store (
                id              SERIAL PRIMARY KEY,
                report_filename TEXT    NOT NULL,
                campaign_label  TEXT,
                platform        TEXT,
                format_type     TEXT,
                file_data       BYTEA   NOT NULL,
                generated_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """)
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        logger.warning("_ensure_table failed: %s", e)

_ensure_table()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """
    Upload one or more Excel files.
    Files whose names contain 'template' become the master template.
    All other .xlsx files are treated as campaign burst inputs.
    Returns { template, inputs, errors }.
    """
    result   = {"template": None, "inputs": [], "errors": []}
    saved    = []

    for f in files:
        fname = f.filename or ""
        if not fname.lower().endswith(".xlsx"):
            result["errors"].append(f"{fname}: only .xlsx files are accepted")
            continue

        # Save to temp dir with a unique prefix to avoid collisions
        uid      = uuid.uuid4().hex[:8]
        temp_path = os.path.join(_UPLOAD_DIR, f"{uid}_{fname}")
        content  = await f.read()
        try:
            with open(temp_path, "wb") as fh:
                fh.write(content)
        except Exception as e:
            result["errors"].append(f"{fname}: save failed — {e}")
            continue

        is_template = "template" in fname.lower()

        if is_template:
            result["template"] = {"filename": fname, "path": temp_path}
        else:
            try:
                audience, burst = parse_filename(fname)
                result["inputs"].append({
                    "filename": fname,
                    "path":     temp_path,
                    "label":    f"{audience} — Burst {burst}",
                    "audience": audience,
                    "burst":    burst,
                })
            except ValueError as e:
                result["errors"].append(f"{fname}: {e}")

    return result


@router.post("/generate")
async def generate_report(
    template_path: str         = Form(...),
    input_paths:   str         = Form(...),   # comma-separated file paths
    platform:      str         = Form("MPN"),
    format_type:   str         = Form("Banner"),
    output_label:  Optional[str] = Form(None),
):
    """
    Generate the consolidated MPN & CPN Breakdown workbook.
    Returns the Excel file as a download and saves it to history.
    """
    if not os.path.isfile(template_path):
        raise HTTPException(status_code=400, detail=f"Template file not found: {template_path}")

    paths = [p.strip() for p in input_paths.split(",") if p.strip()]
    if not paths:
        raise HTTPException(status_code=400, detail="No input files provided")

    for p in paths:
        if not os.path.isfile(p):
            raise HTTPException(status_code=400, detail=f"Input file not found: {p}")

    # Parse
    campaigns = []
    for p in paths:
        try:
            campaigns.append(parse_campaign_file(p))
        except Exception as e:
            raise HTTPException(status_code=400,
                detail=f"Error parsing {os.path.basename(p)}: {e}")

    try:
        template_meta = parse_template_file(template_path, platform=platform, format_type=format_type)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error parsing template: {e}")

    # Generate workbook
    try:
        wb = generate_reach_report(campaigns, template_meta)
    except Exception as e:
        logger.exception("generate_reach_report failed")
        raise HTTPException(status_code=500, detail=f"Report generation error: {e}")

    # Serialise to bytes
    import io
    buf = io.BytesIO()
    wb.save(buf)
    report_bytes = buf.getvalue()

    # Save to history DB
    label      = output_label or f"{platform} {format_type} — {len(campaigns)} burst(s)"
    ts         = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_name   = f"reach_report_{ts}.xlsx"
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            """
            INSERT INTO reach_report_store
                (report_filename, campaign_label, platform, format_type, file_data)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (out_name, label, platform, format_type, report_bytes),
        )
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        logger.warning("Could not save report to DB: %s", e)

    return Response(
        content     = report_bytes,
        media_type  = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers     = {"Content-Disposition": f'attachment; filename="{out_name}"'},
    )


@router.get("/history")
def list_history():
    """Return all saved reach reports (no file bytes)."""
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute("""
            SELECT id, report_filename, campaign_label, platform, format_type,
                   generated_at, octet_length(file_data) AS file_size
            FROM   reach_report_store
            ORDER  BY generated_at DESC
        """)
        rows = cur.fetchall()
        cur.close(); conn.close()
        return [
            {
                "id":             r[0],
                "filename":       r[1],
                "campaign_label": r[2],
                "platform":       r[3],
                "format_type":    r[4],
                "generated_at":   r[5].isoformat() if r[5] else None,
                "file_size":      r[6],
            }
            for r in rows
        ]
    except Exception as e:
        logger.exception("list_history failed")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{report_id}/download")
def download_history(report_id: int):
    """Download a previously generated report from DB."""
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            "SELECT report_filename, file_data FROM reach_report_store WHERE id = %s",
            (report_id,),
        )
        row = cur.fetchone()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not row:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

    fname, fdata = row
    return Response(
        content    = bytes(fdata),
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers    = {"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@router.delete("/history/{report_id}")
def delete_history(report_id: int):
    """Delete a saved reach report."""
    try:
        conn = _get_conn()
        cur  = conn.cursor()
        cur.execute(
            "DELETE FROM reach_report_store WHERE id = %s RETURNING id",
            (report_id,),
        )
        deleted = cur.fetchone()
        conn.commit()
        cur.close(); conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return {"deleted": report_id}
