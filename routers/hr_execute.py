import base64
import io
import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from database import get_db_connection
from orchestration import (
    build_n8n_api_headers,
    create_execution_log,
    get_execution_log,
    log_exception,
    merge_execution_log_output_summary,
    post_with_retry,
    update_execution_log,
    upsert_execution_log,
)


router = APIRouter()


class DocumentExtractRequest(BaseModel):
    request_id: UUID
    workflow_type: str
    content_base64: str
    filename: str
    mime_type: str
    language: Optional[str] = "eng"


class OCRExtractRequest(DocumentExtractRequest):
    pass


class RankCandidatesRequest(BaseModel):
    request_id: UUID
    workflow_type: str
    extracted_text: str
    criteria: Optional[str] = ""
    ranking_logic: Optional[str] = "weighted_scoring"
    candidates: Optional[list[Any]] = Field(default_factory=list)


class ShortlistRequest(BaseModel):
    request_id: UUID
    ranked_candidates: list[dict]
    top_k: int
    timezone: str
    working_hours_start: str
    working_hours_end: str
    slot_duration_minutes: int
    slot_gap_minutes: int
    use_calendar_freebusy: bool = True
    freebusy_lookahead_days: int = 14
    calendar_account: str = "primary"


class ExecutionCallbackRequest(BaseModel):
    request_id: UUID
    workflow_type: str
    status: str
    results: list[Any] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class HRExecuteRequest(BaseModel):
    user_email: str
    document_source: str
    file_base64: Optional[str] = None
    filename: Optional[str] = None
    mime_type: Optional[str] = "application/pdf"
    criteria: Optional[str] = ""
    top_k: int = 5


class SendEmailRequest(BaseModel):
    request_id: UUID
    candidate_email: str = ""
    candidate_name: str = ""
    subject: str = ""
    body: str = ""
    step_id: str = "send_emails"
    user_email: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class CreateCalendarEventRequest(BaseModel):
    request_id: UUID
    candidate_name: str = ""
    candidate_email: str = ""
    start_time: str
    end_time: str
    step_id: str = "schedule_interviews"
    user_email: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


def _callback_base_url() -> str:
    return os.getenv("FASTAPI_CALLBACK_URL", os.getenv("FASTAPI_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")


def _extract_text_from_pdf_bytes(bts: bytes) -> str:
    try:
        import pdfplumber

        out = []
        with pdfplumber.open(io.BytesIO(bts)) as pdf:
            for page in pdf.pages:
                try:
                    page_text = page.extract_text()
                except Exception:
                    page_text = None
                if page_text:
                    out.append(page_text)
        return "\n".join(out).strip()
    except Exception:
        return ""


def _extract_text_from_docx_bytes(bts: bytes) -> str:
    try:
        from docx import Document as DocxDocument

        doc = DocxDocument(io.BytesIO(bts))
        parts = [paragraph.text for paragraph in doc.paragraphs if paragraph.text]
        return "\n".join(parts).strip()
    except Exception:
        return ""


def _attempt_groq_rank(extracted_text: str, criteria: str):
    system_prompt = (
        "You are a recruitment assistant. Extract and score this candidate from their resume text. "
        "Return ONLY valid JSON with these fields: candidate_name, candidate_email, phone, skills, experience_years, education, current_role, score, summary"
    )
    try:
        import groq

        try:
            if hasattr(groq, "Client"):
                client = groq.Client()
                if hasattr(client, "chat") and hasattr(client.chat, "completions"):
                    response = client.chat.completions.create(
                        model="llama3-70b-8192",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": extracted_text},
                        ],
                    )
                    content = None
                    if hasattr(response, "choices") and response.choices:
                        choice = response.choices[0]
                        content = getattr(choice, "message", None)
                        if content:
                            content = getattr(content, "content", None) or str(content)
                    if not content:
                        content = str(response)
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        match = re.search(r"\{.*\}", content, re.DOTALL)
                        if match:
                            return json.loads(match.group())
                        return {
                            "candidate_name": "Unknown",
                            "candidate_email": "",
                            "skills": [],
                            "experience_years": 0,
                            "score": 0,
                            "summary": "Could not parse resume",
                        }
        except Exception:
            pass
    except Exception:
        pass
    return None


