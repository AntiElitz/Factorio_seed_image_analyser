from __future__ import annotations

import os
from typing import Optional

import numpy as np
from PIL import Image
import cv2
import math

import analyser_factorio_coordinate_wrapper


class OrePatch:
    def __init__(self, resource_array: np.ndarray, resource_type: str, tiles_per_pixel: int):
        self.resource_array = resource_array
        self.resource_type = resource_type
        self.size = np.sum(self.resource_array)
        self._contour = None  # lazy initialization (costly operation that will be done just in time in the getter)
        self._center_point = None  # lazy initialization (costly operation that will be done just in time in the getter)
        self.ore_patch_coordinate_wrapper = analyser_factorio_coordinate_wrapper.OrePatchFactorioCoordinateWrapper(
            self, tiles_per_pixel
        )

    def display(self) -> None:  # This will open the image in your default image viewer.
        """This will open the image of the ore patch in your default image viewer. Very slow. Use for debug only"""
        Image.fromarray(self.resource_array * 255, "L").show()

    @property
    def contour(self):
        if self._contour is None:  # lazy initialization
            """A 2d array that contains various points that define the contour of the ore patch"""
            contours = cv2.findContours(self.resource_array, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            self._contour = np.reshape(contours[0][0], (contours[0][0].shape[0], contours[0][0].shape[2]))
        return self._contour

    @property
    def center_point(self):
        """Return the weighted center of an ore patch in a pixel point"""
        if self._center_point is None:  # lazy initialization
            moments = cv2.moments(self.resource_array)
            self._center_point = (
                (moments["m10"] / moments["m00"]),
                (moments["m01"] / moments["m00"]),
            )
        return self._center_point

    def __lt__(self, other):
        return self.size < other.size

    def __le__(self, other):
        return self.size <= other.size

    def __gt__(self, other):
        return self.size > other.size

    def __ge__(self, other):
        return self.size >= other.size


def _create_all_combined_ore_patches(
    image: np.ndarray,
    resource_colors: dict[str, tuple[int, int, int]],
    tiles_per_pixel: int,
) -> dict[str, OrePatch]:
    """Filters the original image by each defined resource-colors and creates a patch from it"""
    ore_patch_combined = {}
    all_resource_array = np.zeros((image.shape[0], image.shape[1]), dtype=np.uint8)
    for resource_type, resource_color in resource_colors.items():
        resource_color = resource_color[::-1]  # notice conversion from RGB to BGR with [::-1]
        combined_resource_array = cv2.inRange(image, resource_color, resource_color) // 255
        ore_patch_combined[resource_type] = OrePatch(combined_resource_array, resource_type, tiles_per_pixel)
        all_resource_array += combined_resource_array
    ore_patch_combined["all"] = OrePatch(all_resource_array, "all", tiles_per_pixel)
    return ore_patch_combined


def _find_all_ore_patches(
    ore_patch_combined: dict[str, OrePatch],
    resource_types: list[str],
    tiles_per_pixel: int,
) -> dict[str, list[OrePatch]]:
    """separates ore patches combined by resource type into individual ore patches"""
    ore_patches: dict[str, list[OrePatch]] = {"all": []}
    for resource_type in resource_types:
        ore_patches[resource_type] = []
        num_of_labels, image_of_labels = cv2.connectedComponents(ore_patch_combined[resource_type].resource_array)
        for label_value in range(1, num_of_labels):  # skip label_value 0 as it is background
            resource_array_of_single_patch = (image_of_labels == label_value).astype(np.uint8)
            new_ore_patch = OrePatch(resource_array_of_single_patch, resource_type, tiles_per_pixel)
            ore_patches[resource_type].append(new_ore_patch)
        ore_patches["all"].extend(ore_patches[resource_type])
    return ore_patches


class MapAnalyser:
    def __init__(
        self,
        image_path: str,
        resource_colors: dict[str, tuple[int, int, int]],
        tiles_per_pixel: int,
    ):
        image = cv2.imread(image_path)
        self.map_seed = os.path.splitext(os.path.basename(image_path))[0]
        self.dimensions = (image.shape[0], image.shape[1])
        self.resource_types = list(resource_colors)
        self.ore_patch_combined = _create_all_combined_ore_patches(image, resource_colors, tiles_per_pixel)
        self.ore_patches = _find_all_ore_patches(self.ore_patch_combined, self.resource_types, tiles_per_pixel)
        self.map_analyser_coordinate_wrapper = (
            analyser_factorio_coordinate_wrapper.MapAnalyserFactorioCoordinateWrapper(self, tiles_per_pixel)
        )

    @property
    def min_x(self) -> int:
        return 0

    @property
    def min_y(self) -> int:
        return 0

    @property
    def max_x(self) -> int:
        return self.dimensions[1]

    @property
    def max_y(self) -> int:
        return self.dimensions[0]

    def get_ore_patches_partially_in_region(self, start_x: int, start_y: int, end_x: int, end_y: int):
        filtered_ore_patches = dict.fromkeys(self.ore_patches)  # this includes "all"
        for resource_type, ore_patches in self.ore_patches.items():  # this includes "all"
            filtered_ore_patches[resource_type] = []
            if resource_type == "all":
                continue
            for ore_patch in ore_patches:
                if np.sum(ore_patch.resource_array[start_y:end_y, start_x:end_x]):
                    filtered_ore_patches[resource_type].append(ore_patch)
                    filtered_ore_patches["all"].append(ore_patch)
        return filtered_ore_patches

    def count_resources_in_region(self, start_x: int, start_y: int, end_x: int, end_y: int, resource_type: str) -> int:
        """Return the amount of a given resource in the specified region in pixel"""
        return np.sum(self.ore_patch_combined[resource_type].resource_array[start_y:end_y, start_x:end_x])

    def find_longest_consecutive_line_of_resources(
        self,
        resource_type: str,
        thickness: int,
        tolerance: int,
        init_start_x: int,
        init_start_y: int,
        init_end_x: int,
        init_end_y: int,
    ) -> tuple[int, Optional[tuple[int, int, int, int]]]:
        """Return the largest region of consecutive resources regarding a set width and its length in pixel"""
        resource_array = self.ore_patch_combined[resource_type].resource_array[
            init_start_y:init_end_y, init_start_x:init_end_x
        ]
        x_length = init_end_x - init_start_x
        y_length = init_end_y - init_start_y
        max_length = max(x_length, y_length)
        while True:
            # horizontal window
            kernel = np.ones((thickness, max_length), np.int8)
            dst_horizontal = cv2.filter2D(resource_array, -1, kernel, anchor=(0, 0))[
                0 : (y_length - thickness + 1), 0 : (x_length - max_length + 1)
            ]
            dst_vertical = cv2.filter2D(
                resource_array, -1, kernel.transpose(), anchor=(0, 0), borderType=cv2.BORDER_CONSTANT
            )[0 : y_length - max_length + 1, 0 : x_length - thickness + 1]
            area_with_resources_horizontal = np.amax(dst_horizontal)
            area_with_resources_vertical = np.amax(dst_vertical)
            if area_with_resources_horizontal < area_with_resources_vertical:
                is_vertically_orientated = True
                dst = dst_vertical
                area_with_resources = area_with_resources_vertical
            else:
                is_vertically_orientated = False
                dst = dst_horizontal
                area_with_resources = area_with_resources_horizontal
            if area_with_resources + tolerance < max_length * thickness:
                max_length = (area_with_resources + tolerance) // thickness
            else:
                break
        result = np.where(dst == area_with_resources)
        max_pos_with_offset = list(zip(result[1], result[0]))[0]
        max_pos = max_pos_with_offset[0] + init_start_x, max_pos_with_offset[1] + init_start_y
        if is_vertically_orientated:
            max_region = max_pos[0], max_pos[1], max_pos[0] + thickness, max_pos[1] + max_length
        else:
            max_region = max_pos[0], max_pos[1], max_pos[0] + max_length, max_pos[1] + thickness
        return max_length, max_region

    def find_longest_consecutive_line_of_resources_old(
        self,
        resource_type: str,
        thickness: int,
        tolerance: int,
        init_start_x: int,
        init_start_y: int,
        init_end_x: int,
        init_end_y: int,
    ) -> tuple[int, Optional[tuple[int, int, int, int]]]:
        """Return the largest region of consecutive resources regarding a set width and its length in pixel"""
        # TODO: this is extremely slow - need a different approach here, there is probably sth. in cv2
        max_x = init_end_x
        max_y = init_end_y
        max_length = 0
        max_region = None
        resource_array = self.ore_patch_combined[resource_type].resource_array
        # approach is a sliding window of static thickness/width and dynamically increasing max length
        # vertical window
        for start_x in range(init_start_x, max_x - thickness + 1):
            end_x = start_x + thickness
            start_y = init_start_y
            end_y = start_y + (max_length + 1)  # new length must be one tiles larger than the currently largest one
            while end_y <= max_y:
                # count resources in region (start_x, start_y, end_x, end_y) and check if amount is within tolerance
                if np.sum(resource_array[start_y:end_y, start_x:end_x]) >= thickness * (max_length + 1) - tolerance:
                    max_length += 1  # new length must be one tile larger than the currently largest one
                    max_region = (start_x, start_y, end_x, end_y)
                else:
                    start_y += 1
                end_y += 1  # This is equal to "end_y = start_y + (max_length + 1)"
        # horizontal window
        for start_y in range(init_start_y, max_y - thickness + 1):
            end_y = start_y + thickness
            start_x = init_start_x
            end_x = start_x + (1 + max_length)  # new length must be one tile larger than the currently largest one
            while end_x <= max_x:
                # count resources in region (start_x, start_y, end_x, end_y) and check if amount is within tolerance
                if np.sum(resource_array[start_y:end_y, start_x:end_x]) >= thickness * (max_length + 1) - tolerance:
                    max_length = max_length + 1  # new length must be one tiles larger than the currently largest one
                    max_region = (start_x, start_y, end_x, end_y)
                else:
                    start_x += 1
                end_x += 1  # This is equal to "end_x = start_x + (max_length + 1)"
        return max_length, max_region

    @staticmethod
    def calculate_min_distance_between_patches(ore_patch: OrePatch, other_ore_patch: OrePatch) -> float:
        """Return the distance between two ore patches in pixel"""
        return MapAnalyser._calculate_min_distance_between_contours(ore_patch.contour, other_ore_patch.contour)

    @staticmethod
    def calculate_min_distance_between_patches_within_region(
        ore_patch: OrePatch,
        other_ore_patch: OrePatch,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> float:
        """Return the distance between two ore patches in pixel within the specified region"""
        if not (
            np.amax(ore_patch.resource_array[start_y:end_y, start_x:end_x])
            and np.amax(other_ore_patch.resource_array[start_y:end_y, start_x:end_x])
        ):
            return float("inf")  # fast return if any list of contour points is empty after filtering
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
            condition = np.array(
                [
                    np.logical_and(contour_x + 1, contour_y + 1),
                ]
                * 2
            ).transpose()
            contour_within_region = np.ndarray.reshape(patch.contour[condition], (-1, 2))  # filter array by condition
            # # if not contour_within_region.size:
            # #     return float('inf')  # fast return if any list of contour points is empty after filtering
            contours_within_region.append(contour_within_region)
        return MapAnalyser._calculate_min_distance_between_contours(
            contours_within_region[0], contours_within_region[1]
        )

    @staticmethod
    def combine_ore_patches(
        list_of_ore_patches: list[OrePatch],
        resource_type: str,
        dimensions: tuple[int, int],
        tiles_per_pixel: int,
    ) -> OrePatch:
        """Merges a list of ore patches into a virtually single one, that may not even be connected"""
        combined_resource_array = np.zeros((dimensions[0], dimensions[1]), dtype=np.uint8)  # in case the list is empty
        for ore_patch in list_of_ore_patches:
            combined_resource_array += ore_patch.resource_array
        return OrePatch(combined_resource_array, resource_type, tiles_per_pixel)

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
        contour_x_matrix = np.array(
            [
                contour_x,
            ]
            * other_contour_x.shape[0]
        ).transpose()
        other_contour_x_matrix = np.array(
            [
                other_contour_x,
            ]
            * contour_x.shape[0]
        )
        contour_y_matrix = np.array(
            [
                contour_y,
            ]
            * other_contour_y.shape[0]
        ).transpose()
        other_contour_y_matrix = np.array(
            [
                other_contour_y,
            ]
            * contour_y.shape[0]
        )
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
