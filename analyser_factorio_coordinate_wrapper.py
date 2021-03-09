from __future__ import annotations

import math
from typing import Optional

import analyser


class OrePatchCoordinateWrapper:
    def __init__(self, ore_patch: analyser.OrePatch, tiles_per_pixel: int):
        self.wrapped_ore_patch = ore_patch
        self._tiles_per_pixel = tiles_per_pixel

    @property
    def size(self) -> int:
        """Return the size of an ore patch in Factorio tiles"""
        return self.wrapped_ore_patch.size * self._tiles_per_pixel * self._tiles_per_pixel

    @property
    def resource_type(self) -> str:  #
        """Return the resource type of an ore patch"""
        return self.wrapped_ore_patch.resource_type

    @property
    def center_point(self) -> tuple[float, float]:
        """Return the weighted center of an ore patch in Factorio coordinates"""
        # get weighted center in pixel coordinates
        x_px, y_px = self.wrapped_ore_patch.center_point
        # convert pixel to Factorio coordinates
        min_x_px = -self.wrapped_ore_patch.resource_array.shape[1] // 2
        min_y_px = -self.wrapped_ore_patch.resource_array.shape[0] // 2
        x = (x_px + min_x_px) * self._tiles_per_pixel
        y = (y_px + min_y_px) * self._tiles_per_pixel
        return x, y

    def display(self) -> None:  #
        """This will open the image of the ore patch in your default image viewer. Very slow. Use for debug only"""
        self.wrapped_ore_patch.display()

    def __lt__(self, other):
        return self.size < other.size

    def __le__(self, other):
        return self.size <= other.size

    def __gt__(self, other):
        return self.size > other.size

    def __ge__(self, other):
        return self.size >= other.size


