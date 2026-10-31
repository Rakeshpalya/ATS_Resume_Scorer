import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile

from backend.api.auth import AuthenticatedUser, get_authenticated_user, get_current_user
from backend.core.config import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from backend.models.schemas import AnalysisResponse, ComponentScores, JDComparison, SkillValidationDetails
from backend.utils.file_utils import (
    get_default_grammar_results,
    get_default_location_results,
    get_default_skill_validation_results,
)

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['Analysis'])

def _clean(text: str) -> str:
    for prefix in ('✅', '🌟', '❌', '⚠️', '📝', '🔴', '🟡', '🟢', '🟠', '👍'):
        text = text.lstrip(prefix)
    return text.strip()

@router.post('/analyze-resume', response_model=AnalysisResponse)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(..., description='Resume file — PDF or DOCX, max 5 MB'),
    job_description: str = Form('', description='Job description text (optional)'),
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    warnings: List[str] = []
    user_id = authenticated_user.user_id

    nlp      = request.app.state.nlp
    embedder = request.app.state.embedder

    from backend.services.resume_parser import (
        FileParsingError,
        FileValidationError,
        parse_resume_file,
    )

    try:
        file_bytes = await resume.read(MAX_FILE_SIZE_BYTES + 1)
        if len(file_bytes) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f'Resume exceeds the maximum upload size of {MAX_FILE_SIZE_MB} MB.',
            )
        filename   = resume.filename or 'resume'
        resume_text, _metadata = parse_resume_file(file_bytes, filename)
        logger.info("Resume parsed: %s characters extracted", len(resume_text))
    except HTTPException:
        raise
    except (FileParsingError, FileValidationError) as exc:
        logger.exception("Resume processing rejected (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        logger.exception("Resume processing failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=422,
            detail='Could not read or parse the resume. Upload a valid PDF or DOCX file.',
        ) from exc

    #Full Analysis Pipeline 
    try:
        from backend.services.groq_parser import GroqServiceError
        from backend.services.resume_analyzer import analyze_full_resume
        
        result = analyze_full_resume(
            resume_text=resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description
        )
    except GroqServiceError as exc:
        logger.exception("Resume analysis provider failure (%s)", exc.category)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.user_message,
        ) from exc
    except Exception as exc:
        logger.exception("Full analysis pipeline failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=502,
            detail='Resume analysis failed while processing the document. Please retry.',
        ) from exc

    from backend.models.schemas import ComponentScores

    #Extract jd_comparison details
    jd_comparison_result = None
    if result.get('jd_comparison'):
        jd_comparison_result = JDComparison(
            match_percentage=round(float(result['jd_comparison'].get('match_percentage', 0.0)), 1),
            semantic_similarity=round(float(result['jd_comparison'].get('semantic_similarity', 0.0)), 3),
            matched_keywords=result['jd_comparison'].get('matched_keywords', [])[:20],
            missing_keywords=result['jd_comparison'].get('missing_keywords', [])[:15],
            skills_gap=result['jd_comparison'].get('skills_gap', [])[:10],
        )

    # Convert detailed_feedback objects from prediction into what schema expects
    detailed_fb = result.get('detailed_feedback', [])
    

    svd_raw = result.get('skill_validation_details') or {}
    skill_val_details = SkillValidationDetails(
        validated       = svd_raw.get('validated', []),
        unvalidated     = svd_raw.get('unvalidated', []),
        total           = svd_raw.get('total', 0),
        validated_count = svd_raw.get('validated_count', 0),
        validation_pct  = svd_raw.get('validation_pct', 0.0),
    )

    response = AnalysisResponse(
        ATS_score=result['ats_score'],
        component_scores=ComponentScores(**result['component_scores']),
        issues_summary=result['issues_summary'],
        detailed_feedback=detailed_fb,
        jd_match_analysis=jd_comparison_result,
        skill_validation_details=skill_val_details,

        # Retro-compatibility fields
        ats_score=result['ats_score'],
        keyword_match=jd_comparison_result.match_percentage if jd_comparison_result else 0.0,
        missing_keywords=result.get('missing_keywords', []),
        matched_keywords=result.get('matched_keywords', []),
        skills=list(result.get('skills', [])[:20]),
        strengths=result.get('strengths', []),
        critical_issues=result.get('critical_issues', []),
        suggestions=result.get('suggestions', []),
        warnings=warnings,
        jd_comparison=jd_comparison_result,
        interpretation=result.get('interpretation', '')
    )


    try:
        from backend.database.supabase_db import save_analysis
        await save_analysis(
            user_id,
            filename,
            result,
            authenticated_user.access_token,
        )
    except Exception as exc:
        logger.warning("History save failed (%s)", type(exc).__name__)
        warnings.append('Analysis completed, but the result could not be saved to history.')
    response.warnings = warnings

    return response

