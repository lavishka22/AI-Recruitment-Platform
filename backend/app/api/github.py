from fastapi import APIRouter, HTTPException

from app.core.supabase_client import supabase
from app.services.github_service import (
    GitHubAnalysisError,
    analyze_github_profile,
)


router = APIRouter(
    prefix="/api/github",
    tags=["GitHub Analysis"],
)


@router.get("/health")
def github_health():
    return {
        "status": "GitHub analysis module ready"
    }


@router.post("/analyze/{candidate_id}")
def analyze_candidate_github(
    candidate_id: int,
):
    """
    Analyze one candidate's GitHub profile.
    """

    candidate_response = (
        supabase
        .table("candidates")
        .select("id,name,github")
        .eq("id", candidate_id)
        .limit(1)
        .execute()
    )

    if not candidate_response.data:
        raise HTTPException(
            status_code=404,
            detail="Candidate not found.",
        )

    candidate = candidate_response.data[0]

    try:
        result = analyze_github_profile(
            candidate["github"]
        )

        database_record = {
            "candidate_id": candidate_id,
            **result,
        }

        save_response = (
            supabase
            .table("github_analyses")
            .upsert(
                database_record,
                on_conflict="candidate_id",
            )
            .execute()
        )

        return {
            "message": "GitHub profile analyzed successfully.",
            "candidate": {
                "id": candidate_id,
                "name": candidate["name"],
            },
            "analysis": result,
            "saved": bool(save_response.data),
        }

    except GitHubAnalysisError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "GitHub analysis failed.",
                "candidate_id": candidate_id,
                "error": str(exc),
            },
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Unexpected GitHub analysis error.",
                "candidate_id": candidate_id,
                "error": str(exc),
            },
        ) from exc


@router.post("/analyze-all")
def analyze_all_candidate_github_profiles():
    """
    Analyze all candidate GitHub profiles.
    """

    candidate_response = (
        supabase
        .table("candidates")
        .select("id,s_no,name,github")
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
            result = analyze_github_profile(
                candidate["github"]
            )

            database_record = {
                "candidate_id": candidate["id"],
                **result,
            }

            (
                supabase
                .table("github_analyses")
                .upsert(
                    database_record,
                    on_conflict="candidate_id",
                )
                .execute()
            )

            completed.append(
                {
                    "candidate_id": candidate["id"],
                    "candidate_name": candidate["name"],
                    "github_username": result[
                        "github_username"
                    ],
                    "repositories_analyzed": result[
                        "analyzed_repositories"
                    ],
                    "github_score": result[
                        "github_score"
                    ],
                    "top_languages": list(
                        result["languages"].keys()
                    )[:5],
                }
            )

        except Exception as exc:
            failed.append(
                {
                    "candidate_id": candidate["id"],
                    "candidate_name": candidate["name"],
                    "github_url": candidate.get("github"),
                    "error": str(exc),
                }
            )

    completed.sort(
        key=lambda item: item["github_score"],
        reverse=True,
    )

    return {
        "message": "GitHub batch analysis completed.",
        "total_candidates": len(candidates),
        "analyzed_successfully": len(completed),
        "failed": len(failed),
        "results": completed,
        "errors": failed,
    }


@router.get("/results")
def get_github_analysis_results():
    """
    Return stored GitHub analysis results.
    """

    response = (
        supabase
        .table("github_analyses")
        .select(
            "*,"
            "candidates(id,s_no,name,email,college,branch)"
        )
        .order("github_score", desc=True)
        .execute()
    )

    results = response.data or []

    for rank, result in enumerate(
        results,
        start=1,
    ):
        result["github_rank"] = rank

    return {
        "total_results": len(results),
        "results": results,
    }