class MapAnalyserFactorioCoordinateWrapper:
    def __init__(self, map_analyser: analyser.MapAnalyser, tiles_per_pixel: int):
        self.wrapped_map_analyser = map_analyser
        self._tiles_per_pixel = tiles_per_pixel
        self._tiles_per_pixel_sq = tiles_per_pixel * tiles_per_pixel

    @property
    def map_seed(self) -> str:
        """Return the name of file that is being analysed without extension. This is usually the map seed"""
        return self.wrapped_map_analyser.map_seed

    @property
    def resource_types(self) -> list[str]:
        """Return a list of all resource types that can be analysed. Does not include 'all'"""
        return self.wrapped_map_analyser.resource_types.copy()

    @property
    def ore_patches(self) -> dict[str, list[OrePatchCoordinateWrapper]]:
        """Return a Dictionary containing lists of patches for each resource type
        example usages:
        my_map_analyser.ore_patches['coal']  # return list of all coal patches
        my_map_analyser.ore_patches['all']  # return list of ALL patches regardless of resource type
        """
        ore_patches = self.wrapped_map_analyser.ore_patches
        # replace ore_patches with their ore_patch_coordinate_wrapper
        ore_patches_with_wrapper_dict = dict.fromkeys(ore_patches)
        for resource_type in ore_patches_with_wrapper_dict:
            ore_patches_with_wrapper_dict[resource_type] = [
                elem.ore_patch_coordinate_wrapper for elem in ore_patches[resource_type]
            ]
        return ore_patches_with_wrapper_dict

    @property
    def ore_patch_combined(self) -> dict[str, OrePatchCoordinateWrapper]:
        """Return a dictionary containing each resource type as a single combined patch
        example usages:
        my_map_analyser.ore_patch_combined['coal']  # return all coal in only one patch as if it was a single one
        """
        ore_patch_combined = self.wrapped_map_analyser.ore_patch_combined
        # replace ore_patches with their ore_patch_coordinate_wrapper
        ore_patch_combined_with_wrapper_dict = dict.fromkeys(ore_patch_combined)
        for resource_type in ore_patch_combined_with_wrapper_dict:
            ore_patch_combined_with_wrapper_dict[resource_type] = ore_patch_combined[
                resource_type
            ].ore_patch_coordinate_wrapper
        return ore_patch_combined_with_wrapper_dict

    @property
    def min_x(self) -> int:
        """Return the minimum x value of the image in Factorio coordinates"""
        return (-self.wrapped_map_analyser.dimensions[1] // 2) * self._tiles_per_pixel

    @property
    def min_y(self) -> int:
        """Return the minimum y value of the image in Factorio coordinates"""
        return (-self.wrapped_map_analyser.dimensions[0] // 2) * self._tiles_per_pixel

    @property
    def max_x(self) -> int:
        """Return the maximum x value of the image in Factorio coordinates"""
        return (self.wrapped_map_analyser.dimensions[1] // 2) * self._tiles_per_pixel

    @property
    def max_y(self) -> int:
        """Return the maximum y value of the image in Factorio coordinates"""
        return (self.wrapped_map_analyser.dimensions[0] // 2) * self._tiles_per_pixel

    def is_in_bounds_x(self, x: int) -> bool:
        """Checks if the x value of a Factorio coordinate is withing the bounds of the image"""
        return self.min_x <= x <= self.max_x

    def is_in_bounds_y(self, y: int) -> bool:
        """Checks if the y value of a Factorio coordinate is withing the bounds of the image"""
        return self.min_y <= y <= self.max_y

    def is_in_bounds_point(self, point: tuple[int, int]) -> bool:
        """Checks if a Factorio coordinate is withing the bounds of the image"""
        return self.is_in_bounds_x(point[0]) and self.is_in_bounds_y(point[1])

    def count_resources_in_region(self, start_x: int, start_y: int, end_x: int, end_y: int, resource_type: str) -> int:
        """Return the amount of a given resource in the specified region in Factorio tiles"""
        # convert Factorio coordinates to pixel - makes region larger, if inputs don't align
        start_x_px, start_y_px, end_x_px, end_y_px = self._coordinate_region_to_pixel_region(
            start_x, start_y, end_x, end_y
        )
        # call parent and convert area in square pixels to Factorio tiles
        area_px = self.wrapped_map_analyser.count_resources_in_region(
            start_x_px, start_y_px, end_x_px, end_y_px, resource_type
        )
        return self._tiles_per_pixel_sq * area_px

    def get_ore_patches_partially_in_region(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> dict[str, list[OrePatchCoordinateWrapper]]:
        """Return a dictionary containing lists of patches that are partially in a region for each resource type"""
        # convert Factorio coordinates to pixel - makes region larger, if inputs don't align
        start_x_px, start_y_px, end_x_px, end_y_px = self._coordinate_region_to_pixel_region(
            start_x, start_y, end_x, end_y
        )
        ore_patches = self.wrapped_map_analyser.get_ore_patches_partially_in_region(
            start_x_px, start_y_px, end_x_px, end_y_px
        )
        # replace ore_patches with their ore_patch_coordinate_wrapper
        ore_patches_with_wrapper_dict = dict.fromkeys(ore_patches)
        for resource_type in ore_patches_with_wrapper_dict:
            ore_patches_with_wrapper_dict[resource_type] = [
                elem.ore_patch_coordinate_wrapper for elem in ore_patches[resource_type]
            ]
        return ore_patches_with_wrapper_dict

    def find_longest_consecutive_line_of_resources(
        self,
        resource_type: str,
        thickness: int = None,
        tolerance: int = 0,
        start_x: int = None,
        start_y: int = None,
        end_x: int = None,
        end_y: int = None,
    ) -> tuple[int, Optional[tuple[int, int, int, int]]]:
        """Return the largest region of consecutive resources regarding a set width and its length in Factorio coords
        Return (0, None) if nothing is found
        param thickness: The width of the region
        param tolerance: How many tiles of the given resource the region can miss"""
        if thickness is None:
            thickness = self._tiles_per_pixel
        elif thickness <= 0:
            raise IndexError("Thickness must be positive value larger than 0")
        if start_x is None:
            start_x = self.min_x
        if start_y is None:
            start_y = self.min_y
        if end_x is None:
            end_x = self.max_x
        if end_y is None:
            end_y = self.max_y
        # convert Factorio coordinates to pixel - makes region larger, if inputs don't align
        start_x_px, start_y_px, end_x_px, end_y_px = self._coordinate_region_to_pixel_region(
            start_x, start_y, end_x, end_y
        )
        # call parent with conversions to pixel
        max_length, region = self.wrapped_map_analyser.find_longest_consecutive_line_of_resources(
            resource_type,
            math.ceil(thickness / self._tiles_per_pixel),
            math.ceil(tolerance / self._tiles_per_pixel_sq),
            start_x_px,
            start_y_px,
            end_x_px,
            end_y_px,
        )
        #  convert back to Factorio tiles
        if region is None:
            return 0, None
        return (
            max_length * self._tiles_per_pixel,
            self._pixel_region_to_coordinate_region(region[0], region[1], region[2], region[3]),
        )

    def calculate_min_distance_between_patches(
        self, ore_patch: OrePatchCoordinateWrapper, other_ore_patch: OrePatchCoordinateWrapper
    ) -> float:
        """Return the distance between two ore patches in Factorio tiles"""
        # call parent and convert distance in pixels to Factorio tiles
        return (
            analyser.MapAnalyser.calculate_min_distance_between_patches(
                ore_patch.wrapped_ore_patch, other_ore_patch.wrapped_ore_patch
            )
            * self._tiles_per_pixel
        )

    def calculate_min_distance_between_patches_within_region(
        self,
        ore_patch: OrePatchCoordinateWrapper,
        other_ore_patch: OrePatchCoordinateWrapper,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
    ) -> float:
        """Return the distance between two ore patches in Factorio tiles within the specified region
        This can be useful when very large patches have several points close to each other, but
        one is only interested in the closest point within the starting area."""
        # convert Factorio coordinates to pixel - makes region larger, if inputs don't align
        start_x_px, start_y_px, end_x_px, end_y_px = self._coordinate_region_to_pixel_region(
            start_x, start_y, end_x, end_y
        )
        # call parent and convert distance in pixels to Factorio tiles
        return (
            analyser.MapAnalyser.calculate_min_distance_between_patches_within_region(
                ore_patch.wrapped_ore_patch,
                other_ore_patch.wrapped_ore_patch,
                start_x_px,
                start_y_px,
                end_x_px,
                end_y_px,
            )
            * self._tiles_per_pixel
        )

    def _coordinate_to_pixel(self, point: tuple[int, int], round_up: bool = False) -> tuple[int, int]:
        """Converts Factorio coordinates to an image point in pixel"""
        if round_up:
            point = (  # This takes advantage of negative int rounding: 3 // 2 = 1, but -(-3 // 2) = 2
                -((-point[0] + self.min_x) // self._tiles_per_pixel),
                -((-point[1] + self.min_y) // self._tiles_per_pixel),
            )
        else:  # round down
            point = ((point[0] - self.min_x) // self._tiles_per_pixel, (point[1] - self.min_y) // self._tiles_per_pixel)
        return point

    def _coordinate_region_to_pixel_region(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> tuple[int, int, int, int]:
        """Converts a region of Factorio coordinates to a region of image points in pixel
        makes the region larger, if inputs don't align"""
        tiles_per_pixel = self._tiles_per_pixel  # cheaper referencing
        min_x = self.min_x  # cheaper referencing
        min_y = self.min_y  # cheaper referencing
        return (
            # round start down
            (start_x - min_x) // tiles_per_pixel,
            (start_y - min_y) // tiles_per_pixel,
            # round end up
            # This takes advantage of negative int rounding: 3 // 2 = 1, but -(-3 // 2) = 2
            -((-end_x + min_x) // tiles_per_pixel),
            -((-end_y + min_y) // tiles_per_pixel),
        )

    def _pixel_region_to_coordinate_region(
        self, start_x: int, start_y: int, end_x: int, end_y: int
    ) -> tuple[int, int, int, int]:
        """Converts a region of image points in pixel to a region of Factorio coordinates"""
        tiles_per_pixel = self._tiles_per_pixel  # cheaper referencing
        min_x = self.min_x  # cheaper referencing
        min_y = self.min_y  # cheaper referencing
        return (
            start_x * tiles_per_pixel + min_x,
            start_y * tiles_per_pixel + min_y,
            end_x * tiles_per_pixel + min_x,
            end_y * tiles_per_pixel + min_y,
        )
