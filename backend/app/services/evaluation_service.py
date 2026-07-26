import re
from typing import Any

from app.resume.parser import extract_skills


SCORING_WEIGHTS = {
    "resume_match": 0.25,
    "project_relevance": 0.10,
    "research_relevance": 0.05,
    "cgpa": 0.10,
    "logical_aptitude": 0.10,
    "coding_test": 0.20,
    "github": 0.20,
}


def clamp_score(value: float) -> float:
    """
    Keep a score between 0 and 100.
    """

    return round(
        max(0.0, min(float(value), 100.0)),
        2,
    )


def normalize_percentage_score(value: Any) -> float:
    """
    Normalize aptitude and coding scores.

    Examples:
    8.5 out of 10 becomes 85
    72 out of 100 remains 72
    """

    if value is None:
        return 0.0

    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return 0.0

    if numeric_value <= 10:
        numeric_value *= 10

    return clamp_score(numeric_value)


def normalize_cgpa(cgpa: Any) -> float:
    """
    Convert CGPA into a percentage-like score.

    Examples:
    8.2 CGPA becomes 82
    75 percentage remains 75
    """

    if cgpa is None:
        return 0.0

    try:
        numeric_cgpa = float(cgpa)
    except (TypeError, ValueError):
        return 0.0

    if numeric_cgpa <= 10:
        numeric_cgpa *= 10

    return clamp_score(numeric_cgpa)


def tokenize_text(text: str | None) -> set[str]:
    """
    Convert text into meaningful lowercase tokens.
    """

    if not text:
        return set()

    words = re.findall(
        r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}",
        str(text).lower(),
    )

    ignored_words = {
        "and",
        "the",
        "with",
        "for",
        "from",
        "that",
        "this",
        "using",
        "into",
        "have",
        "has",
        "will",
        "are",
        "was",
        "were",
        "candidate",
        "experience",
        "work",
        "role",
        "skills",
        "knowledge",
        "preferred",
        "required",
        "looking",
        "strong",
        "good",
        "should",
    }

    return {
        word
        for word in words
        if word not in ignored_words
    }


def calculate_text_relevance(
    candidate_text: str | None,
    job_description: str,
) -> float:
    """
    Calculate keyword overlap between candidate information
    and the job description.
    """

    candidate_tokens = tokenize_text(candidate_text)
    job_tokens = tokenize_text(job_description)

    if not candidate_tokens or not job_tokens:
        return 0.0

    matched_tokens = candidate_tokens.intersection(
        job_tokens
    )

    overlap_ratio = len(matched_tokens) / len(job_tokens)

    # The multiplier prevents short but relevant project
    # descriptions from receiving extremely low scores.
    return clamp_score(overlap_ratio * 250)


def calculate_skill_match(
    candidate_skills: list[str] | None,
    required_skills: list[str],
) -> dict[str, Any]:
    """
    Compare candidate skills against required job skills.
    """

    normalized_candidate_skills = {
        str(skill).strip().lower()
        for skill in (candidate_skills or [])
        if str(skill).strip()
    }

    normalized_required_skills = {
        str(skill).strip().lower()
        for skill in required_skills
        if str(skill).strip()
    }

    if not normalized_required_skills:
        return {
            "score": 0.0,
            "matched_skills": [],
            "missing_skills": [],
        }

    matched_normalized = (
        normalized_candidate_skills
        .intersection(normalized_required_skills)
    )

    missing_normalized = (
        normalized_required_skills
        - normalized_candidate_skills
    )

    original_skill_names = {
        str(skill).strip().lower(): str(skill).strip()
        for skill in required_skills
        if str(skill).strip()
    }

    matched_skills = sorted(
        original_skill_names[skill]
        for skill in matched_normalized
    )

    missing_skills = sorted(
        original_skill_names[skill]
        for skill in missing_normalized
    )

    score = (
        len(matched_normalized)
        / len(normalized_required_skills)
    ) * 100

    return {
        "score": clamp_score(score),
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
    }


def create_recommendation(
    overall_score: float,
) -> str:
    """
    Convert the final score into a recruitment recommendation.
    """

    if overall_score >= 80:
        return "Strong Shortlist"

    if overall_score >= 65:
        return "Shortlist"

    if overall_score >= 50:
        return "Review"

    return "Not Shortlisted"


def create_explanation(
    overall_score: float,
    skill_score: float,
    project_score: float,
    research_score: float,
    coding_score: float,
    logical_aptitude_score: float,
    github_score: float | None,
    matched_skills: list[str],
    missing_skills: list[str],
) -> str:
    """
    Generate an explainable candidate evaluation summary.
    """

    strengths: list[str] = []
    concerns: list[str] = []

    if skill_score >= 75:
        strengths.append(
            "strong alignment with the required technical skills"
        )
    elif skill_score >= 50:
        strengths.append(
            "moderate alignment with the required technical skills"
        )
    else:
        concerns.append(
            "limited alignment with the required technical skills"
        )

    if project_score >= 70:
        strengths.append(
            "highly relevant project experience"
        )
    elif project_score >= 40:
        strengths.append(
            "moderately relevant project experience"
        )
    else:
        concerns.append(
            "low project relevance"
        )

    if research_score >= 60:
        strengths.append(
            "relevant research exposure"
        )
    elif research_score == 0:
        concerns.append(
            "no relevant research information was detected"
        )

    if coding_score >= 75:
        strengths.append(
            "strong coding test performance"
        )
    elif coding_score < 50:
        concerns.append(
            "weak coding test performance"
        )

    if logical_aptitude_score >= 75:
        strengths.append(
            "strong logical aptitude performance"
        )
    elif logical_aptitude_score < 50:
        concerns.append(
            "low logical aptitude performance"
        )

    if github_score is not None:
        if github_score >= 75:
            strengths.append(
                "strong GitHub repository quality and activity"
            )
        elif github_score >= 55:
            strengths.append(
                "moderate GitHub repository quality"
            )
        else:
            concerns.append(
                "limited GitHub repository quality or activity"
            )

    if matched_skills:
        strengths.append(
            "matched skills: "
            + ", ".join(matched_skills[:6])
        )

    if missing_skills:
        concerns.append(
            "missing skills: "
            + ", ".join(missing_skills[:6])
        )

    strengths_text = (
        "; ".join(strengths)
        if strengths
        else "no major strengths were detected"
    )

    concerns_text = (
        "; ".join(concerns)
        if concerns
        else "no major concerns were detected"
    )

    explanation = (
        f"The candidate received an overall score of "
        f"{overall_score:.2f}. Strengths include "
        f"{strengths_text}. Areas requiring review include "
        f"{concerns_text}."
    )

    if github_score is not None:
        explanation += (
            f" GitHub repository analysis contributed a score "
            f"of {clamp_score(github_score):.2f}."
        )
    else:
        explanation += (
            " No GitHub profile was provided, so the final score "
            "was normalized using the remaining available "
            "evaluation components."
        )

    return explanation


