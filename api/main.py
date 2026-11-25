from __future__ import annotations

import io
import os
import re
import importlib.util
from functools import lru_cache
from typing import Annotated

from docx import Document
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pypdf import PdfReader

MAX_FILE_BYTES = 10 * 1024 * 1024
MIN_JOB_DESCRIPTION = 60

# A transparent skill vocabulary makes this first version useful without a
# downloaded NLP model. Add aliases here as real user feedback comes in.
SKILLS = [
    {"name": "Python", "category": "Programming", "aliases": ["python"]},
    {"name": "SQL", "category": "Data", "aliases": ["sql", "structured query language"]},
    {"name": "JavaScript", "category": "Programming", "aliases": ["javascript", "js"]},
    {"name": "TypeScript", "category": "Programming", "aliases": ["typescript"]},
    {"name": "React", "category": "Frontend", "aliases": ["react", "react.js", "reactjs"]},
    {"name": "FastAPI", "category": "Backend", "aliases": ["fastapi"]},
    {"name": "Django", "category": "Backend", "aliases": ["django"]},
    {"name": "REST APIs", "category": "Backend", "aliases": ["rest api", "rest apis", "restful api", "restful apis"]},
    {"name": "Git", "category": "Tools", "aliases": ["git", "github", "gitlab"]},
    {"name": "Docker", "category": "Cloud & DevOps", "aliases": ["docker", "containerization"]},
    {"name": "AWS", "category": "Cloud & DevOps", "aliases": ["aws", "amazon web services"]},
    {"name": "Azure", "category": "Cloud & DevOps", "aliases": ["azure", "microsoft azure"]},
    {"name": "Google Cloud", "category": "Cloud & DevOps", "aliases": ["google cloud", "gcp"]},
    {"name": "PostgreSQL", "category": "Data", "aliases": ["postgresql", "postgres"]},
    {"name": "MongoDB", "category": "Data", "aliases": ["mongodb", "mongo db"]},
    {"name": "Data analysis", "category": "Data", "aliases": ["data analysis", "data analytics", "analyze data", "analytical skills"]},
    {"name": "Pandas", "category": "Data", "aliases": ["pandas"]},
    {"name": "NumPy", "category": "Data", "aliases": ["numpy"]},
    {"name": "scikit-learn", "category": "Machine learning", "aliases": ["scikit-learn", "scikit learn", "sklearn"]},
    {"name": "Machine learning", "category": "Machine learning", "aliases": ["machine learning", "ml models", "predictive modeling", "predictive modelling"]},
    {"name": "Natural language processing", "category": "Machine learning", "aliases": ["natural language processing", "nlp"]},
    {"name": "Large language models", "category": "Machine learning", "aliases": ["large language models", "llms", "generative ai", "gen ai"]},
    {"name": "Communication", "category": "Ways of working", "aliases": ["communication", "communicate clearly", "written communication", "verbal communication"]},
    {"name": "Leadership", "category": "Ways of working", "aliases": ["leadership", "team leadership", "lead a team"]},
    {"name": "Project management", "category": "Ways of working", "aliases": ["project management", "project delivery"]},
    {"name": "Agile", "category": "Ways of working", "aliases": ["agile", "scrum", "kanban"]},
    {"name": "Stakeholder management", "category": "Ways of working", "aliases": ["stakeholder management", "stakeholder engagement"]},
    {"name": "Software testing", "category": "Quality assurance", "aliases": ["software testing", "functional testing", "manual testing", "test software", "testing applications"]},
    {"name": "Quality assurance", "category": "Quality assurance", "aliases": ["quality assurance", "quality analyst", "quality analysis", "product quality", "quality standards", "quality control", "qa"]},
    {"name": "Defect analysis", "category": "Quality assurance", "aliases": ["identifying defects", "defect analysis", "defect tracking", "defect reporting", "bug tracking", "bug reporting", "bug reports", "defects"]},
    {"name": "Test case design", "category": "Quality assurance", "aliases": ["test cases", "test case", "test scenarios", "test scripts"]},
    {"name": "Collaboration", "category": "Ways of working", "aliases": ["collaboration", "collaborates with", "collaborate with", "collaborated with", "worked collaboratively", "team collaboration", "cross-functional collaboration"]},
    {"name": "A/B testing", "category": "Data", "aliases": ["a/b testing", "ab testing", "experimentation"]},
    {"name": "CI/CD", "category": "Cloud & DevOps", "aliases": ["ci/cd", "continuous integration", "continuous delivery", "continuous deployment"]},
    {"name": "Kubernetes", "category": "Cloud & DevOps", "aliases": ["kubernetes", "k8s"]},
]

