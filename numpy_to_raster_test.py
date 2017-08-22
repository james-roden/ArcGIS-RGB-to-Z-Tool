# Name: RGB to Z Raster Tool
# Purpose: To convert RGB value to appropriate z value
# Author: James M Roden
# Created: Aug 2017
# ArcGIS Version: 10.3
# Dependencies: NumPy 1.7.1
# Python Version 2.6
# PEP8
# -----------------------------------------------

import arcpy
import numpy as np


class RgbRange(object):
    """
    Class representing a RGB colour range with associated z values

    rgb_min     -- tuple containing lowermost RGB value
    rgb_max     -- tuple containing uppermost RGB value
    z_min       -- int z value corresponding to rgb_min
    z_max       -- int z value corresponding to rgb_max
    """

    def __init__(self, rgb_min, rgb_max, z_min, z_max):
        self.rgb_min = rgb_min
        self.rgb_max = rgb_max
        self.z_min = z_min
        self.z_max = z_max
        self._z_range = abs(z_max - z_min)
        self.red, self.green, self.blue = [sorted(x) for x in zip(rgb_min, rgb_max)]
        self.rgb_range = tuple(abs(x - y) for x, y in zip(rgb_min, rgb_max))

        # Initialised in rgb_to_z
        self._z_value = None
        self._largest_range = None
        self._spectral_position = None
        self._band = None

    def in_range(self, rgb):
        """
        Checks whether rgb value is within range of rgb_min and rgb_max

        rgb     -- tuple to check
        """

        return (self.red[0] <= rgb[0] <= self.red[1] and self.green[0] <= rgb[1] <= self.green[1] and
                self.blue[0] <= rgb[2] <= self.blue[1])

    def rgb_to_z(self, rgb):
        """
        Returns corresponding z-value for rgb value

        rgb     -- rgb value for which a z-value will be returned
        """

        self._spectral_position = [abs(self.rgb_max[0] - rgb[0]), abs(self.rgb_max[1] - rgb[1]),
                                   abs(self.rgb_max[2] - rgb[2])]
        self._largest_range = max(self._spectral_position)
        self._band = self._spectral_position.index(self._largest_range)  # Band with largest range

        if self._largest_range != 0:
            self._z_value = self._largest_range * (self._z_range / self.rgb_range[self._band]) + self.z_min
            return round(self._z_value)
        else:
            return self.z_min


def return_z_value(pixel, rgb_ranges):
    """
    Checks if the pixel is in any of the rgb ranges, if true it returns z, else returns NoData

    pixel           -- Pixel rgb value to check
    rgb_ranges      -- List of RgbRanges to check against
    """

    pixel = tuple(pixel)
    for rgb_range in rgb_ranges:
        if rgb_range.in_range(pixel):
            return rgb_range.rgb_to_z(pixel)

    # If not in any of the rgb_ranges return -99999 (pseudo NoData number)
    return -99999


# arcpy environment settings
arcpy.env.workspace = "in_memory"
arcpy.env.scratchWorkspace = "in_memory"
arcpy.env.overwriteOutput = True

# TODO ArcGIS parameters
raster = None
lower_left = None
cell_size = None
sr = None

# TODO clean up string parameter and create RgbRange objects
ranges = None

# Run function over numPy array
rgb_raster_array = arcpy.RasterToNumPyArray(raster, nodata_to_value=-99999)
rgb_raster_array = np.dstack((rgb_raster_array[0], rgb_raster_array[1], rgb_raster_array[2]))
z_raster_array = np.apply_along_axis(return_z_value, 2, rgb_raster_array, ranges)
z_raster = arcpy.NumPyArrayToRaster(z_raster_array, lower_left, cell_size, cell_size, -99999)

# TODO Save final raster with defined spatial reference
