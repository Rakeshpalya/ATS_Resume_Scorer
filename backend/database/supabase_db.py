import logging
import httpx
import json
from datetime import datetime, timezone
from typing import List, Dict

logger = logging.getLogger('ats_resume_scorer')

from backend.core.config import SUPABASE_URL, SUPABASE_ANON_KEY

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
            if data and len(data) > 0:
                inserted_id = data[0].get("id")
                if inserted_id is None:
                    raise RuntimeError("Supabase insert response did not include an analysis ID")
                return str(inserted_id)
            raise RuntimeError("Supabase insert response did not include the inserted analysis")
    except Exception as exc:
        logger.error("Failed to save analysis to Supabase (%s)", type(exc).__name__)
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
            
            results = []
            for doc in docs:
                results.append({
                    "id": str(doc.get("id")),
                    "filename": doc.get("filename", "resume"),
                    "resume_name": doc.get("filename", "resume"),
                    "job_title": "Software Engineer",
                    "ats_score": doc.get("ats_score", 0),
                    "keyword_match": doc.get("keyword_match", 0),
                    "missing_keywords": doc.get("missing_keywords", []),
                    "date": doc.get("created_at", ""),
                    "created_at": doc.get("created_at", ""),
                    "analysis_result": doc.get("analysis_result", {}),
                })
            return results
    except Exception as exc:
        logger.error("Failed to fetch history from Supabase (%s)", type(exc).__name__)
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
        logger.error("Failed to delete analysis from Supabase (%s)", type(exc).__name__)
        raise RuntimeError("Could not delete analysis from Supabase") from exc
