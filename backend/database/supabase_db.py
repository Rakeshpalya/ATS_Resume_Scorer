import logging
import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict

logger = logging.getLogger('ats_resume_scorer')

from backend.core.config import SUPABASE_URL, SUPABASE_ANON_KEY


class SupabaseDatabaseError(RuntimeError):
    def __init__(self, category: str, status_code: int, user_message: str):
        super().__init__(user_message)
        self.category = category
        self.status_code = status_code
        self.user_message = user_message


_ANALYSES_COLUMNS = {
    "id",
    "user_id",
    "filename",
    "ats_score",
    "keyword_match",
    "missing_keywords",
    "created_at",
    "analysis_result",
}


def _get_headers(access_token: str) -> dict[str, str]:
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase database access is not configured")
    if not access_token:
        raise RuntimeError("An authenticated access token is required for database access")
    return {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }


def _postgrest_error_code(exc: httpx.HTTPStatusError) -> str | None:
    try:
        body = exc.response.json()
    except ValueError:
        return None
    code = body.get("code") if isinstance(body, dict) else None
    return code if isinstance(code, str) else None


def _raise_database_error(operation: str, exc: Exception) -> None:
    if isinstance(exc, httpx.HTTPStatusError):
        status_code = exc.response.status_code
        error_code = _postgrest_error_code(exc)
        logger.error(
            "Supabase %s failed (HTTP %s, PostgREST code %s)",
            operation,
            status_code,
            error_code or "unavailable",
        )
        if error_code in {"PGRST205", "42P01"}:
            raise SupabaseDatabaseError(
                "missing_table",
                503,
                "Analysis history is unavailable because its database table is missing. Apply the analyses migration.",
            ) from exc
        if error_code in {"PGRST204", "42703"}:
            raise SupabaseDatabaseError(
                "schema_mismatch",
                503,
                "Analysis history is unavailable because the database schema is outdated. Check the analyses migration.",
            ) from exc
        if status_code == 401:
            raise SupabaseDatabaseError(
                "unauthorized",
                401,
                "Your session is no longer authorized for analysis history. Sign in again.",
            ) from exc
        if status_code == 403:
            raise SupabaseDatabaseError(
                "forbidden",
                403,
                "Your account is not permitted to access analysis history.",
            ) from exc
        raise SupabaseDatabaseError(
            "database_error",
            503,
            "Analysis history is temporarily unavailable. Please try again later.",
        ) from exc

    if isinstance(exc, httpx.RequestError):
        logger.error("Supabase %s request failed (%s)", operation, type(exc).__name__)
        raise SupabaseDatabaseError(
            "network_error",
            503,
            "Analysis history service could not be reached. Please try again later.",
        ) from exc

    logger.error("Supabase %s response was invalid (%s)", operation, type(exc).__name__)
    raise SupabaseDatabaseError(
        "invalid_response",
        502,
        "Analysis history service returned an invalid response.",
    ) from exc


def _validate_history_rows(docs: object, user_id: str) -> List[Dict]:
    if not isinstance(docs, list):
        raise SupabaseDatabaseError(
            "invalid_response",
            502,
            "Analysis history service returned an invalid response.",
        )

    results = []
    for doc in docs:
        if not isinstance(doc, dict) or not _ANALYSES_COLUMNS.issubset(doc):
            raise SupabaseDatabaseError(
                "schema_mismatch",
                503,
                "Analysis history is unavailable because the database schema is outdated. Check the analyses migration.",
            )
        if doc["user_id"] != user_id:
            logger.error("Supabase returned a history row outside the requested user scope")
            raise SupabaseDatabaseError(
                "ownership_violation",
                502,
                "Analysis history could not be safely verified.",
            )
        if (
            not isinstance(doc["analysis_result"], dict)
            or not isinstance(doc["missing_keywords"], list)
        ):
            raise SupabaseDatabaseError(
                "schema_mismatch",
                503,
                "Analysis history is unavailable because stored records do not match the expected schema.",
            )
        results.append({
            "id": str(doc["id"]),
            "filename": doc["filename"],
            "resume_name": doc["filename"],
            "job_title": "Software Engineer",
            "ats_score": doc["ats_score"],
            "keyword_match": doc["keyword_match"],
            "missing_keywords": doc["missing_keywords"],
            "date": doc["created_at"],
            "created_at": doc["created_at"],
            "analysis_result": doc["analysis_result"],
        })
    return results


async def save_analysis(
    user_id: str,
    filename: str,
    analysis_result: Dict,
    access_token: str,
) -> str:
    headers = _get_headers(access_token)

    def _json_default(o):
        if hasattr(o, 'model_dump'):
            return o.model_dump()
        return str(o)
    serializable_result = json.loads(json.dumps(analysis_result, default=_json_default))

    doc = {
        "user_id": user_id,
        "filename": filename,
        "ats_score": serializable_result.get("ats_score", 0),
        "keyword_match": serializable_result.get("keyword_match", 0),
        "missing_keywords": serializable_result.get("missing_keywords", []),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "analysis_result": serializable_result,
    }

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=doc)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list) and data:
                if not isinstance(data[0], dict) or "id" not in data[0]:
                    raise ValueError("Supabase insert response omitted the analysis ID")
                inserted_id = data[0].get("id")
                if inserted_id is None:
                    raise RuntimeError("Supabase insert response did not include an analysis ID")
                return str(inserted_id)
            raise ValueError("Supabase insert response did not include the inserted analysis")
    except Exception as exc:
        _raise_database_error("analysis insert", exc)
        raise RuntimeError("Could not save analysis to Supabase") from exc

async def get_user_history(user_id: str, access_token: str) -> List[Dict]:
    headers = _get_headers(access_token)

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url, 
                headers=headers, 
                params={
                    "user_id": f"eq.{user_id}",
                    "order": "created_at.desc"
                }
            )
            response.raise_for_status()
            docs = response.json()
            return _validate_history_rows(docs, user_id)
    except Exception as exc:
        if isinstance(exc, SupabaseDatabaseError):
            raise
        _raise_database_error("history query", exc)
        raise RuntimeError("Could not fetch history from Supabase") from exc

async def delete_analysis(
    analysis_id: str,
    user_id: str,
    access_token: str,
) -> bool:
    headers = _get_headers(access_token)

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/analyses"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                url, 
                headers=headers, 
                params={
                    "id": f"eq.{analysis_id}",
                    "user_id": f"eq.{user_id}"
                }
            )
            response.raise_for_status()
            deleted = response.json()
            return bool(deleted)
    except Exception as exc:
        _raise_database_error("analysis delete", exc)
        raise RuntimeError("Could not delete analysis from Supabase") from exc
