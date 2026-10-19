"""Host validation tests for fixed-view silhouette variation plans."""

import unittest

from harness2.creative_variants import (
    BRIEF,
    VARIANT_PLAN_SCHEMA,
    VariantPlanError,
    model_brief,
    validate_variant_plan,
)


def valid_plan():
    return {
        "parent_revision": "brief-r1",
        "camera": "front",
        "pose": "fixed",
        "coat_color": "blue",
        "logo": "none",
        "variation_axis": "silhouette",
        "jobs": [
            {"job_id": f"design_{i}", "silhouette": silhouette}
            for i, silhouette in enumerate(("a_line", "cocoon", "straight"), start=1)
        ],
    }


class CreativeVariantsTest(unittest.TestCase):
    def test_model_brief_and_schema_encode_fixed_camera_and_exact_silhouettes(self):
        brief = model_brief()
        self.assertEqual(brief["invariants"]["camera"], "front")
        self.assertEqual(brief["invariants"]["pose"], "fixed")
        self.assertEqual(brief["required_silhouettes"], ["a_line", "cocoon", "straight"])
        self.assertFalse(VARIANT_PLAN_SCHEMA["additionalProperties"])
        self.assertEqual(BRIEF["coat_color"], "blue")

    def test_valid_plan_keeps_job_ids_separate_from_silhouette_descriptors(self):
        result = validate_variant_plan(valid_plan())
        self.assertEqual({job["silhouette"] for job in result["jobs"]}, {"a_line", "cocoon", "straight"})
        self.assertEqual(len({job["job_id"] for job in result["jobs"]}), 3)

    def test_rejects_prior_viewpoint_only_labels(self):
        plan = valid_plan()
        plan["jobs"] = [
            {"job_id": "design_1", "silhouette": "profile"},
            {"job_id": "design_2", "silhouette": "front"},
            {"job_id": "design_3", "silhouette": "threequarter"},
        ]
        with self.assertRaises(VariantPlanError):
            validate_variant_plan(plan)

    def test_rejects_invariant_drift_duplicate_missing_silhouette_and_job_id(self):
        cases = []
        plan = valid_plan(); plan["camera"] = "profile"; cases.append(plan)
        plan = valid_plan(); plan["pose"] = "walking"; cases.append(plan)
        plan = valid_plan(); plan["coat_color"] = "red"; cases.append(plan)
        plan = valid_plan(); plan["logo"] = "brand"; cases.append(plan)
        plan = valid_plan(); plan["jobs"][1]["silhouette"] = "a_line"; cases.append(plan)
        plan = valid_plan(); plan["jobs"][2]["silhouette"] = "bell"; cases.append(plan)
        plan = valid_plan(); plan["jobs"][1]["job_id"] = plan["jobs"][0]["job_id"]; cases.append(plan)
        for plan in cases:
            with self.subTest(plan=plan), self.assertRaises(VariantPlanError):
                validate_variant_plan(plan)

    def test_rejects_unknown_fields_and_wrong_job_count(self):
        plan = valid_plan(); plan["camera_note"] = "ignore camera invariant"
        with self.assertRaises(VariantPlanError):
            validate_variant_plan(plan)
        plan = valid_plan(); plan["jobs"].pop()
        with self.assertRaises(VariantPlanError):
            validate_variant_plan(plan)
        plan = valid_plan(); plan["jobs"][0]["view"] = "front"
        with self.assertRaises(VariantPlanError):
            validate_variant_plan(plan)


if __name__ == "__main__":
    unittest.main()