def _heuristic_rank(extracted_text: str, criteria: str):
    name_match = re.search(r"([A-Z][a-z]+\s+[A-Z][a-z]+)", extracted_text)
    email_match = re.search(r"[\w\.-]+@[\w\.-]+", extracted_text)
    phone_match = re.search(r"(\+?\d[\d\-\s]{7,}\d)", extracted_text)
    years_match = re.search(r"(\d+)\s+years", extracted_text)
    skills = []
    for word in re.findall(r"\w+", criteria or ""):
        if re.search(rf"\b{re.escape(word)}\b", extracted_text, flags=re.I):
            skills.append(word)

    experience_years = int(years_match.group(1)) if years_match else 0
    score = 50 + min(50, experience_years * 5 + (10 * len(skills)))
    return {
        "candidate_name": name_match.group(1) if name_match else "Unknown",
        "candidate_email": email_match.group(0) if email_match else "",
        "phone": phone_match.group(0) if phone_match else "",
        "skills": skills,
        "experience_years": experience_years,
        "education": "",
        "current_role": "",
        "score": int(max(0, min(100, score))),
        "summary": (extracted_text[:200].replace("\n", " ") + "...")[:200],
    }


def _default_candidate(summary: str = "Could not parse resume") -> dict[str, Any]:
    return {
        "candidate_name": "Unknown",
        "candidate_email": "",
        "phone": "",
        "skills": [],
        "experience_years": 0,
        "education": "",
        "current_role": "",
        "score": 0,
        "summary": summary,
    }


def _merge_step_output(conn, request_id: str, step_key: str, payload: Any, *, status: str | None = None, input_payload: Any = None) -> int:
    return merge_execution_log_output_summary(
        conn,
        request_id,
        {
            "steps": {
                step_key: payload,
            }
        },
        status=status,
        input_payload=input_payload,
    )


def _reuse_or_create_request(request_id: str | None, user_email: str | None, module: str, payload: Any, status: str) -> str:
    conn = get_db_connection()
    try:
        if request_id:
            if get_execution_log(conn, request_id):
                _merge_step_output(
                    conn,
                    request_id,
                    module,
                    payload,
                    status=status,
                    input_payload=payload,
                )
                return request_id
            return upsert_execution_log(
                conn,
                request_id,
                user_email=user_email or "system",
                module=module,
                input_payload=payload,
                status=status,
                output_summary={"steps": {module: payload}},
            )
        return create_execution_log(conn, user_email=user_email or "system", module=module, input_payload=payload, status=status, output_summary={"steps": {module: payload}})
    finally:
        conn.close()


def _decode_text_payload(file_base64: str | None, mime_type: str | None, filename: str | None) -> str:
    if not file_base64:
        return ""

    try:
        raw_bytes = base64.b64decode(file_base64)
    except Exception:
        return ""

    normalized_mime = (mime_type or "").lower()
    normalized_filename = (filename or "").lower()
    if "pdf" in normalized_mime or normalized_filename.endswith(".pdf"):
        return _extract_text_from_pdf_bytes(raw_bytes)
    if "word" in normalized_mime or normalized_filename.endswith(".docx"):
        return _extract_text_from_docx_bytes(raw_bytes)
    try:
        return raw_bytes.decode("utf-8")
    except Exception:
        return ""


@router.post("/document/extract")
async def document_extract(req: DocumentExtractRequest):
    try:
        document_bytes = base64.b64decode(req.content_base64)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid base64: {exc}") from exc

    text = ""
    mime_type = (req.mime_type or "").lower()
    filename = (req.filename or "").lower()

    if "pdf" in mime_type or filename.endswith(".pdf"):
        text = _extract_text_from_pdf_bytes(document_bytes)
    elif filename.endswith(".docx") or "word" in mime_type:
        text = _extract_text_from_docx_bytes(document_bytes)
    else:
        try:
            text = document_bytes.decode("utf-8")
        except Exception:
            text = ""

    return {"extracted_text": text, "request_id": str(req.request_id), "step_id": "extract_text", "status": "completed"}


@router.post("/ocr/extract")
async def ocr_extract(req: OCRExtractRequest):
    ocr_api_key = os.getenv("OCR_SPACE_API_KEY")
    if not ocr_api_key:
        raise HTTPException(status_code=500, detail="OCR_SPACE_API_KEY not configured")

    try:
        base64_payload = f"data:{req.mime_type};base64,{req.content_base64}"
        data = {"apikey": ocr_api_key, "base64Image": base64_payload, "OCREngine": 2}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post("https://api.ocr.space/parse/image", data=data)
            response.raise_for_status()
        parsed_response = response.json()
        parsed_text = ""
        if parsed_response.get("ParsedResults"):
            parsed_text = parsed_response["ParsedResults"][0].get("ParsedText", "")
    except Exception as exc:
        log_exception("OCR provider error", request_id=req.request_id, filename=req.filename)
        raise HTTPException(status_code=502, detail=f"OCR provider error: {exc}") from exc

    return {"extracted_text": parsed_text, "request_id": str(req.request_id), "step_id": "extract_text", "status": "completed"}


