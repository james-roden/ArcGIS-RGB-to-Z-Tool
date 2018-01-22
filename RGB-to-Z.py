# -----------------------------------------------
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
import os
import sys
import traceback


# Custom exception raster for band count
class CompositeImage(Exception):
    pass


# Custom exception raster georectified
class GeorectifiedImage(Exception):
    pass


# Custom exception RGB file format
class FileFormat(Exception):
    pass


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
        self.red, self.green, self.blue = [sorted(x) for x in zip(rgb_max, rgb_min)]
        self.rgb_range = tuple(abs(x - y) for x, y in zip(rgb_max, rgb_min))

        # Initialised in rgb_to_z
        self._z_value = None
        self._spectral_position = None
        self._largest_range = None
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

        # Spectral position is how far away from the rgb_min the rgb channels sit
        self._spectral_position = [abs(self.rgb_min[0] - rgb[0]), abs(self.rgb_min[1] - rgb[1]),
                                   abs(self.rgb_min[2] - rgb[2])]
        # The largest range is taken to allow more variance in the rgb-to-z comparison
        self._largest_range = max(self._spectral_position)
        self._band = self._spectral_position.index(self._largest_range)  # Band with largest range
        if self._largest_range != 0:
            self._z_value = self._largest_range * (float(self._z_range) / float(self.rgb_range[self._band])) \
                            + self.z_min
            return round(self._z_value)
        else:
            return self.z_min


def create_rgb_range(text_file):
    """
    Creates a list of RGB range objects from a correctly formatted text file

    text_file   -- Text file containing RGB ranges
    """

    rgb_ranges = []
    with open(text_file) as f:
        content = f.readlines()
        content = [x.strip().split() for x in content]
        content = filter(None, content)  # Remove empty elements i.e. empty lines
        content = [[int(n) for n in sub] for sub in content]
        for i, item in enumerate(content[:-1]):
            rgb_min = tuple(content[i][:3])
            rgb_max = tuple(content[i + 1][:3])
            z_min = item[3]
            z_max = content[i + 1][3]
            rgb_ranges.append(RgbRange(rgb_min, rgb_max, z_min, z_max))

    return rgb_ranges


def return_z_value(pixel, rgb_ranges, null_value):
    """
    Checks if the pixel is in any of the rgb ranges, if true it returns z, else returns NoData

    pixel           -- Pixel rgb value to check
    rgb_ranges      -- List of RgbRanges to check against
    """

    pixel = tuple(pixel)
    for rgb_range in rgb_ranges:
        if rgb_range.in_range(pixel):
            return rgb_range.rgb_to_z(pixel)

    # If not in any of the rgb_ranges return NoData number
    return null_value


def calculate_cdf(histogram_value, cum_sum, cdf_min, width, height, levels):
    """
    Reverse engineers the histogram equalisation formula to find original pixel value

    histogram_value -- Histogram equalised value
    cum_sum         -- Cumulative sum histogram
    cdf_min         -- CDF minimum
    width           -- Image width
    height          -- Image height
    levels          -- Levels of band. E.g. Red = 256
    """
    # Reverse levels multiplication of histogram value * (L-2)
    histogram_value = float(histogram_value) / (float(levels) - 2)
    # Work out (M * N) -1, named pixels
    pixels = (width * height) - 1
    # Multiply pixels out of both sides
    histogram_value *= pixels
    # Finally rearrange histogram and pixels to return cdf(value)
    cdf_value = histogram_value + cdf_min
    # Returns the index (bin) with the minimum difference between our cdf_value and cum_sum array elements
    # This bin is the 'pixel value' out of 256 bins we are after
    original_value = np.abs(cum_sum - cdf_value).argmin()
    return original_value

