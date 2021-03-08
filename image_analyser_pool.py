import glob
import concurrent.futures
from typing import Callable, Optional

from tqdm import tqdm
import csv
import analyser
import analyser_coordinate_wrapper

MULTIPROCESS = False  # False is useful to debug and analyse the performance in the profiler. True for faster execution.


def _analyse(
    callback_analyser_function: Callable[
        [analyser_coordinate_wrapper.MapAnalyserCoordinateWrapper], Optional[list[str]]
    ],
    parameters: tuple[str, dict[str, tuple[int, int, int]], int],
) -> Optional[list[str]]:
    """Creates an analyser for the maps and calls the callback function with the wrapped analyser
    This is where the multiprocessing starts. Return the result of the analysing function
    """
    image_path = parameters[0]
    resource_colors = parameters[1]
    tiles_per_pixel = parameters[2]
    my_map_analyser = analyser.MapAnalyser(image_path, resource_colors, tiles_per_pixel)
    map_analyser_coordinate_wrapper = my_map_analyser.map_analyser_coordinate_wrapper
    return callback_analyser_function(map_analyser_coordinate_wrapper)


class ImageAnalyserPool:
    def __init__(self, max_workers: int = None):
        self._max_workers = max_workers
        self._tasks_parameters: list[tuple[str, dict[str, tuple[int, int, int]], int]] = []
        self._tasks_results: list[list[str]] = []

    def add_folder_of_images_to_analyse(
        self,
        folder_path: str,
        file_extension: str = ".png",
        resource_colors: dict[str, tuple[int, int, int]] = None,
        tiles_per_pixel: int = 8,
    ):
        if resource_colors is None:
            resource_colors = {
                "iron": (104, 132, 146),
                "copper": (203, 97, 53),
                "coal": (0, 0, 0),
                "water": (51, 83, 95),
            }
        """Adds each image in a folder as a task"""
        image_paths = glob.glob(folder_path + "/*" + file_extension)
        for image_path in image_paths:
            self._tasks_parameters.append((image_path, resource_colors, tiles_per_pixel))

    def analyse(
        self,
        callback_analyser_function: Callable[
            [analyser_coordinate_wrapper.MapAnalyserCoordinateWrapper], Optional[list[str]]
        ],
        multiprocess: bool = True,
        tqdm_disable: bool = False,
    ):
        """Starts the actual analysing process"""
        if multiprocess:
            with concurrent.futures.ProcessPoolExecutor(max_workers=self._max_workers) as executor:
                with tqdm(total=len(self._tasks_parameters), disable=tqdm_disable) as progress:
                    futures = []
                    for parameters in self._tasks_parameters:
                        future = executor.submit(_analyse, callback_analyser_function, parameters)
                        future.add_done_callback(lambda p: progress.update())
                        futures.append(future)
                    for future in futures:
                        result = future.result()
                        if result is not None:
                            self._tasks_results.append(result)
        else:
            for parameters in tqdm(self._tasks_parameters, disable=tqdm_disable):
                result = _analyse(callback_analyser_function, parameters)
                if result is not None:
                    self._tasks_results.append(result)

    def save_results_to_csv(self, path: str = "results.csv"):
        """Writes the results of each analysed image into a row in a .csv file unless it is None"""
        file = open(path, "w+", newline="")
        with file:
            write = csv.writer(file)
            write.writerows(self._tasks_results)
