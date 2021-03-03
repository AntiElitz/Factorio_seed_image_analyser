from __future__ import annotations

import math
from typing import Optional

import analyser


class OrePatchCoordinateWrapper:
    def __init__(self, ore_patch: analyser.OrePatch, side_length_of_pixel_in_tiles: int):
        self.wrapped_ore_patch = ore_patch
        self._side_length_of_pixel_in_tiles = side_length_of_pixel_in_tiles

    @property
    def size(self) -> int:
        """Return the size of an ore patch in Factorio tiles"""
        return self.wrapped_ore_patch.size * self._side_length_of_pixel_in_tiles * self._side_length_of_pixel_in_tiles

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
        min_x_px = (-self.wrapped_ore_patch.resource_array.shape[1] // 2)
        min_y_px = (-self.wrapped_ore_patch.resource_array.shape[0] // 2)
        x = (x_px + min_x_px) * self._side_length_of_pixel_in_tiles
        y = (y_px + min_y_px) * self._side_length_of_pixel_in_tiles
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


class MapAnalyserCoordinateWrapper:
    def __init__(self, map_analyser: analyser.MapAnalyser, side_length_of_pixel_in_tiles: int):
        self._wrapped_map_analyser = map_analyser
        self._side_length_of_pixel_in_tiles = side_length_of_pixel_in_tiles

    @property
    def map_seed(self) -> str:
        """Return the name of file that is being analysed without extension. This is usually the map seed"""
        return self._wrapped_map_analyser.map_seed

    @property
    def resource_types(self) -> list[str]:
        """Return a list of all resource types that can be analysed. Does not include 'all'"""
        return self._wrapped_map_analyser.resource_types

    @property
    def ore_patches(self) -> dict[str, list[OrePatchCoordinateWrapper]]:
        """Return a Dictionary containing lists of patches for each resource type
        example usages:
        my_map_analyser.ore_patches['coal']  # return list of all coal patches
        my_map_analyser.ore_patches['all']  # return list of ALL patches regardless of resource type
        """
        ore_patches = self._wrapped_map_analyser.ore_patches
        # replace ore_patches with their ore_patch_coordinate_wrapper
        ore_patches_with_wrapper = dict.fromkeys(ore_patches.keys())
        for key in ore_patches_with_wrapper:
            ore_patches_with_wrapper[key] = [elem.ore_patch_coordinate_wrapper for elem in ore_patches[key]]
        return ore_patches_with_wrapper

    @property
    def ore_patch_combined(self) -> dict[str, OrePatchCoordinateWrapper]:
        """Return a Dictionary containing each resource type as a single combined patch
        example usages:
        my_map_analyser.ore_patch_combined['coal']  # return all coal in only one patch as if it was a single one
        """
        ore_patch_combined = self._wrapped_map_analyser.ore_patch_combined
        # replace ore_patches with their ore_patch_coordinate_wrapper
        ore_patch_combined_with_wrapper = dict.fromkeys(ore_patch_combined.keys())
        for key in ore_patch_combined_with_wrapper:
            ore_patch_combined_with_wrapper[key] = ore_patch_combined[key].ore_patch_coordinate_wrapper
        return ore_patch_combined_with_wrapper

    @property
    def min_x(self) -> int:
        """Return the minimum x value of the image in Factorio coordinates"""
        return (-self._wrapped_map_analyser.dimensions[1] // 2) * self._side_length_of_pixel_in_tiles

    @property
    def min_y(self) -> int:
        """Return the minimum y value of the image in Factorio coordinates"""
        return (-self._wrapped_map_analyser.dimensions[0] // 2) * self._side_length_of_pixel_in_tiles

    @property
    def max_x(self) -> int:
        """Return the maximum x value of the image in Factorio coordinates"""
        return (self._wrapped_map_analyser.dimensions[1] // 2) * self._side_length_of_pixel_in_tiles

    @property
    def max_y(self) -> int:
        """Return the maximum y value of the image in Factorio coordinates"""
        return (self._wrapped_map_analyser.dimensions[0] // 2) * self._side_length_of_pixel_in_tiles

    def is_in_bounds_x(self, x: int) -> bool:
        """Checks if the x value of a Factorio coordinate is withing the bounds of the image"""
        return self.min_x <= x <= self.max_x

    def is_in_bounds_y(self, y: int) -> bool:
        """Checks if the y value of a Factorio coordinate is withing the bounds of the image"""
        return self.min_y <= y <= self.max_y

    def is_in_bounds_point(self, point: tuple[int, int]) -> bool:
        """Checks if a Factorio coordinate is withing the bounds of the image"""
        return self.is_in_bounds_x(point[0]) and self.is_in_bounds_y(point[1])

    def count_resources_in_region(self, start_x: int, start_y: int, end_x: int, end_y: int,
                                  resource_type: str) -> int:
        """Return the amount of a given resource in the specified region in Factorio tiles"""
        # convert Factorio coordinates to pixel - makes region larger, if inputs don't align
        (start_x_px, start_y_px, end_x_px, end_y_px) = self._coordinate_region_to_pixel_region((start_x, start_y,
                                                                                                end_x, end_y))
        # call parent and convert area in square pixels to Factorio tiles
        return (self._side_length_of_pixel_in_tiles * self._side_length_of_pixel_in_tiles *  # x*x is faster than x**2
                self._wrapped_map_analyser.count_resources_in_region(start_x_px, start_y_px, end_x_px, end_y_px,
                                                                     resource_type))

    # TODO: get_oro_patches_partially_in_region

    def find_longest_consecutive_line_of_resources(self, resource_type: str, thickness: int = None, tolerance: int = 0,
                                                   start_x: int = None, start_y: int = None,
                                                   end_x: int = None, end_y: int = None
                                                   ) -> tuple[int, tuple[int, int, int, int]]:
        """Return the largest region of consecutive resources regarding a set width and its length in Factorio coords
        Return (0, None) if nothing is found
        param thickness: The width of the region
        param tolerance: How many tiles of the given resource the region can miss """
        if thickness is None:
            thickness = self._side_length_of_pixel_in_tiles
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
        (start_x_px, start_y_px, end_x_px, end_y_px) = self._coordinate_region_to_pixel_region((start_x, start_y,
                                                                                                end_x, end_y))
        # call parent with conversions to pixel
        max_length, region = self._wrapped_map_analyser.find_longest_consecutive_line_of_resources(
                resource_type, math.ceil(thickness / self._side_length_of_pixel_in_tiles),
                math.ceil(tolerance / (self._side_length_of_pixel_in_tiles * self._side_length_of_pixel_in_tiles)),
                start_x_px, start_y_px, end_x_px, end_y_px)
        #  convert back to Factorio tiles
        return max_length * self._side_length_of_pixel_in_tiles, self._pixel_region_to_coordinate_region(region)

    def calculate_min_distance_between_patches(self, ore_patch: OrePatchCoordinateWrapper,
                                               other_ore_patch: OrePatchCoordinateWrapper) -> float:
        """Return the distance between two ore patches in Factorio tiles"""
        # TODO: wrapped_ore_patch being public is probably a result of poor software design. How to make it private?
        # call parent and convert distance in pixels to Factorio tiles
        return analyser.MapAnalyser.calculate_min_distance_between_patches(
            ore_patch.wrapped_ore_patch, other_ore_patch.wrapped_ore_patch) * self._side_length_of_pixel_in_tiles

    def calculate_min_distance_between_patches_within_region(self, ore_patch: OrePatchCoordinateWrapper,
                                                             other_ore_patch: OrePatchCoordinateWrapper,
                                                             start_x: int, start_y: int, end_x: int, end_y: int
                                                             ) -> float:
        """Return the distance between two ore patches in Factorio tiles within the specified region
        This can be useful when very large patches have several points close to each other, but
        one is only interested in the closest point within the starting area."""
        # convert Factorio coordinates to pixel - makes region larger, if inputs don't align
        (start_x_px, start_y_px, end_x_px, end_y_px) = self._coordinate_region_to_pixel_region((start_x, start_y,
                                                                                                end_x, end_y))
        # call parent and convert distance in pixels to Factorio tiles
        return analyser.MapAnalyser.calculate_min_distance_between_patches_within_region(
            ore_patch.wrapped_ore_patch, other_ore_patch.wrapped_ore_patch, start_x_px, start_y_px, end_x_px, end_y_px
        ) * self._side_length_of_pixel_in_tiles

    def _coordinate_to_pixel(self, point: tuple[int, int], round_up: bool = False) -> tuple[int, int]:
        """Converts Factorio coordinates to an image point in pixel"""
        if round_up:
            point = (  # This takes advantage of negative int rounding: 3 // 2 = 1, but -(-3 // 2) = 2
                -((-point[0] + self.min_x) // self._side_length_of_pixel_in_tiles),
                -((-point[1] + self.min_y) // self._side_length_of_pixel_in_tiles)
            )
        else:  # round down
            point = (
                (point[0] - self.min_x) // self._side_length_of_pixel_in_tiles,
                (point[1] - self.min_y) // self._side_length_of_pixel_in_tiles
            )
        return point

    def _coordinate_region_to_pixel_region(self, region: tuple[int, int, int, int]
                                           ) -> Optional[tuple[int, int, int, int]]:
        """Converts a region of Factorio coordinates to a region of image points in pixel
        makes the region larger, if inputs don't align """
        if region is None:
            return None
        # handle invalid inputs
        if not (self.is_in_bounds_point((region[0], region[1])) and self.is_in_bounds_point((region[2], region[3]))):
            raise IndexError("Factorio coordinate is out of map bounds")
        if not (region[0] < region[2] and region[1] < region[3]):
            raise IndexError("The start value must be lower than the end value of the region")
        side_length_of_pixel_in_tiles = self._side_length_of_pixel_in_tiles  # cheaper referencing
        region = (
            # round start down
            (region[0] - self.min_x) // side_length_of_pixel_in_tiles,
            (region[1] - self.min_y) // side_length_of_pixel_in_tiles,
            # round end up
            # This takes advantage of negative int rounding: 3 // 2 = 1, but -(-3 // 2) = 2
            -((-region[2] + self.min_x) // side_length_of_pixel_in_tiles),
            -((-region[3] + self.min_y) // side_length_of_pixel_in_tiles)
        )
        return region

    def _pixel_region_to_coordinate_region(self, region: tuple[int, int, int, int]
                                           ) -> Optional[tuple[int, int, int, int]]:
        """Converts a region of image points in pixel to a region of Factorio coordinates"""
        if region is None:
            return None
        side_length_of_pixel_in_tiles = self._side_length_of_pixel_in_tiles  # cheaper referencing
        region = (
            region[0] * side_length_of_pixel_in_tiles + self.min_x,
            region[1] * side_length_of_pixel_in_tiles + self.min_y,
            region[2] * side_length_of_pixel_in_tiles + self.min_x,
            region[3] * side_length_of_pixel_in_tiles + self.min_y,
        )
        return region