try:
    # arcpy environment settings
    arcpy.env.workspace = "in_memory"
    arcpy.env.scratchWorkspace = "in_memory"
    arcpy.env.overwriteOutput = True

    # ArcGIS tool parameters
    in_raster = arcpy.GetParameterAsText(0)
    rgb_text_file = arcpy.GetParameterAsText(1)
    no_data = int(arcpy.GetParameterAsText(2))
    workspace = arcpy.GetParameterAsText(3)
    histogram_method = arcpy.GetParameterAsText(4)

    # Describe properties of raster
    in_raster = arcpy.Raster(in_raster)

    # Check if raster has 3 bands
    if in_raster.bandCount < 3:
        raise CompositeImage

    # Check if raster is georectified
    if in_raster.spatialReference.type == 'Unknown':
        raise GeorectifiedImage

    lower_left = arcpy.Point(in_raster.extent.XMin, in_raster.extent.YMin)
    cell_width = in_raster.meanCellWidth
    cell_height = in_raster.meanCellHeight
    sr = in_raster.spatialReference
    raster_width = in_raster.width
    raster_height = in_raster.height

    # Create list of RgbRange objects from text file. Raise error if not correctly formatted
    try:
        ranges = create_rgb_range(rgb_text_file)
        arcpy.AddMessage("RGB Range objects created from text file")
    except FileFormat:
        error = "Text File is not formatted correctly."
        arcpy.AddError(error)
        print error

    # Create rgb raster numPy array
    rgb_raster_array = arcpy.RasterToNumPyArray(in_raster, nodata_to_value=no_data)
    arcpy.AddMessage("NumPy Array created from raster")

    # ----------------------------------#
    # Histogram Equalise
    # ----------------------------------#

    if histogram_method == "Histogram Equalised":
        # Create bins for histogram
        bins = np.arange(0, 256)
        arcpy.AddMessage("Histogram bins created")

        # Create histograms for 3 channels
        red_histogram = np.histogram(rgb_raster_array[0], bins)
        green_histogram = np.histogram(rgb_raster_array[1], bins)
        blue_histogram = np.histogram(rgb_raster_array[2], bins)

        # Cumulative sums of histograms
        red_cum_sum = np.cumsum(red_histogram[0])
        green_cum_sum = np.cumsum(red_histogram[1])
        blue_cum_sum = np.cumsum(red_histogram[2])
        arcpy.AddMessage("Cumulative sums calculated")

        # CDF minimums
        red_cdf_min = np.min(red_cum_sum[np.nonzero(red_cum_sum)])
        green_cdf_min = np.min(green_cum_sum[np.nonzero(green_cum_sum)])
        blue_cdf_min = np.min(blue_cum_sum[np.nonzero(blue_cum_sum)])
        arcpy.AddMessage("Cumulative distribution function (CDF) minimums calculated")

        # Calculate CDF for each cell in the 3 channels
        # Red
        for x in np.nditer(rgb_raster_array[0], op_flags=["readwrite"]):
            x[...] = calculate_cdf(x, red_cum_sum, red_cdf_min, raster_width, raster_height, 256)
        # Green
        for x in np.nditer(rgb_raster_array[1], op_flags=["readwrite"]):
            x[...] = calculate_cdf(x, green_cum_sum, green_cdf_min, raster_width, raster_height, 256)
        # Blue
        for x in np.nditer(rgb_raster_array[2], op_flags=["readwrite"]):
            x[...] = calculate_cdf(x, blue_cum_sum, blue_cdf_min, raster_width, raster_height, 256)
        arcpy.AddMessage("CDFs for each pixel calculated")

    # ----------------------------------#
    # end of histogram equalise
    # ----------------------------------#

    # Re-stack array into rows, columns, and channels
    rgb_raster_array = np.dstack((rgb_raster_array[0], rgb_raster_array[1], rgb_raster_array[2]))
    # Run z-value function along channel axis
    z_raster_array = np.apply_along_axis(return_z_value, 2, rgb_raster_array, ranges, no_data)
    z_raster = arcpy.NumPyArrayToRaster(z_raster_array, lower_left, cell_width, cell_height, no_data)
    arcpy.AddMessage("NumPy array re-stacked and z-value function ran across channel axis")

    # Create paths
    out_raster = os.path.join(workspace, "RGBtoZ_Ras")
    out_points = os.path.join(workspace, "RGBtoZ_Pnt")

    # Define raster, convert to points and save both outputs
    arcpy.CopyRaster_management(z_raster, out_raster)
    arcpy.DefineProjection_management(out_raster, sr)
    arcpy.RasterToPoint_conversion(out_raster, out_points)

except CompositeImage:
    error = "A RGB (3-band) composite image must be used."
    arcpy.AddError(error)
    print error

except GeorectifiedImage:
    error = "Raster must be projected"
    arcpy.AddError(error)
    print error

except FileFormat:
    error = "Incorrect text file format. See instructions"
    arcpy.AddError(error)
    print error

except:
    e = sys.exc_info()[1]
    arcpy.AddError(e.args[0])
    tb = sys.exc_info()[2]  # Traceback object
    tbinfo = traceback.format_tb(tb)[0]  # Traceback string
    # Concatenate error information and return to GP window
    pymsg = ('PYTHON ERRORS:\nTraceback info:\n' + tbinfo + '\nError Info: \n'
             + str(sys.exc_info()[1]))
    msgs = 'ArcPy ERRORS:\n' + arcpy.GetMessages() + '\n'
    arcpy.AddError(msgs)
    print pymsg

finally:
    # Delete in_memory
    arcpy.Delete_management('in_memory')
    arcpy.AddMessage("in_memory intermediate files deleted.")

# End of script
