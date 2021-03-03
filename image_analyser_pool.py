import glob
import concurrent.futures
from typing import Callable, Optional

from tqdm import tqdm
import csv
import analyser
import analyser_coordinate_wrapper

MULTIPROCESS = False  # False is useful to debug and analyse the performance in the profiler. True for faster execution.


def _analyse(tasks: tuple[Callable[[analyser_coordinate_wrapper.MapAnalyserCoordinateWrapper], list[str]],
                          str, dict[str, tuple[int, int, int]], int]) -> Optional[list[str]]:
    """Creates an analyser for the maps and calls the callback function with the wrapped analyser
    This is where the multiprocessing starts. Return the result of the analysing function
    """
    callback_analyser_function = tasks[0]
    image_path = tasks[1]
    resource_colors = tasks[2]
    side_length_of_pixel_in_tiles = tasks[3]
    my_map_analyser = analyser.MapAnalyser(image_path, resource_colors, side_length_of_pixel_in_tiles)
    map_analyser_coordinate_wrapper = my_map_analyser.map_analyser_coordinate_wrapper
    return callback_analyser_function(map_analyser_coordinate_wrapper)


class ImageAnalyserPool:
    def __init__(self, max_workers: int = None):
        self._max_workers = max_workers
        self._tasks = []
        if MULTIPROCESS:
            self._tasks_results_futures = []
        else:
            self._tasks_results = []

    def add_folder_of_images_to_analyse(self, folder_path: str, file_extension: str,
                                        callback_analyser_function: Callable[
                                            [analyser_coordinate_wrapper.MapAnalyserCoordinateWrapper], list[str]],
                                        resource_colors: dict[str, tuple[int, int, int]],
                                        side_length_of_pixel_in_tiles: int):
        """Adds each images in a folder as a task"""
        image_paths_to_add = glob.glob(folder_path + "/*" + file_extension)
        callback_analyser_function_list = [callback_analyser_function] * len(image_paths_to_add)
        resource_colors_list = [resource_colors] * len(image_paths_to_add)
        side_length_of_pixel_in_tiles_list = [side_length_of_pixel_in_tiles] * len(image_paths_to_add)
        tasks_to_add = list(zip(callback_analyser_function_list, image_paths_to_add,
                                resource_colors_list, side_length_of_pixel_in_tiles_list))
        self._tasks.extend(tasks_to_add)

    def analyse(self):
        """Starts the actual analysing process"""
        if MULTIPROCESS:
            with concurrent.futures.ProcessPoolExecutor(max_workers=self._max_workers) as executor:
                # TODO: Why doesn't this work for the progress bar?
                # self._tasks_results_futures = list(tqdm(executor.map(_analyse, self._tasks), total=len(self._tasks)))
                self._tasks_results_futures = executor.map(_analyse, self._tasks)
        else:
            for task in self._tasks:
                self._tasks_results.append(_analyse(task))

    def save_results_to_csv(self, path: str = "results.csv"):
        """Writes the results of each analysed image into a row in a .csv file unless it is None"""
        if MULTIPROCESS:
            tasks_results = list(self._tasks_results_futures)
        else:
            tasks_results = self._tasks_results
        tasks_results = list(filter(None, tasks_results))
        file = open(path, 'w+', newline='')
        with file:
            write = csv.writer(file)
            write.writerows(tasks_results)
