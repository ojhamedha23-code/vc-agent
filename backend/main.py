"""
FastAPI Backend — VC Due Diligence Agent API (multi-tenant with Clerk auth).

Every endpoint requires a valid Clerk JWT in `Authorization: Bearer <token>`.
Deals are scoped to the caller's Clerk org_id, so org members share a pipeline.

Set CLERK_DEV_MODE=true in .env to bypass auth during local development.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict

import uvicorn
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add both backend/ and project root to sys.path
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from auth import get_role, require_org, require_permission, verify_token
from database import (
    delete_deal,
    get_all_deals,
    get_deal,
    get_deal_by_hash,
    get_org_settings,
    init_db,
    save_deal,
    save_org_email,
    save_org_thesis,
)

# ── App setup ─────────────────────────────────────────────────────────────────

app = FastAPI(title="VC Due Diligence Agent API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://insidersden.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory progress store: job_id → list[str]
_progress_store: Dict[str, list] = {}
_result_store: Dict[str, object] = {}


@app.on_event("startup")
def startup():
    init_db()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _send_notification_email(
    company: str, fit_pct: float, action: str, deal_id: str, notify_email: str
):
    """Send memo-ready email via Resend. No-ops if not configured."""
    api_key = os.getenv("RESEND_API_KEY", "")
    if not api_key or not notify_email:
        return
    try:
        import resend

        resend.api_key = api_key
        color = {"REVIEW": "#22c55e", "PASS": "#ef4444", "ARCHIVE": "#f59e0b"}.get(action, "#6b7280")
        resend.Emails.send(
            {
                "from": "InsidersDen <onboarding@resend.dev>",
                "to": [notify_email],
                "subject": f"Memo ready: {company} — {action} ({fit_pct:.0f}% fit)",
                "html": f"""
                <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:24px">
                  <h2 style="margin:0 0 8px">📄 Memo ready: {company}</h2>
                  <p style="color:#6b7280;margin:0 0 20px">Your due diligence memo has been generated.</p>
                  <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
                    <tr><td style="padding:8px;color:#6b7280">Thesis Fit</td>
                        <td style="padding:8px;font-weight:600">{fit_pct:.1f}%</td></tr>
                    <tr style="background:#f9fafb">
                        <td style="padding:8px;color:#6b7280">Action</td>
                        <td style="padding:8px">
                          <span style="background:{color};color:#fff;padding:2px 10px;border-radius:99px;font-size:13px;font-weight:600">{action}</span>
                        </td></tr>
                  </table>
                  <a href="https://insidersden.vercel.app/deals/{deal_id}"
                     style="display:inline-block;background:#3b82f6;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600">
                    View Full Memo →
                  </a>
                  <p style="color:#9ca3af;font-size:12px;margin-top:24px">InsidersDen · AI-powered VC due diligence</p>
                </div>
                """,
            }
        )
    except Exception as exc:
        print(f"[email] Failed to send notification: {exc}")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Thesis ────────────────────────────────────────────────────────────────────

@app.get("/api/thesis")
def get_thesis(payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    settings = get_org_settings(org_id)
    text = settings.get("thesis_text", "")
    return {"text": text}


@app.post("/api/thesis")
async def save_thesis(body: dict, payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    require_permission(payload, "edit_thesis")
    text = body.get("text", "").strip()
    save_org_thesis(org_id, text)
    return {"status": "saved"}


@app.post("/api/thesis/upload")
async def upload_thesis_file(
    file: UploadFile = File(...),
    payload: dict = Depends(verify_token),
):
    """Parse PDF or Excel and return extracted text for the thesis."""
    org_id = require_org(payload)
    require_permission(payload, "edit_thesis")

    import io

    suffix = Path(file.filename).suffix.lower()
    content = await file.read()

    if suffix == ".pdf":
        import pdfplumber

        parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t and t.strip():
                    parts.append(t.strip())
        thesis_text = "\n\n".join(parts)

    elif suffix in (".xlsx", ".xls"):
        import openpyxl

        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        parts = []
        for sheet in wb.worksheets:
            parts.append(f"=== {sheet.title} ===")
            for row in sheet.iter_rows(values_only=True):
                vals = [str(c).strip() if c is not None else "" for c in row]
                if any(vals):
                    parts.append("  |  ".join(vals))
        thesis_text = "\n".join(parts)

    else:
        raise HTTPException(status_code=400, detail="Only PDF and Excel (.xlsx) files supported.")

    if not thesis_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the file.")

    return {"text": thesis_text}


# ── Notify Email ──────────────────────────────────────────────────────────────

@app.get("/api/notify-email")
def get_notify_email(payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    settings = get_org_settings(org_id)
    return {"email": settings.get("notify_email", "")}


@app.post("/api/notify-email")
async def save_notify_email(body: dict, payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    email = body.get("email", "").strip()
    save_org_email(org_id, email)
    return {"status": "saved"}


# ── Deals ─────────────────────────────────────────────────────────────────────

@app.get("/api/deals")
def list_deals(payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    deals = get_all_deals(org_id)
    return [
        {
            "id": d["id"],
            "company": d["company"],
            "sector": d["sector"],
            "stage": d["stage"],
            "hq": d["hq"],
            "fit_pct": d["fit_pct"],
            "action": d["action"],
            "confidence": d["confidence"],
            "bonus_pts": d["bonus_pts"],
            "deck_name": d["deck_name"],
            "created_at": d["created_at"],
            "uploaded_by": d.get("uploaded_by"),
        }
        for d in deals
    ]


@app.get("/api/deals/{deal_id}")
def get_deal_detail(deal_id: str, payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    deal = get_deal(deal_id, org_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    for key in ("claims_json", "fact_json", "thesis_json", "memo_json", "search_logs", "slide_texts", "errors_json"):
        val = deal.get(key)
        if val:
            try:
                deal[key] = json.loads(val)
            except Exception:
                pass
    return deal


@app.delete("/api/deals/{deal_id}")
def remove_deal(deal_id: str, payload: dict = Depends(verify_token)):
    org_id = require_org(payload)
    require_permission(payload, "delete")
    delete_deal(deal_id, org_id)
    return {"status": "deleted"}


# ── Org info ──────────────────────────────────────────────────────────────────

@app.get("/api/me")
def get_me(payload: dict = Depends(verify_token)):
    """Return current user's org and role — used by the frontend role hook."""
    org_id = require_org(payload)
    return {
        "user_id": payload.get("sub"),
        "org_id": org_id,
        "role": get_role(payload),
    }


