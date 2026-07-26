from pathlib import Path

import pandas as pd
from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.supabase_client import supabase


router = APIRouter(
    prefix="/api/upload",
    tags=["Candidate Upload"],
)


REQUIRED_COLUMNS = [
    "name",
    "email",
    "college",
    "branch",
    "cgpa",
    "best_ai_project",
    "research_work",
    "github",
    "resume",
]


def normalize_column_name(column: str) -> str:
    """
    Convert uploaded column names into a consistent snake_case format.

    Examples:
    'Best AI Project' -> 'best_ai_project'
    'GitHub Profile'  -> 'github_profile'
    """

    return (
        str(column)
        .strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
    )


@router.post("/candidates")
async def upload_candidates(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was selected.",
        )

    file_extension = Path(file.filename).suffix.lower()

    if file_extension not in {".xlsx", ".xls", ".csv"}:
        raise HTTPException(
            status_code=400,
            detail="Only CSV and Excel files are allowed.",
        )

    try:
        if file_extension == ".csv":
            df = pd.read_csv(file.file)

        else:
            excel_file = pd.ExcelFile(file.file)

            sheet_name = (
                "Response"
                if "Response" in excel_file.sheet_names
                else excel_file.sheet_names[0]
            )

            df = pd.read_excel(
                excel_file,
                sheet_name=sheet_name,
            )

    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Could not read the uploaded file: {str(exc)}",
        ) from exc

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file contains no candidate records.",
        )

    # Normalize uploaded column names.
    df.columns = [
        normalize_column_name(column)
        for column in df.columns
    ]

    # Accept alternate recruiter-friendly column names.
    column_aliases = {
        "github_profile": "github",
        "github_link": "github",
        "resume_link": "resume",
        "best_ai_project_name": "best_ai_project",
    }

    df = df.rename(columns=column_aliases)

    missing_columns = [
        column
        for column in REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Required columns are missing.",
                "missing_columns": missing_columns,
                "received_columns": list(df.columns),
            },
        )

    # Remove completely blank rows.
    df = df.dropna(how="all")

    # Replace NaN values with None for valid JSON and database insertion.
    df = df.astype(object).where(pd.notna(df), None)

    candidates = df.to_dict(orient="records")

    valid_candidates = [
        candidate
        for candidate in candidates
        if (
        candidate.get("s_no") is not None
        and candidate.get("name")
        and candidate.get("email")
        )
    ]

    invalid_candidates = len(candidates) - len(valid_candidates)

    saved_candidates = 0
    failed_candidates = []

    for candidate in valid_candidates:
        try:
            candidate_record = {
                "s_no": candidate.get("s_no"),
                "name": candidate.get("name"),
                "email": candidate.get("email"),
                "college": candidate.get("college"),
                "branch": candidate.get("branch"),
                "cgpa": candidate.get("cgpa"),
                "best_ai_project": candidate.get("best_ai_project"),
                "research_work": candidate.get("research_work"),
                "github": candidate.get("github"),
                "resume": candidate.get("resume"),
                "test_la": candidate.get("test_la"),
                "test_code": candidate.get("test_code"),
                "status": "uploaded",
            }

            supabase.table("candidates").upsert(
                candidate_record,
                on_conflict="s_no",
            ).execute()

            saved_candidates += 1

        except Exception as exc:
            failed_candidates.append(
                {
                    "email": candidate.get("email"),
                    "error": str(exc),
                }
            )

    return {
        "message": "Candidate file processed successfully.",
        "filename": file.filename,
        "total_candidates": len(candidates),
        "valid_candidates": len(valid_candidates),
        "invalid_candidates": invalid_candidates,
        "saved_to_database": saved_candidates,
        "failed_to_save": len(failed_candidates),
        "failed_candidates": failed_candidates,
        "columns": list(df.columns),
        "preview": candidates[:5],
    }