def calculate_normalized_overall_score(
    component_scores: dict[str, float],
    active_weights: dict[str, float],
) -> float:
    """
    Calculate a normalized weighted score.

    If GitHub data is unavailable, the GitHub weight is excluded
    and the remaining weights are normalized automatically.
    """

    total_active_weight = sum(active_weights.values())

    if total_active_weight <= 0:
        return 0.0

    weighted_total = sum(
        component_scores[component_name]
        * active_weights[component_name]
        for component_name in component_scores
    )

    normalized_score = (
        weighted_total / total_active_weight
    )

    return clamp_score(normalized_score)


def evaluate_candidate(
    candidate: dict[str, Any],
    job_description: dict[str, Any],
    github_score: float | None = None,
) -> dict[str, Any]:
    """
    Run the complete candidate evaluation pipeline.

    GitHub scoring is optional. When GitHub data is unavailable,
    the final score is calculated from the remaining components.
    """

    required_skills = (
        job_description.get("required_skills") or []
    )

    # Automatically detect skills from the job description
    # when the recruiter did not provide a separate skills list.
    if not required_skills:
        required_skills = extract_skills(
            job_description.get("description", "")
        )

    candidate_skills = (
        candidate.get("extracted_skills") or []
    )

    skill_result = calculate_skill_match(
        candidate_skills=candidate_skills,
        required_skills=required_skills,
    )

    resume_match_score = skill_result["score"]

    project_relevance_score = calculate_text_relevance(
        candidate_text=candidate.get("best_ai_project"),
        job_description=job_description.get(
            "description",
            "",
        ),
    )

    research_relevance_score = calculate_text_relevance(
        candidate_text=candidate.get("research_work"),
        job_description=job_description.get(
            "description",
            "",
        ),
    )

    cgpa_score = normalize_cgpa(
        candidate.get("cgpa")
    )

    logical_aptitude_score = normalize_percentage_score(
        candidate.get("test_la")
    )

    coding_test_score = normalize_percentage_score(
        candidate.get("test_code")
    )

    github_profile_available = (
        github_score is not None
    )

    normalized_github_score = (
        clamp_score(github_score)
        if github_profile_available
        else None
    )

    component_scores = {
        "resume_match": resume_match_score,
        "project_relevance": project_relevance_score,
        "research_relevance": research_relevance_score,
        "cgpa": cgpa_score,
        "logical_aptitude": logical_aptitude_score,
        "coding_test": coding_test_score,
    }

    active_weights = {
        "resume_match": SCORING_WEIGHTS[
            "resume_match"
        ],
        "project_relevance": SCORING_WEIGHTS[
            "project_relevance"
        ],
        "research_relevance": SCORING_WEIGHTS[
            "research_relevance"
        ],
        "cgpa": SCORING_WEIGHTS["cgpa"],
        "logical_aptitude": SCORING_WEIGHTS[
            "logical_aptitude"
        ],
        "coding_test": SCORING_WEIGHTS[
            "coding_test"
        ],
    }

    if github_profile_available:
        component_scores["github"] = (
            normalized_github_score or 0.0
        )

        active_weights["github"] = (
            SCORING_WEIGHTS["github"]
        )

    overall_score = calculate_normalized_overall_score(
        component_scores=component_scores,
        active_weights=active_weights,
    )

    recommendation = create_recommendation(
        overall_score
    )

    explanation = create_explanation(
        overall_score=overall_score,
        skill_score=resume_match_score,
        project_score=project_relevance_score,
        research_score=research_relevance_score,
        coding_score=coding_test_score,
        logical_aptitude_score=logical_aptitude_score,
        github_score=normalized_github_score,
        matched_skills=skill_result[
            "matched_skills"
        ],
        missing_skills=skill_result[
            "missing_skills"
        ],
    )

    return {
        "resume_match_score": resume_match_score,
        "project_relevance_score": (
            project_relevance_score
        ),
        "research_relevance_score": (
            research_relevance_score
        ),
        "cgpa_score": cgpa_score,
        "logical_aptitude_score": (
            logical_aptitude_score
        ),
        "coding_test_score": coding_test_score,
        "github_score": normalized_github_score,
        "github_profile_available": (
            github_profile_available
        ),
        "overall_score": overall_score,
        "matched_skills": skill_result[
            "matched_skills"
        ],
        "missing_skills": skill_result[
            "missing_skills"
        ],
        "recommendation": recommendation,
        "explanation": explanation,
    }