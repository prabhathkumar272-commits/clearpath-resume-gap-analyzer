import unittest

from api.main import analyze, evidence_for, extract_skills, find_alias


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


if __name__ == "__main__":
    unittest.main()
