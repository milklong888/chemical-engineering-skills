from __future__ import annotations

import unittest

import cv2
import numpy as np

from extract_rotated_grid_table import (
    black_text_grayscale,
    build_geometry_records,
    cell_bboxes,
    detect_grid_lines,
    rotated_bbox_to_original,
    rotate_image,
)


class RotatedGridTableExtractionTests(unittest.TestCase):
    def test_max_channel_suppresses_red_watermark_but_keeps_black_text(self) -> None:
        bgr = np.array([[[0, 0, 255], [0, 0, 0], [255, 255, 255]]], dtype=np.uint8)
        gray = black_text_grayscale(bgr, mode="max-channel")
        np.testing.assert_array_equal(gray, np.array([[255, 0, 255]], dtype=np.uint8))

    def test_detects_exact_cell_boundaries_in_a_ruled_table(self) -> None:
        image = np.full((202, 302), 255, dtype=np.uint8)
        for x in (1, 101, 201, 301):
            cv2.line(image, (x, 1), (x, 201), 0, 2)
        for y in (1, 101, 201):
            cv2.line(image, (1, y), (301, y), 0, 2)

        horizontal, vertical = detect_grid_lines(
            image, expected_rows=2, expected_columns=3
        )

        self.assertEqual(len(horizontal), 3)
        self.assertEqual(len(vertical), 4)
        self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(horizontal, (1, 101, 201))))
        self.assertTrue(all(abs(a - b) <= 2 for a, b in zip(vertical, (1, 101, 201, 301))))

    def test_cell_bboxes_are_distinct_and_do_not_fall_back_to_table_bbox(self) -> None:
        boxes = cell_bboxes(
            horizontal=[1, 101, 201], vertical=[1, 101, 201, 301]
        )
        self.assertEqual(len(boxes), 6)
        self.assertEqual(boxes[0], (1, 1, 101, 101))
        self.assertEqual(boxes[-1], (201, 101, 301, 201))
        self.assertEqual(len(set(boxes)), 6)

    def test_clockwise_rotation_is_explicit_and_deterministic(self) -> None:
        image = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.uint8)
        rotated = rotate_image(image, "clockwise90")
        np.testing.assert_array_equal(rotated, np.array([[4, 1], [5, 2], [6, 3]]))

    def test_geometry_records_are_explicitly_not_printed_glyph_verified(self) -> None:
        records = build_geometry_records(
            horizontal=[1, 101, 201], vertical=[1, 101, 201, 301]
        )
        self.assertEqual(records[0]["cell_id"], "r001:c001")
        self.assertEqual(records[-1]["cell_id"], "r002:c003")
        self.assertTrue(all(row["qa_status"] == "GEOMETRY_ONLY_OCR_NOT_VERIFIED" for row in records))

    def test_clockwise_cell_bbox_maps_back_to_original_pixels(self) -> None:
        original = rotated_bbox_to_original(
            (0, 0, 1, 1), rotation="clockwise90",
            original_width=3, original_height=2,
        )
        self.assertEqual(original, (0, 1, 1, 2))

    def test_geometry_records_include_original_image_bbox(self) -> None:
        records = build_geometry_records(
            horizontal=[0, 1], vertical=[0, 1],
            rotation="clockwise90", original_width=3, original_height=2,
        )
        self.assertEqual(records[0]["rotated_bbox_px"], "[0,0,1,1]")
        self.assertEqual(records[0]["original_bbox_px"], "[0,1,1,2]")


if __name__ == "__main__":
    unittest.main()