# ── Analysis ──────────────────────────────────────────────────────────────────

def _load_thesis_for_org(org_id: str) -> str:
    settings = get_org_settings(org_id)
    t = settings.get("thesis_text", "").strip()
    return t if t and not t.startswith("Paste your fund") else ""


def _run_pipeline_sync(job_id: str, mode: str, org_id: str, user_id: str, **kwargs):
    """Run pipeline in a thread; push progress lines to _progress_store."""
    from pipeline import (
        run_pipeline,
        run_pipeline_images,
        run_pipeline_pptx,
        run_pipeline_url,
    )

    _progress_store[job_id] = []

    def on_progress(msg: str):
        _progress_store[job_id].append(msg)

    thesis_text = _load_thesis_for_org(org_id)
    try:
        if mode == "pdf":
            result = run_pipeline(kwargs["path"], thesis_text, on_progress, org_id=org_id, deal_id=job_id)
        elif mode == "pptx":
            result = run_pipeline_pptx(kwargs["path"], thesis_text, on_progress, org_id=org_id, deal_id=job_id)
        elif mode == "url":
            result = run_pipeline_url(kwargs["url"], thesis_text, on_progress, org_id=org_id, deal_id=job_id)
        elif mode == "images":
            result = run_pipeline_images(kwargs["image_bytes"], kwargs["media_types"], thesis_text, on_progress, org_id=org_id, deal_id=job_id)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        save_deal(
            job_id,
            kwargs.get("deck_name", "unknown"),
            result,
            org_id=org_id,
            uploaded_by=user_id,
            file_hash=kwargs.get("file_hash"),
        )
        _result_store[job_id] = {"status": "done", "deal_id": job_id}
        _progress_store[job_id].append("__DONE__")

        # Email notification
        if result.thesis_result:
            settings = get_org_settings(org_id)
            _send_notification_email(
                company=result.claims.startup_name if result.claims else kwargs.get("deck_name", "Unknown"),
                fit_pct=result.thesis_result.overall_fit,
                action=result.thesis_result.action,
                deal_id=job_id,
                notify_email=settings.get("notify_email", ""),
            )
    except Exception as exc:
        _result_store[job_id] = {"status": "error", "error": str(exc)}
        _progress_store[job_id].append(f"__ERROR__{exc}")


