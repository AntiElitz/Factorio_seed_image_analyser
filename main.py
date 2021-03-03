from typing import Optional

import image_analyser_pool
from analyser_coordinate_wrapper import MapAnalyserCoordinateWrapper

PRINTS = True
PLOTS = False


def my_analyser_function(analyser: MapAnalyserCoordinateWrapper) -> Optional[list[str]]:
    """Your code to analyse an individual map code goes here

    Below are some examples of how to archive some basics
    """

    # example on how to get the map seed and the resources available for analysing
    map_seed = analyser.map_seed
    resource_types = analyser.resource_types
    if PRINTS:
        print("This is the map seed' " + str(map_seed) + "'. It contains the following resource types: "
              + str(resource_types) + ".")

    # example on how to get the amount of "coal" in a specific region
    (start_x, start_y, end_x, end_y) = analyser.min_x, analyser.min_y, analyser.max_x, analyser.max_y
    size_in_tiles = analyser.count_resources_in_region(start_x, start_y, end_x, end_y, "coal")
    if PRINTS:
        print("There are " + str(size_in_tiles) + " 'coal' tiles in the region " + str(
            (start_x, start_y, end_x, end_y)) + ".")

    # example on how to get the largest iron patch and it's size, type and center point
    ore_patches = analyser.ore_patches["iron"]
    largest_ore_patch = max(ore_patches, key=lambda patch: patch.size)
    largest_ore_patch_size_in_tiles = largest_ore_patch.size
    largest_ore_patch_resource_type = largest_ore_patch.resource_type
    largest_ore_patch_center_point = largest_ore_patch.center_point
    if PRINTS:
        print("The largest '" + str(largest_ore_patch_resource_type)
              + "' patch contains " + str(largest_ore_patch_size_in_tiles)
              + " tiles and is located at " + str(largest_ore_patch_center_point))

    # example on how to get the minimum distance between 2 ore patches
    ore_patch = analyser.ore_patches["all"][0]  # the key "all" contains the patches of each key
    other_ore_patch = analyser.ore_patches["all"][1]
    distance = analyser.calculate_min_distance_between_patches(ore_patch, other_ore_patch)
    if PRINTS:
        print("The minimum distance between these 2 ore patches is " + str(distance) + " tiles.")

    # example on how to get the minimum distance between 2 ore patches within a limited region
    ore_patch = analyser.ore_patches["all"][0]
    other_ore_patch = analyser.ore_patches["all"][1]
    (start_x, start_y, end_x, end_y) = 0, 0, 256, 256
    distance = analyser.calculate_min_distance_between_patches_within_region(
        ore_patch, other_ore_patch, start_x, start_y, end_x, end_y)
    if PRINTS:
        print("The minimum distance between these 2 ore patches within the region "
              + str((start_x, start_y, end_x, end_y)) + " is " + str(distance) + " tiles.")

    # example on how to plot any ore patch for debugging
    ore_patch = analyser.ore_patch_combined["water"]  # This is all water combined in one virtual patch
    if PLOTS:
        ore_patch.display()

    # example on how to get the coal patch closest to water in the starting area
    coal_patches = analyser.ore_patches["coal"]
    water_patch = analyser.ore_patch_combined["water"]  # This is all water combined in one virtual patch
    min_distance = float('inf')
    closest_ore_patch = None
    for ore_patch in coal_patches:
        distance = analyser.calculate_min_distance_between_patches(ore_patch, water_patch)
        if distance < min_distance:
            min_distance = distance
            closest_ore_patch = ore_patch
    if PRINTS:
        if closest_ore_patch is None:
            print("There is either no coal or no water")
        else:
            print(
                "The coal that is closest to water is located at " + str(closest_ore_patch.center_point)
                + " and is " + str(min_distance)
                + " tiles away from water. However we don't have information on what water patch this is.")

    # example on how to get the coal patch closest to water in the starting area and not loose any information
    coal_patches = analyser.ore_patches["coal"]
    water_patches = analyser.ore_patches["water"]
    start_x, start_y, end_x, end_y = -128, -128, 128, 128
    min_distance = float('inf')
    closest_ore_patch = None
    closest_water_patch = None
    for ore_patch in coal_patches:
        for other_ore_patch in water_patches:
            distance = analyser.calculate_min_distance_between_patches_within_region(
                ore_patch, other_ore_patch, start_x, start_y, end_x, end_y)
            if distance < min_distance:
                min_distance = distance
                closest_ore_patch = ore_patch
                closest_water_patch = other_ore_patch
    if PRINTS:
        if closest_ore_patch is None:
            print("There is either no coal or no water in the area.")
        else:
            print(
                "The coal in the area " + str((start_x, start_y, end_x, end_y))
                + " that is closest to water is located at " + str(closest_ore_patch.center_point)
                + " and is " + str(min_distance) + " tiles away from the water located at "
                + str(closest_water_patch.center_point) + ".")

    # TODO: add example for second starting area

    # TODO: proper example for find_longest_consecutive_line_of_resources
    # testing stuff
        max_length, region = analyser.find_longest_consecutive_line_of_resources("iron", 8, 256)
        print(max_length)
        print(region)

    # this is what goes into the resulting .csv file row. Return None to discard the map.
    if largest_ore_patch.size > 2500:
        return [str(analyser.map_seed), str(analyser.min_x), str(largest_ore_patch.size)]
    else:
        return None


if __name__ == '__main__':
    """This is where you define what you want to analyse"""
    resource_colors = {  # Colors in RGB
        "iron": (104, 132, 146),
        "copper": (203, 97, 53),
        "coal": (0, 0, 0),
        "water": (51, 83, 95)
    }
    folder_path = "images1"
    file_extension = ".png"

    manager = image_analyser_pool.ImageAnalyserPool(None)
    manager.add_folder_of_images_to_analyse(folder_path, file_extension, my_analyser_function, resource_colors, 8)
    manager.analyse()
    manager.save_results_to_csv("results.csv")