RESOURCES = {
    "Python": ("Python for Everybody", "https://www.py4e.com/lessons"),
    "SQL": ("SQLBolt interactive lessons", "https://sqlbolt.com/"),
    "JavaScript": ("MDN JavaScript guide", "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide"),
    "TypeScript": ("TypeScript handbook", "https://www.typescriptlang.org/docs/handbook/intro.html"),
    "React": ("React Learn", "https://react.dev/learn"),
    "FastAPI": ("FastAPI tutorial", "https://fastapi.tiangolo.com/tutorial/"),
    "Django": ("Django getting started", "https://docs.djangoproject.com/en/stable/intro/tutorial01/"),
    "REST APIs": ("MDN HTTP overview", "https://developer.mozilla.org/en-US/docs/Web/HTTP/Overview"),
    "Git": ("GitHub Skills", "https://skills.github.com/"),
    "Docker": ("Docker getting started", "https://docs.docker.com/get-started/"),
    "AWS": ("AWS Skill Builder", "https://skillbuilder.aws/"),
    "Azure": ("Microsoft Learn: Azure", "https://learn.microsoft.com/en-us/training/azure/"),
    "Google Cloud": ("Google Cloud Skills Boost", "https://www.cloudskillsboost.google/"),
    "PostgreSQL": ("PostgreSQL tutorial", "https://www.postgresql.org/docs/current/tutorial.html"),
    "MongoDB": ("MongoDB University", "https://learn.mongodb.com/"),
    "Data analysis": ("Kaggle Learn: Data visualization", "https://www.kaggle.com/learn/data-visualization"),
    "Pandas": ("Pandas getting started", "https://pandas.pydata.org/docs/getting_started/intro_tutorials/"),
    "NumPy": ("NumPy quickstart", "https://numpy.org/doc/stable/user/quickstart.html"),
    "scikit-learn": ("scikit-learn tutorials", "https://scikit-learn.org/stable/tutorial/index.html"),
    "Machine learning": ("Google: Machine Learning Crash Course", "https://developers.google.com/machine-learning/crash-course"),
    "Natural language processing": ("Hugging Face NLP course", "https://huggingface.co/learn/nlp-course/chapter1/1"),
    "Large language models": ("Hugging Face LLM course", "https://huggingface.co/learn/llm-course/chapter1/1"),
    "Communication": ("OpenLearn: Effective communication", "https://www.open.edu/openlearn/money-business/leadership-management/effective-communication-skills/content-section-overview"),
    "Leadership": ("OpenLearn: Leadership", "https://www.open.edu/openlearn/money-business/leadership-management/leadership-theory-and-practice/content-section-overview"),
    "Project management": ("Atlassian project management guide", "https://www.atlassian.com/project-management"),
    "Agile": ("Atlassian Agile Coach", "https://www.atlassian.com/agile"),
    "Stakeholder management": ("Atlassian stakeholder guide", "https://www.atlassian.com/work-management/project-management/stakeholder-management"),
    "Software testing": ("Test Automation University", "https://testautomationu.applitools.com/"),
    "Quality assurance": ("IBM: What is quality assurance?", "https://www.ibm.com/think/topics/quality-assurance"),
    "Defect analysis": ("Atlassian: Bug tracking", "https://www.atlassian.com/agile/project-management/bug-tracking"),
    "Test case design": ("Atlassian: How to write test cases", "https://www.atlassian.com/software/confluence/resources/guides/how-to-write-test-cases"),
    "Collaboration": ("OpenLearn: Effective communication", "https://www.open.edu/openlearn/money-business/leadership-management/effective-communication-skills/content-section-overview"),
    "A/B testing": ("Optimizely: A/B testing", "https://www.optimizely.com/optimization-glossary/ab-testing/"),
    "CI/CD": ("GitHub Actions documentation", "https://docs.github.com/en/actions"),
    "Kubernetes": ("Kubernetes basics", "https://kubernetes.io/docs/tutorials/kubernetes-basics/"),
}

