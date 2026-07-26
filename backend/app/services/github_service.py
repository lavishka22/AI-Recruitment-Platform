import os
import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv


load_dotenv()

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API_URL = "https://api.github.com"

MAX_REPOSITORIES_TO_ANALYZE = 5
COMMITS_PER_REPOSITORY = 10


class GitHubAnalysisError(Exception):
    """Raised when a GitHub profile cannot be analyzed."""


def get_github_headers() -> dict[str, str]:
    """
    Create headers for GitHub REST API requests.
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Recruitment-Platform",
    }

    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    return headers


def github_request(
    endpoint: str,
    params: dict[str, Any] | None = None,
    allow_not_found: bool = False,
) -> requests.Response | None:
    """
    Send one request to the GitHub REST API.
    """

    url = f"{GITHUB_API_URL}{endpoint}"

    try:
        response = requests.get(
            url,
            headers=get_github_headers(),
            params=params,
            timeout=30,
        )

    except requests.RequestException as exc:
        raise GitHubAnalysisError(
            f"GitHub request failed: {str(exc)}"
        ) from exc

    if response.status_code == 404 and allow_not_found:
        return None

    if response.status_code == 401:
        raise GitHubAnalysisError(
            "GitHub authentication failed. Check GITHUB_TOKEN."
        )

    if response.status_code == 403:
        remaining = response.headers.get(
            "X-RateLimit-Remaining",
            "unknown",
        )

        raise GitHubAnalysisError(
            "GitHub API request was forbidden or rate-limited. "
            f"Remaining requests: {remaining}."
        )

    if not response.ok:
        try:
            error_message = response.json().get(
                "message",
                response.text,
            )
        except ValueError:
            error_message = response.text

        raise GitHubAnalysisError(
            f"GitHub API returned {response.status_code}: "
            f"{error_message}"
        )

    return response


def extract_github_username(profile_url: str) -> str:
    """
    Extract a GitHub username from a profile URL or username.

    Examples:
    https://github.com/lavishka22 -> lavishka22
    github.com/lavishka22         -> lavishka22
    lavishka22                    -> lavishka22
    """

    if not profile_url or not str(profile_url).strip():
        raise GitHubAnalysisError(
            "Candidate does not have a GitHub profile."
        )

    value = str(profile_url).strip()

    if not value.startswith(("http://", "https://")):
        if "github.com" in value.lower():
            value = f"https://{value}"
        else:
            username = value.strip("/")

            if re.fullmatch(r"[A-Za-z0-9-]+", username):
                return username

    parsed_url = urlparse(value)

    if "github.com" not in parsed_url.netloc.lower():
        raise GitHubAnalysisError(
            "The supplied URL is not a GitHub profile URL."
        )

    path_parts = [
        part
        for part in parsed_url.path.split("/")
        if part
    ]

    if not path_parts:
        raise GitHubAnalysisError(
            "GitHub username was missing from the URL."
        )

    username = path_parts[0]

    if not re.fullmatch(r"[A-Za-z0-9-]+", username):
        raise GitHubAnalysisError(
            "The GitHub username is not valid."
        )

    return username


def clamp_score(value: float) -> float:
    return round(
        max(0.0, min(float(value), 100.0)),
        2,
    )


def get_user_profile(username: str) -> dict[str, Any]:
    response = github_request(f"/users/{username}")

    if response is None:
        raise GitHubAnalysisError(
            "GitHub profile was not found."
        )

    return response.json()


def get_user_repositories(
    username: str,
) -> list[dict[str, Any]]:
    """
    Fetch public, non-fork repositories.
    """

    response = github_request(
        f"/users/{username}/repos",
        params={
            "type": "owner",
            "sort": "updated",
            "direction": "desc",
            "per_page": 100,
        },
    )

    repositories = response.json() if response else []

    return [
        repository
        for repository in repositories
        if not repository.get("fork", False)
    ]


def get_repository_languages(
    username: str,
    repository_name: str,
) -> dict[str, int]:
    response = github_request(
        f"/repos/{username}/{repository_name}/languages"
    )

    return response.json() if response else {}


def repository_has_readme(
    username: str,
    repository_name: str,
) -> bool:
    response = github_request(
        f"/repos/{username}/{repository_name}/readme",
        allow_not_found=True,
    )

    return response is not None


def get_recent_commit_count(
    username: str,
    repository_name: str,
) -> int:
    response = github_request(
        f"/repos/{username}/{repository_name}/commits",
        params={
            "author": username,
            "per_page": COMMITS_PER_REPOSITORY,
        },
        allow_not_found=True,
    )

    if response is None:
        return 0

    return len(response.json())


def calculate_repository_quality_score(
    repositories: list[dict[str, Any]],
    repositories_with_readme: int,
) -> float:
    if not repositories:
        return 0.0

    scores = []

    for repository in repositories:
        repository_score = 0.0

        if repository.get("description"):
            repository_score += 20

        if repository.get("homepage"):
            repository_score += 15

        if repository.get("stargazers_count", 0) > 0:
            repository_score += min(
                repository["stargazers_count"] * 5,
                20,
            )

        if repository.get("forks_count", 0) > 0:
            repository_score += min(
                repository["forks_count"] * 5,
                15,
            )

        if repository.get("size", 0) >= 100:
            repository_score += 15

        if repository.get("topics"):
            repository_score += 15

        scores.append(
            clamp_score(repository_score)
        )

    average_quality = sum(scores) / len(scores)

    readme_bonus = (
        repositories_with_readme
        / len(repositories)
    ) * 10

    return clamp_score(
        average_quality + readme_bonus
    )


def calculate_documentation_score(
    repositories_with_readme: int,
    analyzed_repository_count: int,
) -> float:
    if analyzed_repository_count == 0:
        return 0.0

    return clamp_score(
        (
            repositories_with_readme
            / analyzed_repository_count
        )
        * 100
    )


def calculate_activity_score(
    recent_commits: int,
    repositories: list[dict[str, Any]],
) -> float:
    if not repositories:
        return 0.0

    commit_score = min(
        recent_commits * 5,
        60,
    )

    recently_updated = 0
    current_time = datetime.now(timezone.utc)

    for repository in repositories:
        updated_at = repository.get("pushed_at")

        if not updated_at:
            continue

        try:
            pushed_date = datetime.fromisoformat(
                updated_at.replace("Z", "+00:00")
            )

            days_since_push = (
                current_time - pushed_date
            ).days

            if days_since_push <= 180:
                recently_updated += 1

        except ValueError:
            continue

    recency_score = (
        recently_updated / len(repositories)
    ) * 40

    return clamp_score(
        commit_score + recency_score
    )


def calculate_diversity_score(
    language_totals: dict[str, int],
) -> float:
    language_count = len(language_totals)

    if language_count == 0:
        return 0.0

    return clamp_score(
        min(language_count * 20, 100)
    )


def create_github_explanation(
    repository_count: int,
    analyzed_count: int,
    readme_count: int,
    recent_commits: int,
    language_names: list[str],
    total_stars: int,
) -> tuple[list[str], list[str], str]:
    strengths = []
    concerns = []

    if analyzed_count >= 4:
        strengths.append(
            "multiple original repositories were evaluated"
        )
    elif repository_count == 0:
        concerns.append(
            "no original public repositories were found"
        )
    else:
        concerns.append(
            "only a small number of repositories were available"
        )

    if analyzed_count and readme_count == analyzed_count:
        strengths.append(
            "all analyzed repositories contain README documentation"
        )
    elif analyzed_count and readme_count < analyzed_count / 2:
        concerns.append(
            "most repositories lack README documentation"
        )

    if recent_commits >= 10:
        strengths.append(
            "consistent recent commit activity was detected"
        )
    elif recent_commits == 0:
        concerns.append(
            "no authored commits were found in the analyzed sample"
        )

    if len(language_names) >= 4:
        strengths.append(
            "good programming-language diversity"
        )
    elif len(language_names) <= 1:
        concerns.append(
            "limited programming-language diversity"
        )

    if total_stars > 0:
        strengths.append(
            "repositories received community stars"
        )

    if not strengths:
        strengths.append(
            "the GitHub profile was successfully analyzed"
        )

    if not concerns:
        concerns.append(
            "no major repository-level concerns were detected"
        )

    explanation = (
        f"Analyzed {analyzed_count} of "
        f"{repository_count} original repositories. "
        f"Found {readme_count} repositories with README files, "
        f"{recent_commits} recent authored commits and "
        f"{len(language_names)} programming languages. "
        f"Strengths: {'; '.join(strengths)}. "
        f"Areas for review: {'; '.join(concerns)}."
    )

    return strengths, concerns, explanation


def analyze_github_profile(
    profile_url: str,
) -> dict[str, Any]:
    """
    Run complete repository-level GitHub analysis.
    """

    username = extract_github_username(profile_url)
    profile = get_user_profile(username)
    all_repositories = get_user_repositories(username)

    repositories_to_analyze = all_repositories[
        :MAX_REPOSITORIES_TO_ANALYZE
    ]

    total_stars = sum(
        repository.get("stargazers_count", 0)
        for repository in all_repositories
    )

    total_forks = sum(
        repository.get("forks_count", 0)
        for repository in all_repositories
    )

    language_counter: Counter[str] = Counter()
    repositories_with_readme = 0
    recent_commits = 0
    repository_results = []

    for repository in repositories_to_analyze:
        repository_name = repository["name"]

        languages = get_repository_languages(
            username,
            repository_name,
        )

        for language, byte_count in languages.items():
            language_counter[language] += byte_count

        has_readme = repository_has_readme(
            username,
            repository_name,
        )

        if has_readme:
            repositories_with_readme += 1

        commit_count = get_recent_commit_count(
            username,
            repository_name,
        )

        recent_commits += commit_count

        repository_results.append(
            {
                "name": repository_name,
                "url": repository.get("html_url"),
                "description": repository.get("description"),
                "primary_language": repository.get("language"),
                "languages": languages,
                "stars": repository.get(
                    "stargazers_count",
                    0,
                ),
                "forks": repository.get(
                    "forks_count",
                    0,
                ),
                "size_kb": repository.get("size", 0),
                "topics": repository.get("topics", []),
                "has_readme": has_readme,
                "recent_authored_commits": commit_count,
                "last_pushed_at": repository.get("pushed_at"),
            }
        )

    repository_quality_score = (
        calculate_repository_quality_score(
            repositories=repositories_to_analyze,
            repositories_with_readme=(
                repositories_with_readme
            ),
        )
    )

    documentation_score = calculate_documentation_score(
        repositories_with_readme=repositories_with_readme,
        analyzed_repository_count=len(
            repositories_to_analyze
        ),
    )

    activity_score = calculate_activity_score(
        recent_commits=recent_commits,
        repositories=repositories_to_analyze,
    )

    diversity_score = calculate_diversity_score(
        dict(language_counter)
    )

    github_score = clamp_score(
        repository_quality_score * 0.35
        + documentation_score * 0.20
        + activity_score * 0.30
        + diversity_score * 0.15
    )

    strengths, concerns, explanation = (
        create_github_explanation(
            repository_count=len(all_repositories),
            analyzed_count=len(repositories_to_analyze),
            readme_count=repositories_with_readme,
            recent_commits=recent_commits,
            language_names=list(language_counter.keys()),
            total_stars=total_stars,
        )
    )

    return {
        "github_username": username,
        "profile_url": profile.get("html_url"),
        "public_repositories": len(all_repositories),
        "analyzed_repositories": len(
            repositories_to_analyze
        ),
        "followers": profile.get("followers", 0),
        "following": profile.get("following", 0),
        "total_stars": total_stars,
        "total_forks": total_forks,
        "recent_commits": recent_commits,
        "repositories_with_readme": (
            repositories_with_readme
        ),
        "languages": dict(language_counter),
        "top_repositories": repository_results,
        "repository_quality_score": (
            repository_quality_score
        ),
        "documentation_score": documentation_score,
        "activity_score": activity_score,
        "diversity_score": diversity_score,
        "github_score": github_score,
        "strengths": strengths,
        "concerns": concerns,
        "explanation": explanation,
        "status": "completed",
        "analyzed_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }