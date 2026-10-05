import unittest

from app.services.analog_service import (
    analog_relevance_score,
    event_midpoint,
    evidence_quality_score,
    haversine_distance_km,
    lookahead_proximity_score,
    project_event_depth,
    spatial_score,
)


class AnalogServiceTests(unittest.TestCase):
    def test_event_midpoint(self) -> None:
        self.assertEqual(event_midpoint(100, None), 100)
        self.assertEqual(event_midpoint(100, 110), 105)

    def test_projection_matches_demo_fixture(self) -> None:
        relative, projected = project_event_depth(
            3294, 3302, 3020, 3440, 3090, 3520
        )
        self.assertAlmostEqual(relative, 0.661905, places=5)
        self.assertAlmostEqual(projected, 3374.619, places=3)

    def test_haversine(self) -> None:
        self.assertEqual(haversine_distance_km(25.7552, 71.3924, 25.7552, 71.3924), 0)
        distance = haversine_distance_km(25.7552, 71.3924, 25.7638, 71.3854)
        self.assertAlmostEqual(distance, 1.186, places=2)

    def test_spatial_score(self) -> None:
        self.assertEqual(spatial_score(0, 5), 1)
        self.assertEqual(spatial_score(5, 5), 0)
        self.assertEqual(spatial_score(10, 5), 0)
        with self.assertRaises(ValueError):
            spatial_score(1, 0)

    def test_lookahead_proximity_score(self) -> None:
        self.assertEqual(lookahead_proximity_score(0, 150), 1)
        self.assertEqual(lookahead_proximity_score(75, 150), 0.5)
        self.assertEqual(lookahead_proximity_score(200, 150), 0)
        with self.assertRaises(ValueError):
            lookahead_proximity_score(20, 0)

    def test_evidence_quality_score(self) -> None:
        self.assertAlmostEqual(evidence_quality_score(0.9, True), 0.93)
        self.assertAlmostEqual(evidence_quality_score(0.9, False), 0.63)

    def test_analog_relevance_decomposition(self) -> None:
        score = analog_relevance_score(True, 0.8, 0.5, 0.9)
        self.assertAlmostEqual(score, 0.845)
        self.assertEqual(analog_relevance_score(False, 0, 0, 0), 0)


if __name__ == "__main__":
    unittest.main()
