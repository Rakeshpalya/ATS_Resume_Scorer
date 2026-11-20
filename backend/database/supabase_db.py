import logging
from typing import List, Dict, Any, Optional
import httpx
from fastapi import HTTPException

from backend.core.config import settings
from backend.models.schemas import AnalysisResult, AnalysisHistorySummary

logger = logging.getLogger(__name__)

class SupabaseDBClient:
    def __init__(self):
        self.supabase_url = settings.SUPABASE_URL.rstrip("/") if settings.SUPABASE_URL else ""
        self.anon_key = settings.SUPABASE_ANON_KEY
        # In-memory store fallback for offline/demo use when Supabase is not configured
        self._in_memory_analyses: Dict[str, List[Dict[str, Any]]] = {}

    def _get_headers(self, user_token: Optional[str] = None) -> Dict[str, str]:
        headers = {
            "apikey": self.anon_key,
            "Content-Type": "application/json",
            "Prefer": "return=representation"
        }
        if user_token:
            headers["Authorization"] = f"Bearer {user_token}"
        elif self.anon_key:
            headers["Authorization"] = f"Bearer {self.anon_key}"
        return headers

    async def save_analysis(
        self,
        user_id: str,
        user_token: Optional[str],
        analysis: AnalysisResult
    ) -> Dict[str, Any]:
        """Saves an analysis record to Supabase with RLS forwarding user_token."""
        # Calculate keyword match percentage and missing keywords
        kw_match = 0.0
        missing_kw: List[str] = []
        if analysis.jd_comparison:
            kw_match = analysis.jd_comparison.match_percentage
            missing_kw = analysis.jd_comparison.missing_keywords

        record = {
            "id": analysis.id,
            "user_id": user_id,
            "filename": analysis.filename,
            "ats_score": analysis.scores.overall_score,
            "keyword_match": kw_match,
            "missing_keywords": missing_kw,
            "created_at": analysis.created_at,
            "analysis_result": analysis.model_dump()
        }

        if not self.supabase_url or not self.anon_key:
            # Fallback in-memory
            if user_id not in self._in_memory_analyses:
                self._in_memory_analyses[user_id] = []
            self._in_memory_analyses[user_id].insert(0, record)
            return record

        url = f"{self.supabase_url}/rest/v1/analyses"
        headers = self._get_headers(user_token)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, json=record)
            if resp.status_code in [200, 201]:
                data = resp.json()
                return data[0] if isinstance(data, list) and data else record
            else:
                error_body = resp.text
                logger.error(f"Supabase save error ({resp.status_code}): {error_body}")
                if "PGRST204" in error_body or "PGRST205" in error_body:
                    raise HTTPException(
                        status_code=500,
                        detail="Supabase schema mismatch: Please ensure the 'analyses' table migration has been applied."
                    )
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Supabase database error: {error_body}"
                )

    async def get_user_analyses(
        self,
        user_id: str,
        user_token: Optional[str]
    ) -> List[AnalysisHistorySummary]:
        """Fetches history of past analyses for the authenticated user."""
        if not self.supabase_url or not self.anon_key:
            records = self._in_memory_analyses.get(user_id, [])
            return [
                AnalysisHistorySummary(
                    id=str(r["id"]),
                    filename=r["filename"],
                    ats_score=float(r["ats_score"]),
                    keyword_match=float(r["keyword_match"]),
                    missing_keywords=r.get("missing_keywords", []),
                    created_at=str(r["created_at"])
                )
                for r in records
            ]

        url = f"{self.supabase_url}/rest/v1/analyses"
        headers = self._get_headers(user_token)
        params = {
            "select": "id,filename,ats_score,keyword_match,missing_keywords,created_at",
            "order": "created_at.desc"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                return [
                    AnalysisHistorySummary(
                        id=str(r["id"]),
                        filename=r["filename"],
                        ats_score=float(r["ats_score"]),
                        keyword_match=float(r["keyword_match"]),
                        missing_keywords=r.get("missing_keywords", []),
                        created_at=str(r["created_at"])
                    )
                    for r in data
                ]
            else:
                error_body = resp.text
                if "PGRST204" in error_body or "PGRST205" in error_body:
                    raise HTTPException(
                        status_code=500,
                        detail="Supabase schema mismatch: 'analyses' table not found."
                    )
                raise HTTPException(
                    status_code=resp.status_code,
                    detail=f"Supabase fetch error: {error_body}"
                )

    async def get_analysis_by_id(
        self,
        analysis_id: str,
        user_id: str,
        user_token: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Fetches full analysis result by ID."""
        if not self.supabase_url or not self.anon_key:
            records = self._in_memory_analyses.get(user_id, [])
            for r in records:
                if str(r["id"]) == analysis_id:
                    return r["analysis_result"]
            return None

        url = f"{self.supabase_url}/rest/v1/analyses"
        headers = self._get_headers(user_token)
        params = {
            "id": f"eq.{analysis_id}",
            "select": "analysis_result"
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers, params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]["analysis_result"]
                return None
            else:
                raise HTTPException(status_code=resp.status_code, detail=resp.text)

    async def delete_analysis(
        self,
        analysis_id: str,
        user_id: str,
        user_token: Optional[str]
    ) -> bool:
        """Deletes an analysis record for the authenticated user."""
        if not self.supabase_url or not self.anon_key:
            if user_id in self._in_memory_analyses:
                self._in_memory_analyses[user_id] = [
                    r for r in self._in_memory_analyses[user_id] if str(r["id"]) != analysis_id
                ]
            return True

        url = f"{self.supabase_url}/rest/v1/analyses"
        headers = self._get_headers(user_token)
        params = {"id": f"eq.{analysis_id}"}

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.delete(url, headers=headers, params=params)
            return resp.status_code in [200, 204]

supabase_db = SupabaseDBClient()
