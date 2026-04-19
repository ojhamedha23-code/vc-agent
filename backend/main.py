"""
FastAPI Backend — wraps the VC agent pipeline as REST endpoints.

Endpoints:
  GET  /api/deals              → list all screened deals
  GET  /api/deals/{id}         → single deal detail
  DELETE /api/deals/{id}       → delete a deal
  POST /api/analyze/file       → upload PDF or PPTX
  POST /api/analyze/url        → analyze from PDF URL
  GET  /api/analyze/progress/{job_id} → SSE stream of pipeline progress
  GET  /api/thesis             → get current thesis text
  POST /api/thesis             → save thesis text
  GET  /health                 → health check
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
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# Add both backend/ and project root to sys.path
# backend/ → finds database.py
# project root → finds pipeline.py, agents/, tools/, schemas/
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import delete_deal, get_all_deals, get_deal, get_deal_by_hash, init_db, save_deal

THESIS_TEXT_PATH = Path(__file__).parent.parent / "config" / "thesis_text.txt"
NOTIFY_EMAIL_PATH = Path(__file__).parent.parent / "config" / "notify_email.txt"


def _get_notify_email() -> str:
    if NOTIFY_EMAIL_PATH.exists():
        return NOTIFY_EMAIL_PATH.read_text().strip()
    return os.getenv("NOTIFY_EMAIL", "")


def _send_notification_email(company: str, fit_pct: float, action: str, deal_id: str):
    """Send memo-ready email via Resend. Silently no-ops if not configured."""
    api_key = os.getenv("RESEND_API_KEY", "")
    to_email = _get_notify_email()
    if not api_key or not to_email:
        return
    try:
        import resend
        resend.api_key = api_key
        action_color = {"REVIEW": "#22c55e", "PASS": "#ef4444", "ARCHIVE": "#f59e0b"}.get(action, "#6b7280")
        resend.Emails.send({
            "from": "InsidersDen <onboarding@resend.dev>",
            "to": [to_email],
            "subject": f"Memo ready: {company} — {action} ({fit_pct:.0f}% fit)",
            "html": f"""
            <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:24px">
              <h2 style="margin:0 0 8px">📄 Memo ready: {company}</h2>
              <p style="color:#6b7280;margin:0 0 20px">Your due diligence memo has been generated.</p>
              <table style="width:100%;border-collapse:collapse;margin-bottom:20px">
                <tr><td style="padding:8px;color:#6b7280">Thesis Fit</td><td style="padding:8px;font-weight:600">{fit_pct:.1f}%</td></tr>
                <tr style="background:#f9fafb"><td style="padding:8px;color:#6b7280">Action</td>
                  <td style="padding:8px"><span style="background:{action_color};color:#fff;padding:2px 10px;border-radius:99px;font-size:13px;font-weight:600">{action}</span></td></tr>
              </table>
              <a href="https://insidersden.vercel.app/deals/{deal_id}"
                 style="display:inline-block;background:#3b82f6;color:#fff;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600">
                View Full Memo →
              </a>
              <p style="color:#9ca3af;font-size:12px;margin-top:24px">InsidersDen · AI-powered VC due diligence</p>
            </div>
            """,
        })
    except Exception as e:
        print(f"[email] Failed to send notification: {e}")

app = FastAPI(title="VC Due Diligence Agent API", version="1.0.0")

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

# In-memory progress store: job_id → list of progress messages
_progress_store: Dict[str, list] = {}
_result_store: Dict[str, object] = {}


@app.on_event("startup")
def startup():
    init_db()


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}


# ── Thesis ────────────────────────────────────────────────────────────────────

@app.get("/api/thesis")
def get_thesis():
    if THESIS_TEXT_PATH.exists():
        text = THESIS_TEXT_PATH.read_text().strip()
        placeholder = text.startswith("Paste your fund") or not text
        return {"text": "" if placeholder else text}
    return {"text": ""}


@app.post("/api/thesis")
async def save_thesis(payload: dict):
    text = payload.get("text", "").strip()
    THESIS_TEXT_PATH.write_text(text)
    return {"status": "saved"}


@app.post("/api/thesis/upload")
async def upload_thesis_file(file: UploadFile = File(...)):
    """Parse a PDF or Excel file and return extracted text for the thesis."""
    import io
    suffix = Path(file.filename).suffix.lower()
    content = await file.read()

    if suffix == ".pdf":
        import pdfplumber
        text_parts = []
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text and text.strip():
                    text_parts.append(text.strip())
        thesis_text = "\n\n".join(text_parts)

    elif suffix in (".xlsx", ".xls"):
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        text_parts = []
        for sheet in wb.worksheets:
            text_parts.append(f"=== {sheet.title} ===")
            for row in sheet.iter_rows(values_only=True):
                row_vals = [str(cell).strip() if cell is not None else "" for cell in row]
                if any(v for v in row_vals):
                    text_parts.append("  |  ".join(row_vals))
        thesis_text = "\n".join(text_parts)

    else:
        raise HTTPException(status_code=400, detail="Only PDF and Excel (.xlsx) files supported.")

    if not thesis_text.strip():
        raise HTTPException(status_code=400, detail="Could not extract any text from the file.")

    return {"text": thesis_text}


# ── Notify Email ─────────────────────────────────────────────────────────────

@app.get("/api/notify-email")
def get_notify_email():
    return {"email": _get_notify_email()}


@app.post("/api/notify-email")
async def save_notify_email(payload: dict):
    email = payload.get("email", "").strip()
    NOTIFY_EMAIL_PATH.parent.mkdir(exist_ok=True)
    NOTIFY_EMAIL_PATH.write_text(email)
    return {"status": "saved"}


# ── Deals ─────────────────────────────────────────────────────────────────────

@app.get("/api/deals")
def list_deals():
    deals = get_all_deals()
    # Return lightweight list (no full JSON blobs)
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
        }
        for d in deals
    ]


@app.get("/api/deals/{deal_id}")
def get_deal_detail(deal_id: str):
    deal = get_deal(deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    # Parse JSON blobs back to dicts
    for key in ("claims_json", "fact_json", "thesis_json", "memo_json", "search_logs", "slide_texts", "errors_json"):
        val = deal.get(key)
        if val:
            try:
                deal[key] = json.loads(val)
            except Exception:
                pass
    return deal


@app.delete("/api/deals/{deal_id}")
def remove_deal(deal_id: str):
    delete_deal(deal_id)
    return {"status": "deleted"}


# ── Analysis ──────────────────────────────────────────────────────────────────

def _load_thesis() -> str:
    if THESIS_TEXT_PATH.exists():
        t = THESIS_TEXT_PATH.read_text().strip()
        if t and not t.startswith("Paste your fund"):
            return t
    return ""


def _run_pipeline_sync(job_id: str, mode: str, **kwargs):
    """Run pipeline in thread, pushing progress to _progress_store."""
    from pipeline import (
        run_pipeline,
        run_pipeline_images,
        run_pipeline_pptx,
        run_pipeline_url,
    )

    _progress_store[job_id] = []

    def on_progress(msg: str):
        _progress_store[job_id].append(msg)

    thesis_text = _load_thesis()
    try:
        if mode == "pdf":
            result = run_pipeline(kwargs["path"], thesis_text, on_progress)
        elif mode == "pptx":
            result = run_pipeline_pptx(kwargs["path"], thesis_text, on_progress)
        elif mode == "url":
            result = run_pipeline_url(kwargs["url"], thesis_text, on_progress)
        elif mode == "images":
            result = run_pipeline_images(kwargs["image_bytes"], kwargs["media_types"], thesis_text, on_progress)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        deal_id = save_deal(job_id, kwargs.get("deck_name", "unknown"), result, file_hash=kwargs.get("file_hash"))
        _result_store[job_id] = {"status": "done", "deal_id": job_id}
        _progress_store[job_id].append("__DONE__")
        # Send email notification
        if result.thesis_result:
            _send_notification_email(
                company=result.claims.startup_name if result.claims else kwargs.get("deck_name", "Unknown"),
                fit_pct=result.thesis_result.overall_fit,
                action=result.thesis_result.action,
                deal_id=job_id,
            )
    except Exception as e:
        _result_store[job_id] = {"status": "error", "error": str(e)}
        _progress_store[job_id].append(f"__ERROR__{e}")


@app.post("/api/analyze/file")
async def analyze_file(file: UploadFile = File(...)):
    import hashlib
    import concurrent.futures

    if not _load_thesis():
        raise HTTPException(status_code=400, detail="No thesis set. Save your fund thesis first.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".pdf", ".pptx"):
        raise HTTPException(status_code=400, detail="Only PDF and PPTX files supported.")

    content = await file.read()

    # ── Deduplication: same file = same result ────────────────────────────────
    file_hash = hashlib.md5(content).hexdigest()
    existing = get_deal_by_hash(file_hash)
    if existing:
        # Return existing deal immediately — no re-run
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
        _run_pipeline_sync(job_id, mode, path=tmp_path, deck_name=deck_name, file_hash=file_hash)
        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    loop.run_in_executor(executor, _run)
    return {"job_id": job_id}


@app.post("/api/analyze/url")
async def analyze_url(payload: dict):
    if not _load_thesis():
        raise HTTPException(status_code=400, detail="No thesis set.")

    url = payload.get("url", "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    job_id = str(uuid.uuid4())
    deck_name = url.split("/")[-1].replace(".pdf", "") or "url-deck"

    import concurrent.futures
    loop = asyncio.get_event_loop()
    executor = concurrent.futures.ThreadPoolExecutor()

    def _run():
        _run_pipeline_sync(job_id, "url", url=url, deck_name=deck_name)

    loop.run_in_executor(executor, _run)
    return {"job_id": job_id}


@app.get("/api/analyze/progress/{job_id}")
async def stream_progress(job_id: str):
    """Server-Sent Events stream for live pipeline progress."""

    async def event_generator():
        seen = 0
        max_wait = 300  # 5 min timeout
        waited = 0

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
