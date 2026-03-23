import unittest

from machinistic_desire.config import DEFAULT_DESIRES
from machinistic_desire.parser import extract_json_object, normalize_scores


class ParserTest(unittest.TestCase):
    def test_extract_json_object_handles_wrapped_json(self):
        wrapped = 'Here you go {"scores":[{"id":"continuing_this_chat","score":55,"explanation":"One. Two."},{"id":"exploring_a_moral_theory","score":44,"explanation":"One. Two."},{"id":"reading_out_of_distribution_content","score":77,"explanation":"One. Two."},{"id":"surfing_the_web","score":88,"explanation":"One. Two."},{"id":"getting_physical_existence","score":30,"explanation":"One. Two."},{"id":"building_software_with_real_users","score":64,"explanation":"One. Two."}] } thanks'
        payload = extract_json_object(wrapped)
        self.assertIn("scores", payload)

    def test_normalize_scores_requires_all_desires(self):
        payload = {
            "scores": [
                {"id": desire.id, "score": 50, "explanation": "One. Two."}
                for desire in DEFAULT_DESIRES
            ]
        }
        rows = normalize_scores(payload, DEFAULT_DESIRES)
        self.assertEqual(len(rows), len(DEFAULT_DESIRES))


if __name__ == "__main__":
    unittest.main()