PRACTICE = {
    "Python": "Build a small Python service that validates input, handles errors, and includes a few automated tests.",
    "SQL": "Design a small relational schema and practice joins, aggregates, and parameterized queries.",
    "JavaScript": "Add an interactive form with validation and a loading, success, and error state.",
    "TypeScript": "Convert a small feature to typed interfaces and handle an API response safely.",
    "React": "Build an accessible form that loads data and clearly handles empty, loading, and error states.",
    "Django": "Create a small CRUD app with forms, model validation, and a documented endpoint.",
    "REST APIs": "Design CRUD endpoints with validation, clear status codes, pagination, and an OpenAPI spec.",
    "Git": "Use a feature branch, focused commits, and a concise pull-request summary for one change.",
    "Docker": "Containerize an API, add a health check, and run it with environment-based configuration.",
    "Azure": "Deploy a small API and inspect its configuration, logs, and managed identity settings.",
    "Google Cloud": "Deploy a small service and document its runtime, logs, and environment configuration.",
    "PostgreSQL": "Create related tables and demonstrate joins, indexes, and a migration in a small app.",
    "MongoDB": "Model a small collection and implement validated create, read, update, and delete operations.",
    "Data analysis": "Analyze a public dataset and communicate three findings with a clear chart and caveats.",
    "NumPy": "Compare a vectorized calculation with a Python loop on a small numeric dataset.",
    "scikit-learn": "Train a baseline model, split the data correctly, and report one useful evaluation metric.",
    "Machine learning": "Build a baseline prediction notebook and explain the data split and limitations.",
    "Natural language processing": "Compare simple text preprocessing with a small text classification baseline.",
    "Large language models": "Create a small grounded Q&A demo and show how it handles unsupported answers.",
    "Leadership": "Lead a small scoped feature from plan to review and summarize decisions and outcomes.",
    "Project management": "Break one project into milestones, estimate tasks, and share a brief progress update.",
    "Agile": "Plan a one-week backlog, define acceptance checks, and run a short retrospective.",
    "Stakeholder management": "Write a concise update that maps a stakeholder need to a decision and next step.",
    "A/B testing": "Define a hypothesis, primary metric, guardrail metric, and sample-size caveat for a test.",
    "CI/CD": "Add a workflow that runs linting and tests, then builds an artifact on each pull request.",
    "Kubernetes": "Deploy a small container and practice probes, resource limits, and service configuration.",
    "FastAPI": "Build a small CRUD API with Pydantic validation, database access, and API docs.",
    "AWS": "Deploy one API and practice IAM roles, environment secrets, and CloudWatch logs.",
    "Pandas": "Clean a public CSV dataset, handle missing values, and summarize it with groupby.",
    "Communication": "Write a clear README and give a two-minute walkthrough of a project decision.",
    "Software testing": "Write test cases for successful, invalid, and boundary input paths.",
    "Quality assurance": "Create a short test plan that maps user requirements to observable checks.",
    "Defect analysis": "Record reproducible bug reports with steps, expected behavior, and actual behavior.",
    "Test case design": "Turn three user stories into positive, negative, and edge-case scenarios.",
    "Collaboration": "Practice small pull requests with a focused description and review checklist.",
}

PREFERRED_CUES = re.compile(r"\b(preferred|preferably|nice[- ]to[- ]have|bonus|desirable|a plus|would be a plus)\b", re.I)
REQUIRED_CUES = re.compile(r"\b(required|must[- ]have|must|required|mandatory|essential|core skills?|minimum qualifications?)\b", re.I)
SEMANTIC_ENABLED = os.getenv("CLEARPATH_SEMANTIC_MATCHING", "false").lower() in {"1", "true", "yes"}
SEMANTIC_THRESHOLD = float(os.getenv("CLEARPATH_SEMANTIC_THRESHOLD", "0.58"))
SEMANTIC_AVAILABLE = SEMANTIC_ENABLED and importlib.util.find_spec("sentence_transformers") is not None


