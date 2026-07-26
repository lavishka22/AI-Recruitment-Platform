import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from app.resume.parser import parse_resume


BASE_DIR = Path(__file__).resolve().parents[2]
RESUME_FOLDER = BASE_DIR / "uploads" / "resumes"

RESUME_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)


def sanitize_filename(candidate_name: str, candidate_id: int) -> str:
    """
    Generate a safe, unique PDF filename.
    """

    safe_name = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        candidate_name.strip(),
    ).strip("_")

    if not safe_name:
        safe_name = "candidate"

    return f"{candidate_id}_{safe_name}.pdf"


def convert_google_drive_url(url: str) -> str:
    """
    Convert common Google Drive share links into download links.
    """

    if "drive.google.com" not in url:
        return url

    parsed_url = urlparse(url)

    if "/file/d/" in parsed_url.path:
        file_id = parsed_url.path.split("/file/d/")[1].split("/")[0]

        return (
            "https://drive.google.com/uc"
            f"?export=download&id={file_id}"
        )

    query_parameters = parse_qs(parsed_url.query)
    file_ids = query_parameters.get("id")

    if file_ids:
        return (
            "https://drive.google.com/uc"
            f"?export=download&id={file_ids[0]}"
        )

    return url


def download_resume(
    candidate_id: int,
    candidate_name: str,
    resume_url: str,
) -> str:
    """
    Download one candidate resume and return its local path.
    """

    if not resume_url or not str(resume_url).strip():
        raise ValueError("Candidate does not have a resume URL.")

    download_url = convert_google_drive_url(
        str(resume_url).strip()
    )

    filename = sanitize_filename(
        candidate_name=candidate_name,
        candidate_id=candidate_id,
    )

    file_path = RESUME_FOLDER / filename

    response = requests.get(
        download_url,
        timeout=30,
        allow_redirects=True,
        headers={
            "User-Agent": (
                "Mozilla/5.0 AI-Recruitment-Platform/1.0"
            )
        },
    )

    response.raise_for_status()

    content = response.content

    if len(content) < 100:
        raise ValueError(
            "Downloaded resume is unexpectedly small."
        )

    if not content.startswith(b"%PDF"):
        raise ValueError(
            "The resume URL did not return a valid PDF file."
        )

    file_path.write_bytes(content)

    return str(file_path)


def download_and_parse_resume(
    candidate_id: int,
    candidate_name: str,
    resume_url: str,
) -> dict:
    """
    Download and parse one candidate resume.
    """

    file_path = download_resume(
        candidate_id=candidate_id,
        candidate_name=candidate_name,
        resume_url=resume_url,
    )

    parsed_result = parse_resume(file_path)

    return {
        "resume_file_path": file_path,
        **parsed_result,
    }