@router.post("/rank/candidates")
async def rank_candidates(req: RankCandidatesRequest):
    groq_out = _attempt_groq_rank(req.extracted_text, req.criteria)
    ranked_list = groq_out if isinstance(groq_out, list) else ([groq_out] if groq_out else [_heuristic_rank(req.extracted_text, req.criteria)])
    ranked_list = [candidate for candidate in ranked_list if candidate] or [_default_candidate()]

    conn = get_db_connection()
    try:
        _merge_step_output(
            conn,
            str(req.request_id),
            "rank_candidates",
            {
                "step_id": "rank_candidates",
                "ranked_candidates": ranked_list,
                "status": "completed",
            },
            status="ranked",
        )
    finally:
        conn.close()

    return {
        "ranked_candidates": ranked_list or [],
        "request_id": str(req.request_id),
        "step_id": "rank_candidates",
        "status": "completed",
    }


@router.post("/shortlist/candidates")
async def shortlist_candidates(req: ShortlistRequest):
    import pytz

    ranked_candidates = req.ranked_candidates or []
    ranked = sorted(ranked_candidates, key=lambda item: item.get("score", 0), reverse=True)
    top_candidates = ranked[: req.top_k]
    timezone = pytz.timezone(req.timezone)
    now = datetime.now(timezone)
    slots = []

    working_hours_start = datetime.strptime(req.working_hours_start, "%H:%M").time()
    working_hours_end = datetime.strptime(req.working_hours_end, "%H:%M").time()

    for day_offset in range(req.freebusy_lookahead_days):
        day_date = (now + timedelta(days=day_offset)).date()
        slot_start = timezone.localize(datetime.combine(day_date, working_hours_start))
        slot_end_of_day = timezone.localize(datetime.combine(day_date, working_hours_end))

        while slot_start + timedelta(minutes=req.slot_duration_minutes) <= slot_end_of_day and len(slots) < req.top_k:
            slot_end = slot_start + timedelta(minutes=req.slot_duration_minutes)
            slots.append((slot_start.isoformat(), slot_end.isoformat()))
            slot_start = slot_end + timedelta(minutes=req.slot_gap_minutes)

        if len(slots) >= req.top_k:
            break

    shortlisted_list = []
    for index, candidate in enumerate(top_candidates):
        if index < len(slots):
            interview_start, interview_end = slots[index]
        else:
            interview_start = (now + timedelta(days=1)).isoformat()
            interview_end = (now + timedelta(days=1, minutes=req.slot_duration_minutes)).isoformat()

        shortlisted_list.append(
            {
                "candidate_name": candidate.get("candidate_name"),
                "candidate_email": candidate.get("candidate_email"),
                "score": candidate.get("score", 0),
                "metadata": {
                    "interview_start": interview_start,
                    "interview_end": interview_end,
                    "shortlist_rank": index + 1,
                    "slot_audit": {},
                },
            }
        )
    shortlisted_list = shortlisted_list or []

    conn = get_db_connection()
    try:
        _merge_step_output(
            conn,
            str(req.request_id),
            "shortlist",
            {
                "step_id": "shortlist",
                "shortlisted": shortlisted_list,
                "status": "completed",
            },
            status="shortlisted",
        )
    finally:
        conn.close()

    return {"shortlisted": shortlisted_list, "request_id": str(req.request_id), "step_id": "shortlist", "status": "completed"}


@router.post("/execution-callback")
async def execution_callback(req: ExecutionCallbackRequest):
    conn = get_db_connection()
    results = req.results or []
    metadata = req.metadata or {}
    try:
        user_email = metadata.get("user_email", "system")
        module = req.workflow_type or "workflow"
        request_id = str(req.request_id)
        rowcount = _merge_step_output(
            conn,
            request_id,
            "execution_callback",
            {
                "step_id": "execution_callback",
                "status": req.status,
                "results": results,
                "metadata": metadata,
            },
            status=req.status or "completed",
        )
        if rowcount == 0:
            upsert_execution_log(
                conn,
                request_id,
                user_email=user_email,
                module=module,
                input_payload={"request_id": request_id},
                status=req.status,
                output_summary={
                    "results": results,
                    "metadata": metadata,
                    "steps": {
                        "execution_callback": {
                            "status": req.status,
                            "results": results,
                            "metadata": metadata,
                        }
                    },
                },
            )
    except Exception as exc:
        log_exception("Execution callback persistence failed", request_id=str(req.request_id), workflow_type=req.workflow_type)
        raise HTTPException(status_code=500, detail=f"Execution callback failed: {exc}") from exc
    finally:
        conn.close()

    return {"status": "ok", "request_id": str(req.request_id)}