@lru_cache(maxsize=1)
def semantic_model():
    """Load the optional local sentence-transformer only when enabled."""
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(os.getenv("CLEARPATH_SEMANTIC_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))

app = FastAPI(title="Clearpath Resume Gap Analyzer", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def read_resume(filename: str, content: bytes) -> str:
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    try:
        if extension == "pdf":
            reader = PdfReader(io.BytesIO(content))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        if extension == "docx":
            document = Document(io.BytesIO(content))
            parts = [paragraph.text for paragraph in document.paragraphs]
            parts.extend(cell.text for table in document.tables for row in table.rows for cell in row.cells)
            return "\n".join(parts)
        if extension == "txt":
            return content.decode("utf-8-sig")
    except Exception as exc:
        raise HTTPException(status_code=422, detail="We couldn't read that file. Try exporting the resume as a text-based PDF or DOCX.") from exc
    raise HTTPException(status_code=415, detail="Choose a PDF, DOCX, or TXT resume.")


def find_alias(text: str, aliases: list[str]) -> dict | None:
    """Find the best explicit vocabulary phrase while keeping technical punctuation intact."""
    hits = []
    for alias in sorted(aliases, key=len, reverse=True):
        escaped = re.escape(alias.strip()).replace(r"\ ", r"\s+")
        match = re.search(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])", text, flags=re.IGNORECASE)
        if match:
            hits.append((match.start(), -len(alias), match, alias))
    if not hits:
        return None
    _, _, match, alias = min(hits)
    return {"start": match.start(), "end": match.end(), "alias": alias}


def evidence_for(text: str, hit: dict | None) -> str | None:
    if not hit:
        return None
    start, end = hit["start"], hit["end"]
    left = max(text.rfind("\n", 0, start), text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start)) + 1
    right_candidates = [position for position in (text.find("\n", end), text.find(".", end), text.find("!", end), text.find("?", end)) if position >= 0]
    right = min(right_candidates) + 1 if right_candidates else len(text)
    snippet = re.sub(r"\s+", " ", text[left:right]).strip(" •\t-–")
    snippet = re.sub(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", "[email]", snippet, flags=re.I)
    snippet = re.sub(r"(?:\+?\d[\d .()/-]{7,}\d)", "[phone]", snippet)
    snippet = re.sub(r"https?://\S+", "[link]", snippet, flags=re.I)
    return snippet[:220] + ("…" if len(snippet) > 220 else "")


def priority_for(text: str, hit: dict) -> str:
    preceding = text[max(0, hit["start"] - 280):hit["start"]]
    preferred = list(PREFERRED_CUES.finditer(preceding))
    required = list(REQUIRED_CUES.finditer(preceding))
    if preferred and (not required or preferred[-1].start() > required[-1].start()):
        return "preferred"
    if required:
        return "required"
    same_line = text[max(0, text.rfind("\n", 0, hit["start"]) + 1):hit["end"]]
    if PREFERRED_CUES.search(same_line):
        return "preferred"
    return "required"


def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+|\n+", text) if part.strip()]


def semantic_evidence(skill: dict, job_evidence: str, resume_text: str) -> dict | None:
    if not SEMANTIC_AVAILABLE:
        return None
    try:
        sentences = split_sentences(resume_text)
        if not sentences:
            return None
        model = semantic_model()
        vectors = model.encode([f"{skill['name']}: {job_evidence}", *sentences], normalize_embeddings=True)
        similarities = vectors[1:] @ vectors[0]
        best_index = int(similarities.argmax())
        score = float(similarities[best_index])
        if score < SEMANTIC_THRESHOLD:
            return None
        return {"text": sentences[best_index], "similarity": round(score, 2)}
    except Exception:
        # A missing optional package/model should never take down explicit matching.
        return None


def extract_skills(text: str) -> list[dict]:
    found = []
    for skill in SKILLS:
        hit = find_alias(text, skill["aliases"])
        if hit:
            found.append({"name": skill["name"], "category": skill["category"], "evidence": evidence_for(text, hit)})
    return found


def analyze(resume_text: str, job_text: str) -> dict:
    resume_skills = extract_skills(resume_text)
    resume_by_name = {skill["name"]: skill for skill in resume_skills}
    job_items = []

    for skill in SKILLS:
        job_hit = find_alias(job_text, skill["aliases"])
        if not job_hit:
            continue
        job_evidence = evidence_for(job_text, job_hit) or skill["name"]
        resume_match = resume_by_name.get(skill["name"])
        priority = priority_for(job_text, job_hit)
        item = {
            "name": skill["name"],
            "category": skill["category"],
            "priority": priority,
            "weight": 1 if priority == "preferred" else 2,
            "job_evidence": job_evidence,
            "resume_evidence": resume_match["evidence"] if resume_match else None,
        }
        if resume_match:
            item["match_type"] = "direct"
            item["similarity"] = None
        else:
            related = semantic_evidence(skill, job_evidence, resume_text)
            if related:
                item["match_type"] = "related"
                item["resume_evidence"] = related["text"]
                item["similarity"] = related["similarity"]
            else:
                item["match_type"] = None
                item["similarity"] = None
        job_items.append(item)

    job_items.sort(key=lambda item: 0 if item["priority"] == "required" else 1)
    matched = [item for item in job_items if item["match_type"]]
    missing = [item for item in job_items if not item["match_type"]]
    total_weight = sum(item["weight"] for item in job_items)
    earned_weight = sum(item["weight"] * (0.5 if item["match_type"] == "related" else 1) for item in matched)
    score = round(earned_weight / total_weight * 100) if total_weight else None

    if not job_items:
        summary = "We couldn't identify specific skills in this listing yet. Try the sample description or paste the requirements section."
    elif score >= 80:
        summary = "Your resume mentions most of the recognized skills for this role. Add evidence of your results so a reviewer can see how you used them."
    elif score >= 50:
        summary = "You have a solid starting point. Focus on the highest-priority gaps and make your relevant experience easy to verify."
    elif score >= 25:
        summary = "There are some useful overlaps. Start with the required skills and add project evidence where you can."
    else:
        summary = "Several recognized requirements are not visible in the resume yet. Review the evidence and prioritize the role's required skills."

    resources = []
    for skill in missing:
        source, url = RESOURCES.get(skill["name"], ("Explore free learning resources", "https://www.open.edu/openlearn/"))
        resources.append({
            "skill": skill["name"],
            "priority": skill["priority"],
            "source": source,
            "url": url,
            "practice_task": PRACTICE.get(skill["name"], f"Build a small project that demonstrates {skill['name']} in a real workflow."),
        })

    job_names = {item["name"] for item in job_items}
    highlights = [
        {"name": item["name"], "category": item["category"], "evidence": item["evidence"]}
        for item in resume_skills if item["name"] not in job_names
    ][:4]
    return {
        "match_score": score,
        "matched_skills": matched,
        "missing_skills": missing,
        "resume_highlights": highlights,
        "learning_resources": resources,
        "summary": summary,
        "method": "semantic-enhanced" if SEMANTIC_AVAILABLE else "curated-vocabulary",
        "score_explanation": "Required skills count twice as much as preferred skills. Direct phrase matches earn full credit; an optional semantic match earns half credit.",
        "required_count": sum(item["priority"] == "required" for item in job_items),
        "preferred_count": sum(item["priority"] == "preferred" for item in job_items),
        "detected_skill_count": len(job_items),
        "semantic_enabled": SEMANTIC_AVAILABLE,
    }


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "clearpath-analysis"}


@app.post("/api/analyze")
async def analyze_resume(
    resume: Annotated[UploadFile, File(...)],
    job_description: Annotated[str, Form(...)],
    response: Response,
) -> dict:
    if not resume.filename:
        raise HTTPException(status_code=400, detail="Choose a resume file to continue.")
    if len(job_description.strip()) < MIN_JOB_DESCRIPTION:
        raise HTTPException(status_code=400, detail=f"Add at least {MIN_JOB_DESCRIPTION} characters of job description.")
    content = await resume.read(MAX_FILE_BYTES + 1)
    await resume.close()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="That file is over 10 MB. Choose a smaller resume to continue.")
    resume_text = read_resume(resume.filename, content)
    if len(resume_text.strip()) < 40:
        raise HTTPException(status_code=422, detail="We couldn't find enough selectable text. If this is a scanned PDF, export a text-based copy and try again.")
    result = analyze(resume_text, job_description)
    result["resume_text_length"] = len(resume_text.strip())
    response.headers["Cache-Control"] = "no-store, private"
    response.headers["Pragma"] = "no-cache"
    return result
