from pathlib import Path
from typing import Any

import fitz


SKILL_KEYWORDS = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript", "js"],
    "TypeScript": ["typescript"],
    "C": [" c programming ", "language c"],
    "C++": ["c++", "cpp"],
    "C#": ["c#", "c sharp"],

    "HTML": ["html"],
    "CSS": ["css"],
    "React": ["react", "react.js", "reactjs"],
    "Angular": ["angular"],
    "Vue.js": ["vue", "vue.js"],
    "Node.js": ["node.js", "nodejs"],
    "Express.js": ["express.js", "expressjs"],

    "FastAPI": ["fastapi"],
    "Flask": ["flask"],
    "Django": ["django"],
    "Spring Boot": ["spring boot"],

    "Pandas": ["pandas"],
    "NumPy": ["numpy"],
    "Matplotlib": ["matplotlib"],
    "Scikit-learn": ["scikit-learn", "sklearn"],
    "TensorFlow": ["tensorflow"],
    "Keras": ["keras"],
    "PyTorch": ["pytorch"],
    "OpenCV": ["opencv"],
    "MediaPipe": ["mediapipe"],

    "Machine Learning": [
        "machine learning",
        "ml model",
        "predictive modeling",
    ],
    "Deep Learning": ["deep learning", "neural network"],
    "Natural Language Processing": [
        "natural language processing",
        "nlp",
    ],
    "Computer Vision": ["computer vision"],
    "Generative AI": [
        "generative ai",
        "genai",
        "large language model",
        "llm",
    ],
    "RAG": [
        "retrieval augmented generation",
        "retrieval-augmented generation",
        "rag pipeline",
    ],
    "LangChain": ["langchain"],
    "Hugging Face": ["hugging face", "huggingface"],

    "SQL": ["sql"],
    "MySQL": ["mysql"],
    "PostgreSQL": ["postgresql", "postgres"],
    "MongoDB": ["mongodb"],
    "SQLite": ["sqlite"],
    "Supabase": ["supabase"],
    "Firebase": ["firebase"],

    "Power BI": ["power bi", "powerbi"],
    "Tableau": ["tableau"],
    "Excel": ["microsoft excel", "advanced excel", "ms excel"],

    "Git": [" git ", "git version control"],
    "GitHub": ["github"],
    "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"],
    "MLflow": ["mlflow"],
    "GitHub Actions": ["github actions"],
    "CI/CD": ["ci/cd", "continuous integration"],

    "AWS": ["aws", "amazon web services"],
    "Azure": ["microsoft azure", "azure"],
    "Google Cloud": ["google cloud", "gcp"],

    "REST API": ["rest api", "restful api"],
    "Data Analysis": ["data analysis", "data analytics"],
    "Data Engineering": ["data engineering", "etl pipeline", "data pipeline"],
}


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract readable text from a PDF using PyMuPDF.
    """

    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(
            f"Resume file does not exist: {file_path}"
        )

    if path.suffix.lower() != ".pdf":
        raise ValueError(
            f"Expected a PDF file, received: {path.suffix}"
        )

    document = None

    try:
        document = fitz.open(path)

        if document.page_count == 0:
            raise ValueError("The resume PDF contains no pages.")

        extracted_pages = []

        for page_number, page in enumerate(document, start=1):
            page_text = page.get_text("text").strip()

            if page_text:
                extracted_pages.append(
                    f"--- Page {page_number} ---\n{page_text}"
                )

        complete_text = "\n\n".join(extracted_pages).strip()

        if not complete_text:
            raise ValueError(
                "No readable text was found in the PDF. "
                "The resume may be scanned or image-based."
            )

        return complete_text

    except fitz.FileDataError as exc:
        raise ValueError(
            "The downloaded file is not a valid PDF."
        ) from exc

    finally:
        if document is not None:
            document.close()


def extract_skills(resume_text: str) -> list[str]:
    """
    Find technical skills using controlled keyword matching.
    """

    normalized_text = f" {resume_text.lower()} "
    detected_skills = []

    for skill_name, keywords in SKILL_KEYWORDS.items():
        skill_found = any(
            keyword.lower() in normalized_text
            for keyword in keywords
        )

        if skill_found:
            detected_skills.append(skill_name)

    return sorted(set(detected_skills))


def calculate_resume_statistics(resume_text: str) -> dict[str, Any]:
    """
    Produce simple explainable resume statistics.
    """

    words = resume_text.split()
    lines = [
        line.strip()
        for line in resume_text.splitlines()
        if line.strip()
    ]

    return {
        "character_count": len(resume_text),
        "word_count": len(words),
        "non_empty_lines": len(lines),
    }


def parse_resume(file_path: str) -> dict[str, Any]:
    """
    Run the complete deterministic resume parsing pipeline.
    """

    resume_text = extract_text_from_pdf(file_path)
    skills = extract_skills(resume_text)
    statistics = calculate_resume_statistics(resume_text)

    return {
        "resume_text": resume_text,
        "extracted_skills": skills,
        "statistics": statistics,
    }