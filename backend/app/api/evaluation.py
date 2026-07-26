from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.supabase_client import supabase
from app.services.evaluation_service import (
    evaluate_candidate,
)


router = APIRouter(
    prefix="/api/evaluation",
    tags=["Candidate Evaluation"],
)


class JobDescriptionRequest(BaseModel):
    title: str = Field(
        min_length=2,
        max_length=200,
    )

    description: str = Field(
        min_length=20,
    )

    required_skills: list[str] = Field(
        default_factory=list
    )


@router.post("/job-description")
def create_job_description(
    request: JobDescriptionRequest,
):
    """
    Save a recruiter-provided job description.
    """

    required_skills = sorted(
        {
            skill.strip()
            for skill in request.required_skills
            if skill.strip()
        }
    )

    response = (
        supabase
        .table("job_descriptions")
        .insert(
            {
                "title": request.title.strip(),
                "description": request.description.strip(),
                "required_skills": required_skills,
            }
        )
        .execute()
    )

    if not response.data:
        raise HTTPException(
            status_code=500,
            detail="The job description could not be saved.",
        )

    return {
        "message": "Job description saved successfully.",
        "job_description": response.data[0],
    }


@router.get("/job-descriptions")
def get_job_descriptions():
    """
    Return all saved job descriptions.
    """

    response = (
        supabase
        .table("job_descriptions")
        .select("*")
        .order("created_at", desc=True)
        .execute()
    )

    return {
        "total": len(response.data or []),
        "job_descriptions": response.data or [],
    }


@router.post(
    "/candidate/{candidate_id}/job/{job_description_id}"
)
def evaluate_single_candidate(
    candidate_id: int,
    job_description_id: int,
):
    """
    Evaluate one candidate for one job description.
    """

    candidate_response = (
        supabase
        .table("candidates")
        .select(
            "id,s_no,name,email,college,branch,cgpa,"
            "best_ai_project,research_work,extracted_skills,"
            "test_la,test_code,resume_processing_status"
        )
        .eq("id", candidate_id)
        .limit(1)
        .execute()
    )

    if not candidate_response.data:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        )

    job_response = (
        supabase
        .table("job_descriptions")
        .select("*")
        .eq("id", job_description_id)
        .limit(1)
        .execute()
    )

    if not job_response.data:
        raise HTTPException(
            status_code=404,
            detail="Job description not found.",
        )

    candidate = candidate_response.data[0]
    job_description = job_response.data[0]

    evaluation = evaluate_candidate(
        candidate=candidate,
        job_description=job_description,
    )

    database_record = {
        "candidate_id": candidate_id,
        "job_description_id": job_description_id,
        **evaluation,
    }

    save_response = (
        supabase
        .table("candidate_evaluations")
        .upsert(
            database_record,
            on_conflict=(
                "candidate_id,job_description_id"
            ),
        )
        .execute()
    )

    return {
        "message": "Candidate evaluated successfully.",
        "candidate": {
            "id": candidate["id"],
            "name": candidate["name"],
            "email": candidate["email"],
        },
        "job_description": {
            "id": job_description["id"],
            "title": job_description["title"],
        },
        "evaluation": evaluation,
        "saved_evaluation": (
            save_response.data[0]
            if save_response.data
            else None
        ),
    }


@router.post(
    "/evaluate-all/{job_description_id}"
)
def evaluate_all_candidates(
    job_description_id: int,
):
    """
    Evaluate all candidates for one job description.
    """

    job_response = (
        supabase
        .table("job_descriptions")
        .select("*")
        .eq("id", job_description_id)
        .limit(1)
        .execute()
    )

    if not job_response.data:
        raise HTTPException(
            status_code=404,
            detail="Job description not found.",
        )

    job_description = job_response.data[0]

    candidate_response = (
        supabase
        .table("candidates")
        .select(
            "id,s_no,name,email,college,branch,cgpa,"
            "best_ai_project,research_work,extracted_skills,"
            "test_la,test_code,resume_processing_status"
        )
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
        try:
            evaluation = evaluate_candidate(
                candidate=candidate,
                job_description=job_description,
            )

            database_record = {
                "candidate_id": candidate["id"],
                "job_description_id": (
                    job_description_id
                ),
                **evaluation,
            }

            (
                supabase
                .table("candidate_evaluations")
                .upsert(
                    database_record,
                    on_conflict=(
                        "candidate_id,"
                        "job_description_id"
                    ),
                )
                .execute()
            )

            completed.append(
                {
                    "candidate_id": candidate["id"],
                    "candidate_name": candidate["name"],
                    "overall_score": evaluation[
                        "overall_score"
                    ],
                    "recommendation": evaluation[
                        "recommendation"
                    ],
                    "matched_skills": evaluation[
                        "matched_skills"
                    ],
                }
            )

        except Exception as exc:
            failed.append(
                {
                    "candidate_id": candidate["id"],
                    "candidate_name": candidate["name"],
                    "error": str(exc),
                }
            )

    completed.sort(
        key=lambda item: item["overall_score"],
        reverse=True,
    )

    for rank, result in enumerate(
        completed,
        start=1,
    ):
        result["rank"] = rank

    return {
        "message": "Candidate evaluation completed.",
        "job_description": {
            "id": job_description["id"],
            "title": job_description["title"],
        },
        "total_candidates": len(candidates),
        "evaluated_successfully": len(completed),
        "failed": len(failed),
        "ranking": completed,
        "errors": failed,
    }


@router.get("/ranking/{job_description_id}")
def get_candidate_ranking(
    job_description_id: int,
):
    """
    Return stored candidate rankings.
    """

    evaluation_response = (
        supabase
        .table("candidate_evaluations")
        .select(
            "candidate_id,resume_match_score,"
            "project_relevance_score,"
            "research_relevance_score,cgpa_score,"
            "logical_aptitude_score,coding_test_score,"
            "overall_score,matched_skills,missing_skills,"
            "recommendation,explanation,"
            "candidates(id,s_no,name,email,college,branch)"
        )
        .eq(
            "job_description_id",
            job_description_id,
        )
        .order(
            "overall_score",
            desc=True,
        )
        .execute()
    )

    ranking = evaluation_response.data or []

    for rank, evaluation in enumerate(
        ranking,
        start=1,
    ):
        evaluation["rank"] = rank

    return {
        "job_description_id": job_description_id,
        "total_ranked_candidates": len(ranking),
        "ranking": ranking,
    }