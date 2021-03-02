from __future__ import annotations

import os

import numpy as np
from PIL import Image
import cv2
import math

import analyser_coordinate_wrapper


class OrePatch:
    def __init__(self, resource_array: np.ndarray, resource_type: str, side_length_of_pixel_in_tiles: int):
        self.resource_array = resource_array
        self.resource_type = resource_type
        self.size = np.sum(self.resource_array)
        self._contour = None  # lazy initialization (costly operation that will be done just in time in the getter)
        self._center_point = None  # lazy initialization (costly operation that will be done just in time in the getter)
        self.ore_patch_coordinate_wrapper = analyser_coordinate_wrapper.OrePatchCoordinateWrapper(
            self, side_length_of_pixel_in_tiles)

    def display(self) -> None:  # This will open the image in your default image viewer.
        Image.fromarray(self.resource_array * 255, 'L').show()

    @property
    def contour(self):
        if self._contour is None:  # lazy initialization
            contours = cv2.findContours(self.resource_array, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            self._contour = np.reshape(contours[0][0], (contours[0][0].shape[0], contours[0][0].shape[2]))
        return self._contour

    @property
    def center_point(self):
        if self._center_point is None:  # lazy initialization
            moments = cv2.moments(self.resource_array)
            self._center_point = ((moments["m10"] / moments["m00"]), (moments["m01"] / moments["m00"]))
        return self._center_point

    def __lt__(self, other):
        return self.size < other.size

    def __le__(self, other):
        return self.size <= other.size

    def __gt__(self, other):
        return self.size > other.size

    def __ge__(self, other):
        return self.size >= other.size


def _create_all_combined_ore_patches(image: np.ndarray,
                                     resource_colors: dict[str, tuple[int, int, int]],
                                     side_length_of_pixel_in_tiles: int,
                                     ) -> dict[str, OrePatch]:
    ore_patch_combined = {}
    all_resource_array = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
    for resource_type in resource_colors.keys():
        resource_color = resource_colors[resource_type][::-1]  # notice conversion from RGB to BGR with [::-1]
        combined_resource_array = cv2.inRange(image, resource_color, resource_color) // 255
        ore_patch_combined[resource_type] = OrePatch(combined_resource_array, resource_type,
                                                     side_length_of_pixel_in_tiles)
        all_resource_array += combined_resource_array
    ore_patch_combined["all"] = OrePatch(all_resource_array,
                                         "all", side_length_of_pixel_in_tiles)
    return ore_patch_combined


def _find_all_ore_patches(ore_patch_combined: dict[str, OrePatch],
                          resource_types: list[str],
                          side_length_of_pixel_in_tiles: int
                          ) -> dict[str, list[OrePatch]]:
    ore_patches = {"all": []}
    for resource_type in resource_types:
        ore_patches[resource_type] = []
        num_of_labels, image_of_labels = cv2.connectedComponents(ore_patch_combined[resource_type].resource_array)
        for label_value in range(1, num_of_labels):  # skip label_value 0 as it is background
            resource_array_of_single_patch = (image_of_labels == label_value).astype(np.uint8)
            new_ore_patch = OrePatch(resource_array_of_single_patch, resource_type, side_length_of_pixel_in_tiles)
            ore_patches[resource_type].append(new_ore_patch)
        ore_patches["all"].extend(ore_patches[resource_type])
    return ore_patches


class MapAnalyser:
    def __init__(self, image_path: str, resource_colors: dict[str, tuple[int, int, int]],
                 side_length_of_pixel_in_tiles: int):
        image = cv2.imread(image_path)
        self.map_seed = int(os.path.splitext(os.path.basename(image_path))[0])
        self.dimensions = (image.shape[0], image.shape[1])
        self.resource_types = list(resource_colors.keys())
        self.ore_patch_combined = _create_all_combined_ore_patches(
            image, resource_colors, side_length_of_pixel_in_tiles)
        self.ore_patches = _find_all_ore_patches(
            self.ore_patch_combined, self.resource_types, side_length_of_pixel_in_tiles)
        self.map_analyser_coordinate_wrapper = analyser_coordinate_wrapper.MapAnalyserCoordinateWrapper(
            self, side_length_of_pixel_in_tiles)

    def count_resources_in_region(self, start_x: int, start_y: int, end_x: int, end_y: int,
                                  resource_type: str) -> int:
        return np.sum(self.ore_patch_combined[resource_type].resource_array[start_y:end_y, start_x:end_x])

    @staticmethod
    def calculate_min_distance_between_patches(ore_patch: OrePatch, other_ore_patch: OrePatch) -> float:
        return MapAnalyser._calculate_min_distance_between_contours(ore_patch.contour, other_ore_patch.contour)

    @staticmethod
    def calculate_min_distance_between_patches_within_region(ore_patch: OrePatch, other_ore_patch: OrePatch,
                                                             start_x: int, start_y: int, end_x: int, end_y: int
                                                             ) -> float:
        contours_within_region = []
        for patch in (ore_patch, other_ore_patch):
            # remove points in contour that are not in range, tough so read, but performant
            contour_x = patch.contour[:, 0]  # this also creates a copy so the original values don't get overwritten
            contour_y = patch.contour[:, 1]  # this also creates a copy so the original values don't get overwritten
            contour_x[start_x > contour_x] = -1  # mark for removal
            contour_x[contour_x >= end_x] = -1  # mark for removal
            contour_y[start_y > contour_y] = -1  # mark for removal
            contour_y[contour_y >= end_y] = -1  # mark for removal
            # by adding 1 to the array and interpreting at as a bool, the previous -1 now becomes False, all other True
            # if any of the x values is marked for removal we also want to remove it's y counterpart and vice versa
            # so we use a logical and to combine the array and than duplicate it, so x and y get the same bool value
            condition = np.array([np.logical_and(contour_x + 1, contour_y + 1), ] * 2).transpose()
            contour_within_region = np.ndarray.reshape(patch.contour[condition], (-1, 2))  # filter array by condition
            if not contour_within_region.size:
                return float('inf')  # fast return if any list of contour points is empty after filtering
            contours_within_region.append(contour_within_region)
        return MapAnalyser._calculate_min_distance_between_contours(contours_within_region[0],
                                                                    contours_within_region[1])

    @staticmethod
    def combine_ore_patches(list_of_ore_patches: list[OrePatch], resource_type: str,
                            dimensions: tuple[int, int], side_length_of_pixel_in_tiles: int) -> OrePatch:
        """Merges a list of ore patches into a virtually single one, that may not even be connected"""
        combined_resource_array = np.zeros((dimensions[0], dimensions[1]), dtype=np.uint8)  # in case the list is empty
        for ore_patch in list_of_ore_patches:
            combined_resource_array += ore_patch.resource_array
        return OrePatch(combined_resource_array, resource_type, side_length_of_pixel_in_tiles)

    @staticmethod
    def _calculate_min_distance_between_contours(contour: np.ndarray, other_contour: np.ndarray) -> float:
        """Calculates the minimum free space between two sets of points. This will be 0 for two adjacent points"""
        # good luck trying to understand this: Using matrix operations makes this 100x faster than regular python code.
        # We are starting with 2 arrays of vectors that contain the points of each contour.
        # Example - expected distance is 0 since the point (5, 6) and (4, 6) are adjacent:
        #   contour             other_contour
        #   [[1 2]              [[7 8]
        #    [3 4]               [4 6]
        #    [5 6]]              [1 4]]
        # We want to calculate the delta_x and delta_y of every point with every other point.
        # So the first step is to separate the x and y values.
        contour_x = contour[:, 0]
        other_contour_x = other_contour[:, 0]
        contour_y = contour[:, 1]
        other_contour_y = other_contour[:, 1]
        #   contour_x           other_contour_x             contour_y           other_contour_y
        #   [1 3 5]             [7 4 1]                     [2 4 6]             [8 6 4]
        # We copy the row and transpose just one on the resulting arrays.
        # Now we can run operations on every x with every other x - same for y.
        contour_x_matrix = np.array([contour_x, ] * other_contour_x.shape[0]).transpose()
        other_contour_x_matrix = np.array([other_contour_x, ] * contour_x.shape[0])
        contour_y_matrix = np.array([contour_y, ] * other_contour_y.shape[0]).transpose()
        other_contour_y_matrix = np.array([other_contour_y, ] * contour_y.shape[0])
        #   contour_x_matrix    other_contour_x_matrix      contour_y_matrix    other_contour_y_matrix
        #   [[1 1 1]            [[7 4 1]                    [[2 2 2]            [[8 6 4]
        #    [3 3 3]             [7 4 1]                    [4 4 4]              [8 6 4]
        #    [5 5 5]]            [7 4 1]]                   [6 6 6]]             [8 6 4]]
        # To get the x_delta of each pair we simply subtract the arrays.
        diff_x_matrix = np.absolute(other_contour_x_matrix - contour_x_matrix)
        diff_y_matrix = np.absolute(other_contour_y_matrix - contour_y_matrix)
        #   diff_x_matrix                                   diff_y_matrix
        #   [[6 3 0]                                        [[6 4 2]
        #    [4 1 2]                                         [4 2 0]
        #    [2 1 4]]                                        [2 0 2]]
        # Adjacent tiles have a distance of 0, but a delta of 1.
        # This is why we have to reduce the delta by 1 for each dimension. Also is the reason for the abs() previously.
        diff_x_matrix[diff_x_matrix > 0] -= 1
        diff_y_matrix[diff_y_matrix > 0] -= 1
        #   diff_x_matrix                                   diff_y_matrix
        #   [[5 2 0]                                        [[5 3 1]
        #    [3 0 1]                                         [3 1 0]
        #    [1 0 3]]                                        [1 0 1]]
        # With the deltas of each dimension we can now simply apply the euclidean norm to get the distances.
        # sqrt(x²+y²): First square the x and y values and add them up.
        x_matrix_sq = np.square(diff_x_matrix)
        y_matrix_sq = np.square(diff_y_matrix)
        distance_matrix_sq = x_matrix_sq + y_matrix_sq
        # distance_matrix_sq min value is at 3, 2 which is the point pair (5, 6) and (4, 6) that are adjacent.
        #   x_matrix_sq         y_matrix_sq                 distance_matrix_sq
        #   [[25 4 0]            [[25 9 1]                  [[50 13  1]
        #    [ 9 0 1]      +      [ 9 1 0]         =         [18  1  1]
        #    [ 1 0 9]]            [ 1 0 1]]                  [ 2  0 10]]
        # sqrt is a costly function, so we first find the smallest distance and only use sqrt() on the final value.
        return math.sqrt(np.min(distance_matrix_sq))