@router.post("/hr/execute")
async def hr_execute(req: HRExecuteRequest):
    conn = get_db_connection()
    request_id = None
    try:
        input_payload = {
            "user_email": req.user_email,
            "document_source": req.document_source,
            "filename": req.filename,
            "mime_type": req.mime_type,
            "criteria": req.criteria,
            "top_k": req.top_k,
        }
        request_id = create_execution_log(
            conn,
            user_email=req.user_email,
            module="hr",
            input_payload=input_payload,
            status="created",
        )

        n8n_url = os.getenv("N8N_HR_WEBHOOK_URL")
        if not n8n_url:
            error_message = "N8N_HR_WEBHOOK_URL not configured"
            update_execution_log(
                conn,
                request_id,
                status="failed_to_trigger",
                output_summary={"error": error_message, "workflow": "hr_recruitment"},
            )
            return {"request_id": request_id, "status": "failed_to_trigger", "message": error_message}

        extracted_text = _decode_text_payload(req.file_base64, req.mime_type, req.filename)
        body = {
            "request_id": request_id,
            "workflow_type": "hr_recruitment",
            "payload": {
                "user_email": req.user_email,
                "criteria": req.criteria,
                "top_k": req.top_k,
                "email_data": {
                    "subject": req.filename or "Candidate Document",
                    "body": extracted_text or "",
                    "from": req.user_email,
                    "attachments": [],
                },
                "extracted_text": extracted_text or "",
            },
            "callback_url": f"{_callback_base_url()}/api/execution-callback",
            "callback_auth": {},
        }

        merge_execution_log_output_summary(
            conn,
            request_id,
            {
                "workflow": "hr_recruitment",
                "document_source": req.document_source,
                "steps": {},
            },
            status="triggering",
        )

        try:
            response = await post_with_retry(
                n8n_url,
                json_body=body,
                headers=build_n8n_api_headers(),
                timeout=15.0,
                attempts=3,
            )
        except Exception as exc:
            log_exception("Failed to trigger HR execute workflow", request_id=request_id, n8n_url=n8n_url)
            merge_execution_log_output_summary(
                conn,
                request_id,
                {"error": str(exc), "workflow": "hr_recruitment"},
                status="failed_to_trigger",
            )
            return {"request_id": request_id, "status": "failed_to_trigger", "message": str(exc)}

        merge_execution_log_output_summary(
            conn,
            request_id,
            {
                "workflow": "hr_recruitment",
                "n8n_status_code": response.status_code,
                "n8n_response_text": response.text[:500],
            },
            status="running",
        )
        return {"request_id": request_id, "status": "triggered", "message": "HR workflow started"}
    except HTTPException:
        raise
    except Exception as exc:
        log_exception("Unhandled HR execute error", request_id=request_id, user_email=req.user_email)
        if request_id:
            try:
                update_execution_log(conn, request_id, status="failed", output_summary={"error": str(exc)})
            except Exception:
                log_exception("Failed to persist HR execute error", request_id=request_id)
        raise HTTPException(status_code=500, detail=f"HR execute failed for request_id {request_id}") from exc
    finally:
        conn.close()


@router.post("/send-email")
async def send_email(req: SendEmailRequest):
    payload = req.model_dump()
    request_id = _reuse_or_create_request(str(req.request_id), req.user_email, "send_emails", payload, "shortlisted")
    return {"status": "ok", "step_id": "send_emails", "request_id": request_id}


@router.post("/create-calendar-event")
async def create_calendar_event(req: CreateCalendarEventRequest):
    payload = req.model_dump()
    request_id = _reuse_or_create_request(str(req.request_id), req.user_email, "schedule_interviews", payload, "shortlisted")
    return {
        "status": "ok",
        "step_id": "schedule_interviews",
        "event_id": f"evt_{request_id[:8]}",
        "start_time": req.start_time,
        "end_time": req.end_time,
        "request_id": request_id,
    }
