from __future__ import annotations

import unittest

from factorio_seed_image_analyser import MapAnalyser, MapAnalyserFactorioCoordinateWrapper, ImageAnalyserPool


class SeedAnalyserUnittest(unittest.TestCase):
    resource_type_with_all = ["iron", "copper", "coal", "water", "all"]

    def my_analyser_func(self, map_analyser: MapAnalyser) -> list[str]:
        self.analyser.append(map_analyser.map_analyser_coordinate_wrapper)
        return []

    def setUp(self):
        self.analyser: list[MapAnalyserFactorioCoordinateWrapper] = []

        for i in range(0, 5):
            resource_colors = {
                "iron": (104, 132, 146),
                "copper": (203, 97, 53),
                "coal": (0, 0, 0),
                "water": (51, 83, 95),
            }
            folder_path = "images/" + str(i)
            file_extension = ".png"
            tiles_per_pixel = 8

            manager = ImageAnalyserPool(None)
            manager.add_folder_of_images_to_analyse(folder_path, file_extension, tiles_per_pixel, resource_colors)
            manager.analyse(self.my_analyser_func, False, True)

    def test_ore_patch_size(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [3328, 3264, 4096, 7104, 5056]
                ore_patches = self.analyser[i].ore_patches[self.resource_type_with_all[i]]
                largest_ore_patch = max(ore_patches)
                self.assertEqual(largest_ore_patch.size, expected_results[i])

    def test_resource_type(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = ["iron", "copper", "coal", "water", "water"]
                ore_patches = self.analyser[i].ore_patches[self.resource_type_with_all[i]]
                largest_ore_patch = max(ore_patches)
                self.assertEqual(largest_ore_patch.resource_type, expected_results[i])

    def test_center_point(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [
                    (-167.23, -233.23),
                    (125.65, -223.53),
                    (289.38, -211.62),
                    (28.61, 251.39),
                    (101.67, 129.11),
                ]
                ore_patches = self.analyser[i].ore_patches[self.resource_type_with_all[i]]
                largest_ore_patch = max(ore_patches)
                center = round(largest_ore_patch.center_point[0], 2), round(largest_ore_patch.center_point[1], 2)
                self.assertEqual(center, expected_results[i])

    def test_analyser_map_seed(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = ["1021", "1811", "4417", "5147", "7585"]
                self.assertEqual(self.analyser[i].map_seed, expected_results[i])

    def test_analyser_resource_types(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_result = ["iron", "copper", "coal", "water"]
                self.assertEqual(self.analyser[i].resource_types, expected_result)

    def test_ore_patch_combined_size(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [21696, 18432, 21312, 12160, 45248]
                ore_patch = self.analyser[i].ore_patch_combined[self.resource_type_with_all[i]]
                self.assertEqual(ore_patch.size, expected_results[i])

    def test_ore_patch_combined_resource_type(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = ["iron", "copper", "coal", "water", "all"]
                ore_patch = self.analyser[i].ore_patch_combined[self.resource_type_with_all[i]]
                self.assertEqual(ore_patch.resource_type, expected_results[i])

    def test_analyser_min_x(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [-384, -384, -384, -240, -336]
                self.assertEqual(self.analyser[i].min_x, expected_results[i])

    def test_analyser_max_x(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [384, 384, 384, 240, 328]
                self.assertEqual(self.analyser[i].max_x, expected_results[i])

    def test_analyser_min_y(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [-384, -384, -384, -296, -288]
                self.assertEqual(self.analyser[i].min_y, expected_results[i])

    def test_analyser_max_y(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [384, 384, 384, 296, 280]
                self.assertEqual(self.analyser[i].max_y, expected_results[i])

    def test_count_resources_in_region_1(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [21696, 18432, 21312, 12160, 45248]
                self.assertEqual(
                    self.analyser[i].count_resources_in_region(
                        self.resource_type_with_all[i],
                        self.analyser[i].min_x,
                        self.analyser[i].min_y,
                        self.analyser[i].max_x,
                        self.analyser[i].max_y
                    ),
                    expected_results[i],
                )

    def test_count_resources_in_region_2(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [1216, 704, 128, 0, 2112]
                self.assertEqual(
                    self.analyser[i].count_resources_in_region(self.resource_type_with_all[i], -96, -40, -16, 40),
                    expected_results[i],
                )

    def test_count_resources_in_region_3(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [1216, 704, 128, 0, 2112]
                self.assertEqual(
                    self.analyser[i].count_resources_in_region(self.resource_type_with_all[i], -90, -33, -22, 33),
                    expected_results[i],
                )

    def test_calculate_min_distance_between_patches(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [304, 422.18, 617.25, 407.92, 97.32]
                ore_patches = self.analyser[i].ore_patches[self.resource_type_with_all[i]]
                ore_patches = sorted(ore_patches)
                patch1 = None
                patch2 = None
                for elem in ore_patches:
                    if elem.size > 500:
                        patch1 = elem
                        break
                for elem in ore_patches:
                    if elem.size > 1000:
                        patch2 = elem
                        break
                result = self.analyser[i].calculate_min_distance_between_patches(patch1, patch2)
                self.assertEqual(round(result, 2), expected_results[i])

    def test_calculate_min_distance_between_patches_dist0(self):
        for i in range(4, 5):
            with self.subTest(i=i):
                expected_result = 0
                ore_patches = self.analyser[i].ore_patches[self.resource_type_with_all[i]]
                ore_patches = sorted(ore_patches)
                patch1 = None
                patch2 = None
                for elem in ore_patches:
                    if elem.size == 512:
                        patch1 = elem
                        break
                for elem in ore_patches:
                    if elem.size == 3008:
                        patch2 = elem
                        break
                result = self.analyser[i].calculate_min_distance_between_patches(patch1, patch2)
                self.assertEqual(round(result, 2), expected_result)

    def test_calculate_min_distance_between_patches_within_region(self):
        for i in range(4, 5):
            with self.subTest(i=i):
                expected_result = 16
                ore_patches = self.analyser[i].ore_patches[self.resource_type_with_all[i]]
                ore_patches = sorted(ore_patches)
                patch1 = None
                patch2 = None
                for elem in ore_patches:
                    if elem.size == 2240:
                        patch1 = elem
                        break
                for elem in ore_patches:
                    if elem.size == 2560:
                        patch2 = elem
                        break
                result = self.analyser[i].calculate_min_distance_between_patches_within_region(
                    patch1, patch2, self.analyser[i].min_x, self.analyser[i].min_y, self.analyser[i].max_x, -30
                )
                self.assertEqual(round(result, 2), expected_result)

    def test_find_longest_consecutive_line_of_resources(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [
                    (72, (-168, -264, -160, -192)),
                    (88, (336, -384, 352, -296)),
                    (112, (360, -320, 384, -208)),
                    (120, (-24, 232, 96, 264)),
                    (136, (-80, 64, 56, 104)),
                ]
                self.assertEqual(
                    self.analyser[i].find_longest_consecutive_line_of_resources_in_region(
                        self.resource_type_with_all[i], 8 * (i + 1), 256 * i
                    ),
                    expected_results[i],
                )

    def test_find_longest_consecutive_line_of_resources_in_region(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [
                    (64, (-40, 8, 24, 16)),
                    (64, (-48, 0, -32, 64)),
                    (96, (-64, -128, -40, -32)),
                    (72, (24, 32, 56, 104)),
                    (136, (-80, 64, 56, 104)),
                ]
                self.assertEqual(
                    self.analyser[i].find_longest_consecutive_line_of_resources_in_region(
                        self.resource_type_with_all[i], 8 * (i + 1), 256 * i, -128, -128, 128, 128
                    ),
                    expected_results[i],
                )

    def test_get_ore_patches_partially_in_region(self):
        for i in range(0, 5):
            with self.subTest(i=i):
                expected_results = [
                    [2368, 2112],
                    [1024, 1536],
                    [3072],
                    [2176],
                    [2240, 960, 2880, 1728, 2560, 1536, 1280, 1344],
                ]
                ore_patches = self.analyser[i].get_ore_patches_partially_in_region(-64, -64, 64, 64)[
                    self.resource_type_with_all[i]
                ]
                self.assertEqual([elem.size for elem in ore_patches], expected_results[i])


resource_type_with_all = ["iron", "copper", "coal", "water", "all"]

if __name__ == "__main__":
    unittest.main()
