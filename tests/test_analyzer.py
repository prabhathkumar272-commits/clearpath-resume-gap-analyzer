import unittest
from unittest.mock import patch

from fastapi import HTTPException

from api.main import (
    analyze,
    configured_origins,
    consume_rate_limit,
    evidence_for,
    extract_skills,
    find_alias,
    rate_limit_buckets,
    read_resume,
    validate_upload_size,
    validate_resume_upload,
)


class SkillMatchingTests(unittest.TestCase):
    def test_scores_direct_required_and_preferred_skills_with_weights(self):
        result = analyze(
            "Python developer. Built a small API using Python and SQL.",
            "Core skills: Python, SQL, AWS.\nPreferred skills: Pandas.",
        )

        self.assertEqual(result["match_score"], 57)  # (2 + 2) / (2 + 2 + 2 + 1)
        self.assertEqual([item["name"] for item in result["matched_skills"]], ["Python", "SQL"])
        gaps = {item["name"]: item for item in result["missing_skills"]}
        self.assertEqual(gaps["AWS"]["priority"], "required")
        self.assertEqual(gaps["Pandas"]["priority"], "preferred")

    def test_direct_match_includes_redacted_evidence_from_both_documents(self):
        result = analyze(
            "Contact person@example.com. Built Python services.",
            "Required: Python. Please contact recruiter@example.com for details.",
        )

        python = next(item for item in result["matched_skills"] if item["name"] == "Python")
        self.assertEqual(python["match_type"], "direct")
        self.assertIn("Python", python["job_evidence"])
        self.assertIn("Python", python["resume_evidence"])
        self.assertNotIn("person@example.com", python["resume_evidence"])
        self.assertNotIn("recruiter@example.com", python["job_evidence"])

    def test_synonyms_map_to_canonical_skill(self):
        skills = extract_skills("Created RESTful APIs and collaborated with a cross-functional team.")
        names = {skill["name"] for skill in skills}
        self.assertIn("REST APIs", names)
        self.assertIn("Collaboration", names)

    def test_unknown_job_description_has_no_misleading_numeric_score(self):
        result = analyze("Python developer", "A motivated intern will learn on the job and work with the team.")
        self.assertIsNone(result["match_score"])
        self.assertEqual(result["detected_skill_count"], 0)

    def test_alias_matching_observes_word_boundaries(self):
        self.assertIsNone(find_alias("MySQL experience", ["sql"]))
        self.assertIsNotNone(find_alias("Used SQL with PostgreSQL", ["sql"]))

    def test_evidence_without_match_is_empty(self):
        self.assertIsNone(evidence_for("Python and SQL", None))


class ApiSafetyTests(unittest.TestCase):
    def setUp(self):
        rate_limit_buckets.clear()
        self.job_description = "Required: Python, SQL, Git, and Docker. Build reliable services and collaborate with the engineering team."

    def test_cors_includes_the_local_frontend_origin(self):
        self.assertIn("http://localhost:5174", configured_origins)

    def test_analyze_accepts_a_valid_text_resume(self):
        content = b"Python developer with SQL and Git experience. Built API services."
        extension = validate_resume_upload("resume.txt", "text/plain", content)
        result = analyze(read_resume("resume.txt", content, extension), self.job_description)
        self.assertIn("match_score", result)

    def test_analyze_rejects_an_unsupported_extension(self):
        with self.assertRaises(HTTPException) as raised:
            validate_resume_upload("resume.exe", "application/octet-stream", b"Python developer with SQL and Git experience.")
        self.assertEqual(raised.exception.status_code, 415)

    def test_analyze_rejects_a_file_over_the_configured_limit(self):
        with patch("api.main.MAX_FILE_BYTES", 32):
            with self.assertRaises(HTTPException) as raised:
                validate_upload_size(b"x" * 33)
        self.assertEqual(raised.exception.status_code, 413)

    def test_rate_limiter_blocks_after_its_configured_allowance(self):
        with patch("api.main.RATE_LIMIT_REQUESTS", 2), patch("api.main.RATE_LIMIT_WINDOW_SECONDS", 60):
            self.assertIsNone(consume_rate_limit("test-client"))
            self.assertIsNone(consume_rate_limit("test-client"))
            self.assertGreaterEqual(consume_rate_limit("test-client"), 1)


if __name__ == "__main__":
    unittest.main()
