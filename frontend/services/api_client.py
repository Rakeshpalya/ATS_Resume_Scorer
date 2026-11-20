import os
import requests
from typing import Dict, Any, List, Optional, Tuple

DEFAULT_API_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

class APIClient:
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or DEFAULT_API_URL).rstrip("/")

    def check_health(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/health", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def analyze_resume(
        self,
        file_bytes: bytes,
        filename: str,
        jd_text: Optional[str] = None,
        jd_bytes: Optional[bytes] = None,
        jd_filename: Optional[str] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/analyze"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        files = {
            "resume_file": (filename, file_bytes, "application/octet-stream")
        }
        data = {}
        if jd_text:
            data["jd_text"] = jd_text
        if jd_bytes and jd_filename:
            files["jd_file"] = (jd_filename, jd_bytes, "text/plain")

        resp = requests.post(url, headers=headers, files=files, data=data, timeout=60.0)
        if resp.status_code != 200:
            error_msg = resp.text
            try:
                error_msg = resp.json().get("detail", error_msg)
            except Exception:
                pass
            raise RuntimeError(f"API Error ({resp.status_code}): {error_msg}")

        return resp.json()

    def get_history(self, token: str) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/api/history"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=10.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch history: {resp.text}")
        return resp.json()

    def get_analysis(self, analysis_id: str, token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/analyses/{analysis_id}"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=10.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to fetch analysis: {resp.text}")
        return resp.json()

    def delete_analysis(self, analysis_id: str, token: str) -> bool:
        url = f"{self.base_url}/api/analyses/{analysis_id}"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.delete(url, headers=headers, timeout=10.0)
        return resp.status_code in [200, 204]

    def export_pdf(self, analysis_data: Dict[str, Any]) -> Tuple[bytes, str]:
        url = f"{self.base_url}/api/export-pdf"
        resp = requests.post(url, json=analysis_data, timeout=30.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to export report: {resp.text}")
        mime_type = resp.headers.get("Content-Type", "application/pdf")
        return resp.content, mime_type

    def get_analysis_pdf(self, analysis_id: str, token: str) -> Tuple[bytes, str]:
        url = f"{self.base_url}/api/analyses/{analysis_id}/pdf"
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, timeout=30.0)
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download report: {resp.text}")
        mime_type = resp.headers.get("Content-Type", "application/pdf")
        return resp.content, mime_type

api_client = APIClient()
