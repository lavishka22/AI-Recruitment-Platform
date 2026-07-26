from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.core.supabase_client import supabase
from app.services.resume_service import (
    download_and_parse_resume,
)


router = APIRouter(
    prefix="/api/resume",
    tags=["Resume Processing"],
)


@router.get("/health")
def resume_health():
    return {
        "status": "Resume module ready"
    }


@router.post("/process/{candidate_id}")
def process_candidate_resume(candidate_id: int):
    """
    Download and parse one candidate's resume.
    """

    candidate_response = (
        supabase
        .table("candidates")
        .select("id,name,resume")
        .eq("id", candidate_id)
        .limit(1)
        .execute()
    )

    if not candidate_response.data:
        raise HTTPException(
            status_code=404,
            detail=f"Candidate {candidate_id} was not found.",
        )

    candidate = candidate_response.data[0]

    try:
        supabase.table("candidates").update(
            {
                "resume_processing_status": "processing",
            }
        ).eq(
            "id",
            candidate_id,
        ).execute()

        result = download_and_parse_resume(
            candidate_id=candidate["id"],
            candidate_name=candidate["name"],
            resume_url=candidate["resume"],
        )

        processed_at = datetime.now(
            timezone.utc
        ).isoformat()

        supabase.table("candidates").update(
            {
                "resume_text": result["resume_text"],
                "extracted_skills": result["extracted_skills"],
                "resume_file_path": result["resume_file_path"],
                "resume_processing_status": "completed",
                "resume_processed_at": processed_at,
            }
        ).eq(
            "id",
            candidate_id,
        ).execute()

        return {
            "message": "Resume processed successfully.",
            "candidate_id": candidate_id,
            "candidate_name": candidate["name"],
            "resume_file_path": result["resume_file_path"],
            "skills_detected": len(
                result["extracted_skills"]
            ),
            "extracted_skills": result[
                "extracted_skills"
            ],
            "statistics": result["statistics"],
            "text_preview": result["resume_text"][:500],
        }

    except Exception as exc:
        supabase.table("candidates").update(
            {
                "resume_processing_status": "failed",
            }
        ).eq(
            "id",
            candidate_id,
        ).execute()

        raise HTTPException(
            status_code=500,
            detail={
                "message": "Resume processing failed.",
                "candidate_id": candidate_id,
                "error": str(exc),
            },
        ) from exc


@router.post("/process-all")
def process_all_resumes():
    """
    Download, parse, and save all candidate resumes.
    """

    candidate_response = (
        supabase
        .table("candidates")
        .select("id,name,resume")
        .order("s_no")
        .execute()
    )

    candidates = candidate_response.data or []

    if not candidates:
        raise HTTPException(
            status_code=404,
            detail="No candidates were found.",
        )

    completed = []
    failed = []

    for candidate in candidates:
        candidate_id = candidate["id"]

        try:
            supabase.table("candidates").update(
                {
                    "resume_processing_status": "processing",
                }
            ).eq(
                "id",
                candidate_id,
            ).execute()

            result = download_and_parse_resume(
                candidate_id=candidate_id,
                candidate_name=candidate["name"],
                resume_url=candidate["resume"],
            )

            processed_at = datetime.now(
                timezone.utc
            ).isoformat()

            supabase.table("candidates").update(
                {
                    "resume_text": result["resume_text"],
                    "extracted_skills": result[
                        "extracted_skills"
                    ],
                    "resume_file_path": result[
                        "resume_file_path"
                    ],
                    "resume_processing_status": "completed",
                    "resume_processed_at": processed_at,
                }
            ).eq(
                "id",
                candidate_id,
            ).execute()

            completed.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate["name"],
                    "skills_detected": len(
                        result["extracted_skills"]
                    ),
                    "extracted_skills": result[
                        "extracted_skills"
                    ],
                    "word_count": result[
                        "statistics"
                    ]["word_count"],
                }
            )

        except Exception as exc:
            supabase.table("candidates").update(
                {
                    "resume_processing_status": "failed",
                }
            ).eq(
                "id",
                candidate_id,
            ).execute()

            failed.append(
                {
                    "candidate_id": candidate_id,
                    "candidate_name": candidate["name"],
                    "error": str(exc),
                }
            )

    return {
        "message": "Resume batch processing completed.",
        "total_candidates": len(candidates),
        "processed_successfully": len(completed),
        "failed": len(failed),
        "results": completed,
        "errors": failed,
    }