@router.get('/health')
async def health_check(request: Request):
    """Health check — confirms models are loaded and the API is ready."""
    return {
        'status':          'healthy',
        'nlp_loaded':      request.app.state.nlp is not None,
        'embedder_loaded': request.app.state.embedder is not None,
    }

@router.get('/history')
async def get_history(
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Return the signed-in user's past analyses (identity comes from the JWT)."""
    from backend.database.supabase_db import SupabaseDatabaseError, get_user_history
    try:
        return await get_user_history(
            authenticated_user.user_id,
            authenticated_user.access_token,
        )
    except SupabaseDatabaseError as exc:
        logger.warning("History fetch unavailable (%s)", exc.category)
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.user_message,
        ) from exc
    except Exception as exc:
        logger.exception("History fetch failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail='Could not load analysis history.') from exc


@router.delete('/history/{analysis_id}')
async def delete_history_entry(
    analysis_id: str,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    """Delete one analysis from the signed-in user's history."""
    from backend.database.supabase_db import delete_analysis
    try:
        success = await delete_analysis(
            analysis_id,
            authenticated_user.user_id,
            authenticated_user.access_token,
        )
        if not success:
            raise HTTPException(status_code=404, detail='Analysis not found or not owned by this user.')
        return {'status': 'deleted', 'id': analysis_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("History delete failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail='Could not delete analysis history entry.') from exc
    

@router.post('/generate-pdf')
async def generate_pdf(
    data: AnalysisResponse,
    user_id: str = Depends(get_current_user),
):
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    try:
        html_docs = generate_html_reports(data.model_dump())
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=ats_report.pdf"
            }
        )
    except ImportError as exc:
        logger.warning("PDF generation is unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="PDF report generation is unavailable on this system.") from exc
    except Exception as exc:
        logger.error("Failed to generate PDF (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to generate PDF report.") from exc
    

@router.get('/history/{analysis_id}/pdf')
async def generate_history_pdf(
    analysis_id: str,
    authenticated_user: AuthenticatedUser = Depends(get_authenticated_user),
):
    from backend.database.supabase_db import get_user_history
    from backend.services.report_generator import generate_html_reports
    from backend.services.pdf_export import generate_combined_pdf
    from fastapi.responses import Response

    try:
        history = await get_user_history(
            authenticated_user.user_id,
            authenticated_user.access_token,
        )
    except Exception as exc:
        logger.error("Failed to load analysis history for PDF (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Could not load analysis history.") from exc
    analysis_data = next((item["analysis_result"] for item in history if item["id"] == analysis_id), None)

    if not analysis_data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        html_docs = generate_html_reports(analysis_data)
        pdf_bytes = generate_combined_pdf(html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ats_report_{analysis_id}.pdf"
            }
        )
    except ImportError as exc:
        logger.warning("PDF generation is unavailable (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="PDF report generation is unavailable on this system.") from exc
    except Exception as exc:
        logger.error("Failed to generate history PDF (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="Failed to generate PDF report.") from exc