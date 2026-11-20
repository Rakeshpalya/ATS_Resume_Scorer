import io
import os
from typing import Optional, List
from fastapi import (
    APIRouter,
    UploadFile,
    File,
    Form,
    Depends,
    HTTPException,
    Header,
    status
)
from fastapi.responses import StreamingResponse

from backend.core.config import settings
from backend.models.schemas import (
    AnalysisResult,
    AnalysisHistorySummary,
    UserProfile
)
from backend.api.auth import get_current_user, get_optional_current_user
from backend.database.supabase_db import supabase_db
from backend.services.resume_analyzer import resume_analyzer
from backend.services.pdf_export import generate_pdf_report
from backend.utils.file_utils import ALLOWED_EXTENSIONS, MAX_FILE_SIZE

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "ATS Resume Scorer Backend",
        "models": {
            "primary": settings.GROQ_MODEL_PRIMARY,
            "sentence_transformer": settings.SENTENCE_TRANSFORMER_MODEL
        }
    }

@router.post("/analyze", response_model=AnalysisResult)
async def analyze_resume_endpoint(
    resume_file: UploadFile = File(...),
    jd_text: Optional[str] = Form(None),
    jd_file: Optional[UploadFile] = File(None),
    user: Optional[UserProfile] = Depends(get_optional_current_user),
    authorization: Optional[str] = Header(None)
):
    filename = resume_file.filename or "resume.pdf"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Only .pdf and .docx are supported."
        )

    content = await resume_file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum allowed size of 5 MB ({len(content) / (1024 * 1024):.2f} MB)."
        )

    # Resolve JD text from form or uploaded file
    final_jd_text = jd_text or ""
    if jd_file and jd_file.filename:
        jd_bytes = await jd_file.read()
        try:
            final_jd_text = jd_bytes.decode("utf-8", errors="ignore")
        except Exception:
            pass

    try:
        analysis = resume_analyzer.analyze_resume(
            filename=filename,
            content=content,
            jd_text=final_jd_text
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis pipeline error: {str(e)}"
        )

    # If user is authenticated, save record to Supabase
    if user and user.id:
        token = authorization.replace("Bearer ", "").strip() if authorization else None
        try:
            await supabase_db.save_analysis(
                user_id=user.id,
                user_token=token,
                analysis=analysis
            )
        except Exception as e:
            # Do not fail analysis output if saving history encounters an error
            pass

    return analysis

@router.get("/history", response_model=List[AnalysisHistorySummary])
async def get_history_endpoint(
    user: UserProfile = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    return await supabase_db.get_user_analyses(user.id, token)

@router.get("/analyses/{analysis_id}")
async def get_analysis_by_id_endpoint(
    analysis_id: str,
    user: UserProfile = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    result = await supabase_db.get_analysis_by_id(analysis_id, user.id, token)
    if not result:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    return result

@router.delete("/analyses/{analysis_id}")
async def delete_analysis_endpoint(
    analysis_id: str,
    user: UserProfile = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    success = await supabase_db.delete_analysis(analysis_id, user.id, token)
    if not success:
        raise HTTPException(status_code=404, detail="Analysis not found or could not be deleted.")
    return {"success": True, "deleted_id": analysis_id}

@router.post("/export-pdf")
async def export_pdf_endpoint(analysis: AnalysisResult):
    file_bytes, mime_type = generate_pdf_report(analysis)
    ext = "pdf" if mime_type == "application/pdf" else "txt"
    out_filename = f"ATS_Report_{analysis.id or 'analysis'}.{ext}"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{out_filename}"'}
    )

@router.get("/analyses/{analysis_id}/pdf")
async def get_analysis_pdf_endpoint(
    analysis_id: str,
    user: UserProfile = Depends(get_current_user),
    authorization: Optional[str] = Header(None)
):
    token = authorization.replace("Bearer ", "").strip() if authorization else None
    result_data = await supabase_db.get_analysis_by_id(analysis_id, user.id, token)
    if not result_data:
        raise HTTPException(status_code=404, detail="Analysis record not found.")

    analysis = AnalysisResult(**result_data)
    file_bytes, mime_type = generate_pdf_report(analysis)
    ext = "pdf" if mime_type == "application/pdf" else "txt"
    out_filename = f"ATS_Report_{analysis_id}.{ext}"

    return StreamingResponse(
        io.BytesIO(file_bytes),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{out_filename}"'}
    )