@app.post("/api/analyze/file")
async def analyze_file(
    file: UploadFile = File(...),
    payload: dict = Depends(verify_token),
):
    import concurrent.futures
    import hashlib

    org_id  = require_org(payload)
    user_id = payload.get("sub", "unknown")
    require_permission(payload, "upload")

    if not _load_thesis_for_org(org_id):
        raise HTTPException(status_code=400, detail="No thesis set. Save your fund thesis first.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".pptx"):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files supported.")

    content = await file.read()
    file_hash = hashlib.md5(content).hexdigest()

    # Deduplication: same file + same org = return cached result
    existing = get_deal_by_hash(file_hash, org_id)
    if existing:
        job_id = existing["id"]
        _progress_store[job_id] = []
        _result_store[job_id] = {"status": "done", "deal_id": job_id}
        _progress_store[job_id].append("__DONE__")
        return {"job_id": job_id}

    job_id = str(uuid.uuid4())
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    deck_name = Path(file.filename).stem
    mode = "pdf" if suffix == ".pdf" else "pptx"

    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor()

    def _run():
        _run_pipeline_sync(
            job_id, mode,
            org_id=org_id, user_id=user_id,
            path=tmp_path, deck_name=deck_name, file_hash=file_hash,
        )
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    loop.run_in_executor(executor, _run)
    return {"job_id": job_id}


@app.post("/api/analyze/url")
async def analyze_url(body: dict, payload: dict = Depends(verify_token)):
    import concurrent.futures

    org_id  = require_org(payload)
    user_id = payload.get("sub", "unknown")
    require_permission(payload, "upload")

    if not _load_thesis_for_org(org_id):
        raise HTTPException(status_code=400, detail="No thesis set.")

    url = body.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    job_id    = str(uuid.uuid4())
    deck_name = url.split("/")[-1].replace(".pdf", "") or "url-deck"

    loop     = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor()

    def _run():
        _run_pipeline_sync(
            job_id, "url",
            org_id=org_id, user_id=user_id,
            url=url, deck_name=deck_name,
        )

    loop.run_in_executor(executor, _run)
    return {"job_id": job_id}


@app.get("/api/analyze/progress/{job_id}")
async def stream_progress(job_id: str):
    """SSE stream — no auth required (job_id is the access token here)."""

    async def event_generator():
        seen = 0
        max_wait = 300
        waited = 0.0

        while waited < max_wait:
            messages = _progress_store.get(job_id, [])
            while seen < len(messages):
                msg = messages[seen]
                seen += 1
                if msg.startswith("__DONE__"):
                    yield f"data: {json.dumps({'type': 'done', 'deal_id': job_id})}\n\n"
                    return
                elif msg.startswith("__ERROR__"):
                    err = msg[len("__ERROR__"):]
                    yield f"data: {json.dumps({'type': 'error', 'message': err})}\n\n"
                    return
                else:
                    yield f"data: {json.dumps({'type': 'progress', 'message': msg})}\n\n"

            await asyncio.sleep(0.5)
            waited += 0.5

        yield f"data: {json.dumps({'type': 'error', 'message': 'Timeout'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
