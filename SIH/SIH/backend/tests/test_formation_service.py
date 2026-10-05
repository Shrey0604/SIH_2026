import unittest

from app.services.formation_service import (
    clamp01,
    find_formation_at_depth,
    normalized_formation_position,
)


class FormationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.intervals = [
            {
                "id": "tipam",
                "formation_id": "formation-tipam",
                "formation_name": "Tipam",
                "top_md_m": 2800.0,
                "base_md_m": 3090.0,
            },
            {
                "id": "barail",
                "formation_id": "formation-barail",
                "formation_name": "Barail",
                "top_md_m": 3090.0,
                "base_md_m": 3520.0,
            },
            {
                "id": "kopili",
                "formation_id": "formation-kopili",
                "formation_name": "Kopili",
                "top_md_m": 3520.0,
                "base_md_m": 3860.0,
            },
        ]

    def test_clamp01(self) -> None:
        self.assertEqual(clamp01(-2), 0)
        self.assertEqual(clamp01(0.4), 0.4)
        self.assertEqual(clamp01(2), 1)

    def test_normalized_position_and_bounds(self) -> None:
        self.assertEqual(normalized_formation_position(3090, 3090, 3520), 0)
        self.assertEqual(normalized_formation_position(3520, 3090, 3520), 1)
        self.assertEqual(normalized_formation_position(3000, 3090, 3520), 0)
        self.assertEqual(normalized_formation_position(3600, 3090, 3520), 1)
        with self.assertRaises(ValueError):
            normalized_formation_position(100, 200, 200)

    def test_boundary_belongs_to_deeper_formation(self) -> None:
        at_boundary = find_formation_at_depth(self.intervals, 3090)
        self.assertIsNotNone(at_boundary)
        self.assertEqual(at_boundary["formation_name"], "Barail")
        self.assertEqual(at_boundary["normalized_position"], 0)

    def test_final_base_is_included_and_outside_is_none(self) -> None:
        self.assertEqual(
            find_formation_at_depth(self.intervals, 3860)["formation_name"],
            "Kopili",
        )
        self.assertIsNone(find_formation_at_depth(self.intervals, 3860.1))


if __name__ == "__main__":
    unittest.main()

