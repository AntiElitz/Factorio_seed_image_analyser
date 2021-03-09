from typing import Optional

import image_analyser_pool
from analyser import MapAnalyser

PRINTS = False
PLOTS = False


def my_analyser_function(analyser: MapAnalyser) -> Optional[list[str]]:
    """Your code to analyse an individual map goes here

    Below are some examples of how to archive some basics
    """
    # the wrapper allows to use Factorio coordinates with a centered coordinate system and tile units instead of pixels
    analyser = analyser.map_analyser_coordinate_wrapper  # ! you may not want to remove this

    # example on how to get the map seed and the resources available for analysing
    map_seed = analyser.map_seed
    resource_types = analyser.resource_types
    if PRINTS:
        print(f"This is the map seed {map_seed}. It contains the following resource types: {resource_types}.")

    # example on how to get the amount of "coal" in a specific region
    (start_x, start_y, end_x, end_y) = analyser.min_x, analyser.min_y, analyser.max_x, analyser.max_y
    size_in_tiles = analyser.count_resources_in_region(start_x, start_y, end_x, end_y, "coal")
    if PRINTS:
        print(f"There are {size_in_tiles} coal tiles in the region {(start_x, start_y, end_x, end_y)}.")

    # example on how to get the largest iron patch and it's size, type and center point
    ore_patches = analyser.ore_patches["iron"]
    largest_ore_patch = max(ore_patches, key=lambda patch: patch.size)
    largest_ore_patch_size_in_tiles = largest_ore_patch.size
    largest_ore_patch_resource_type = largest_ore_patch.resource_type
    largest_ore_patch_center_point = largest_ore_patch.center_point
    if PRINTS:
        print(
            f"The largest {largest_ore_patch_resource_type} patch contains {largest_ore_patch_size_in_tiles} "
            f"tiles and is located at {largest_ore_patch_center_point}."
        )

    # example on how to get a list of ore patches partially in a specific region
    start_x, start_y, end_x, end_y = -64, -64, 64, 64
    filtered_ore_patches_dict = analyser.get_ore_patches_partially_in_region(start_x, start_y, end_x, end_y)
    iron_ore_patches = filtered_ore_patches_dict["iron"]
    if PRINTS:
        print(
            f"The center points of the iron ore patches partially in the region {(start_x, start_y, end_x, end_y)} "
            f"are {[elem.center_point for elem in iron_ore_patches]}."
        )

    # example on how to plot any ore patch for debugging
    ore_patch = analyser.ore_patch_combined["water"]  # This is all water combined in one virtual patch
    if PLOTS:
        ore_patch.display()

    # example on how to get the minimum distance between 2 ore patches
    ore_patch = analyser.ore_patches["all"][0]  # the key "all" contains the patches of each key
    other_ore_patch = analyser.ore_patches["all"][1]
    distance = analyser.calculate_min_distance_between_patches(ore_patch, other_ore_patch)
    if PRINTS:
        print(f"The minimum distance between these 2 ore patches is {distance} tiles.")

    # example on how to get the minimum distance between 2 ore patches within a limited region
    ore_patch = analyser.ore_patches["all"][0]
    other_ore_patch = analyser.ore_patches["all"][1]
    (start_x, start_y, end_x, end_y) = 0, 0, 256, 256
    distance = analyser.calculate_min_distance_between_patches_within_region(
        ore_patch, other_ore_patch, start_x, start_y, end_x, end_y
    )
    if PRINTS:
        print(
            f"The minimum distance between these 2 ore patches within the region {(start_x, start_y, end_x, end_y)} "
            f"is {distance} tiles."
        )

    # example on how to get the coal patch closest to water in the starting area
    coal_patches = analyser.ore_patches["coal"]
    water_patch = analyser.ore_patch_combined["water"]  # This is all water combined in one virtual patch
    min_distance = float("inf")
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
                f"The coal that is closest to water is located at {closest_ore_patch.center_point} and is "
                f"{min_distance} tiles away from water. However there is no information on what water patch this is."
            )

    # example on how to get the coal patch closest to water in the starting area and not loose any information
    coal_patches = analyser.ore_patches["coal"]
    water_patches = analyser.ore_patches["water"]
    start_x, start_y, end_x, end_y = -128, -128, 128, 128
    min_distance = float("inf")
    closest_ore_patch = None
    closest_water_patch = None
    for ore_patch in coal_patches:
        for other_ore_patch in water_patches:
            distance = analyser.calculate_min_distance_between_patches_within_region(
                ore_patch, other_ore_patch, start_x, start_y, end_x, end_y
            )
            if distance < min_distance:
                min_distance = distance
                closest_ore_patch = ore_patch
                closest_water_patch = other_ore_patch
    if PRINTS:
        if closest_ore_patch is None or closest_water_patch is None:
            print("There is either no coal or no water in the area.")
        else:
            print(
                f"The coal in the area {(start_x, start_y, end_x, end_y)} that is closest to water is located at "
                f"{closest_ore_patch.center_point} and is {min_distance} tiles away from the water located at "
                f"{closest_water_patch.center_point}."
            )

    # example on how to find all starting areas
    ore_patches_dict = analyser.ore_patches
    ore_patch_min_size = 1024  # The minimum size in tiles a patch has to have to be considered for the starting area
    max_distance = 40  # The max distance in tiles the patches in the possible start area may be apart from each other
    possible_starting_areas = []
    # generate list of ore patches larger than ore_patch_min_size
    large_iron_ore_patches = [p for p in ore_patches_dict["iron"] if p.size > ore_patch_min_size]
    large_copper_ore_patches = [p for p in ore_patches_dict["copper"] if p.size > ore_patch_min_size]
    large_coal_ore_patches = [p for p in ore_patches_dict["coal"] if p.size > ore_patch_min_size]

    copper_patch_combined = analyser.ore_patch_combined["copper"]
    coal_patch_combined = analyser.ore_patch_combined["coal"]
    for iron_patch in large_iron_ore_patches:
        # first test if any copper patch & coal patch is within max_distance of the tested iron patch otherwise skip
        if max_distance >= analyser.calculate_min_distance_between_patches(
            iron_patch, copper_patch_combined
        ) and max_distance >= analyser.calculate_min_distance_between_patches(iron_patch, coal_patch_combined):
            # just test for all combinations of this iron and all copper/ coal patches
            for copper_patch in large_copper_ore_patches:
                # copper close to this iron?
                if max_distance >= analyser.calculate_min_distance_between_patches(iron_patch, copper_patch):
                    for coal_patch in large_coal_ore_patches:
                        # coal close to this iron?
                        if max_distance >= analyser.calculate_min_distance_between_patches(coal_patch, iron_patch):
                            if max_distance >= analyser.calculate_min_distance_between_patches(
                                # coal close to copper?
                                coal_patch, copper_patch
                            ):
                                # found iron/ copper/ coal triple successfully
                                possible_starting_areas.append((iron_patch, copper_patch, coal_patch))
    # now get the average center point of the 3 patches für printing
    possible_starting_areas_coordinates = []
    for area in possible_starting_areas:
        possible_starting_areas_coordinates.append(
            (
                (area[0].center_point[0] + area[1].center_point[0] + area[2].center_point[0]) / 3,
                (area[0].center_point[1] + area[1].center_point[1] + area[2].center_point[1]) / 3,
            )
        )
    if PRINTS:
        print(f"There are nice starting areas located at {possible_starting_areas_coordinates}.")

    # # example on how to find the largest resource area of a given width
    # max_length, region = analyser.find_longest_consecutive_line_of_resources("iron", 16, 256)
    # if PRINTS:
    #     print(
    #         f"The largest area of iron that is 16 tiles wide is {max_length} tiles long and located at {region}. "
    #         f"It may contain up to 256 other tiles."
    #     )

    if PRINTS:
        print("------------------------------------------")

    # this is what goes into the resulting .csv file row. Return None to discard the map.
    if largest_ore_patch.size > 2500:
        return [str(analyser.map_seed), str(analyser.min_x), str(largest_ore_patch.size)]
    else:
        return None


def main():
    """This is where you define what you want to analyse"""
    resource_colors = {  # Colors in RGB
        "iron": (104, 132, 146),
        "copper": (203, 97, 53),
        "coal": (0, 0, 0),
        "water": (51, 83, 95),
    }
    folder_path = "images10000"
    file_extension = ".png"
    tiles_pre_pixel = 8
    multiprocess = False

    manager = image_analyser_pool.ImageAnalyserPool(None)
    manager.add_folder_of_images_to_analyse(folder_path, file_extension, resource_colors, tiles_pre_pixel)
    manager.analyse(my_analyser_function, multiprocess)
    manager.save_results_to_csv("results.csv")


if __name__ == "__main__":
    main()
