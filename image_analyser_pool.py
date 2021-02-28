import glob
import concurrent.futures
from typing import Callable

import csv
import analyser
import analyser_coordinate_wrapper

MULTIPROCESS = False  # False is useful to analyse the performance in the profiler


def _analyse(tasks: tuple[Callable[[analyser_coordinate_wrapper.MapAnalyserCoordinateWrapper], list[str]],
                          str, dict[str, tuple[int, int, int]], int]) -> list[str]:
    my_map_analyser = analyser.MapAnalyser(tasks[1], tasks[2], tasks[3])
    return tasks[0](my_map_analyser.map_analyser_coordinate_wrapper)


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
        image_paths_to_add = glob.glob(folder_path + "/*" + file_extension)
        callback_analyser_function_list = [callback_analyser_function] * len(image_paths_to_add)
        resource_colors_list = [resource_colors] * len(image_paths_to_add)
        side_length_of_pixel_in_tiles_list = [side_length_of_pixel_in_tiles] * len(image_paths_to_add)
        tasks_to_add = list(zip(callback_analyser_function_list, image_paths_to_add,
                                resource_colors_list, side_length_of_pixel_in_tiles_list))
        self._tasks.extend(tasks_to_add)

    def analyse(self):
        if MULTIPROCESS:
            with concurrent.futures.ProcessPoolExecutor(max_workers=self._max_workers) as executor:
                # executor.map(_analyse, self._tasks)
                self._tasks_results_futures = executor.map(_analyse, self._tasks)
        else:
            for task in self._tasks:
                self._tasks_results.append(_analyse(task))

    def save_results_to_csv(self, path: str = "results.csv"):
        file = open(path, 'w+', newline='')
        with file:
            write = csv.writer(file)
            if MULTIPROCESS:
                write.writerows(self._tasks_results_futures)
            else:
                write.writerows(self._tasks_results)
