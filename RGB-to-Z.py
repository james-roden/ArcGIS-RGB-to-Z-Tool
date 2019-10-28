# -----------------------------------------------
# Name: RGB to Z Raster Tool
# Version: 0.2.0 // Jan 2019
# Purpose: To convert RGB value to appropriate z value
# Author: James M Roden
# Created: Aug 2017
# ArcGIS Version: 10.5
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


class RangeError(Exception):
    def __init__(self, message):
        self.message = message


class _Range(object):
    """Object that contains the RGB & Z values for the base and top of the colour ramp. This is a private class that
    is used within the Rgb2z class.
    Attributes:
        _rgb_base      : The RGB base value.
        _rgb_top       : The RGB top value.
        _z_base        : The z base value.
        _z_top         : The z top value.
        _z_range       : The range between the top & bottom of z
        _rgb_ranges    : The range between the top & bottom of RGB
        _<colour>_top  : The top value of <colour>
        _<colour>_base : The base value of <colour>
    """

    def __init__(self, rgb_base, rgb_top, z_base, z_top):
        """Creates instance of _Range object
        Args:
            rgb_base : The RGB base value
            rgb_top  : The RGB top value
            z_base   : The z base value
            z_top    : The z top value
        """

        # Check if all RGB values are within correct range
        if not all(0 <= x <= 255 for x in [value for sublist in [rgb_base, rgb_top] for value in sublist]):
            raise RangeError('RGB values must be from 0 to 255')
        # Check if z_base is less than z_top
        if z_base > z_top:
            raise RangeError('The value of z_base must be less than z_top')
        self._rgb_base = rgb_base
        self._rgb_top = rgb_top
        self._z_base = z_base
        self._z_top = z_top
        self._z_range = abs(z_top - z_base)
        # Find top and base value for the three channels - used for in_range method
        self._red_base, self._red_top, self._green_base, self._green_top, self._blue_base, self._blue_top = \
            [value for sublist in [sorted(x) for x in zip(rgb_top, rgb_base)] for value in sublist]
        self._rgb_ranges = [abs(x - y) for x, y in zip(self._rgb_top, self._rgb_base)]
        self.mem_dict = {}

    def in_range(self, rgb):
        """Checks whether a RGB value is within the instances RGB range.
        Checks if red from rgb (input) is within the range of red_base and red_top of the instance. The same is done
        for green and blue.
        Args:
            rgb (tuple): RGB value to be checked if it is in instances RGB range
        Returns:
            Boolean: True if all values are within their respective RGB range
        """
        return (self._red_base <= rgb[0] <= self._red_top and self._green_base <= rgb[1] <= self._green_top
                and self._blue_base <= rgb[2] <= self._blue_top)

    def rgb_to_z(self, rgb):
        """Converts a RGB value to its corresponding z value from the instances mappings object.
        Maps the rgb value to the range and returns its corresponding z value.
        Args:
            rgb (tuple): RGB value to be converted to Z value
        Returns:
            Int: Corresponding Z value for RGB input
        """

        spectral_position = [abs(self._red_base - rgb[0]), abs(self._green_base - rgb[1]),
                             abs(self._blue_base - rgb[2])]
        # The largest range is taken to allow more variance in the rgb-to-z comparison
        max_range = max(spectral_position)
        max_index = spectral_position.index(max_range)  # Band with largest range
        if max_range != 0:
            z_value = max_range * (float(self._z_range) / float(self._rgb_ranges[max_index])) + self._z_base
            return round(z_value)
        # rgb is the same as the range rgb base.
        else:
            return self._z_base


def map_from_file(text_file):
    """Creates mappings list from correctly formatted text document.
    Updates the instances mapping attribute with a list of _Range objects from a correctly formatted text file.
    The text file must follow the format 'r g b z\n'
    Args:
        text_file: text file with 'r g b z\n' format
    """

    rgb_ranges = []
    with open(text_file) as f:
        content = f.readlines()
        content = [x.strip().split() for x in content]
        content = filter(None, content)  # Remove empty elements i.e. empty lines
        content = [[float(n) for n in sub] for sub in content]
        for i, item in enumerate(content[:-1]):
            rgb_base = tuple(content[i][:3])
            rgb_top = tuple(content[i + 1][:3])
            z_base = item[3]
            z_top = content[i + 1][3]
            rgb_ranges.append(_Range(rgb_base, rgb_top, z_base, z_top))

    return rgb_ranges


def _return_z(pixel, mappings, null_value):
    """Checks if a pixel is in a list of ranges, if yes, returns its corresponding z value
    Returns:
        int : z value
    """

    pixel = tuple(pixel)
    for mapping in mappings:
        if mapping.in_range(pixel):
            return mapping.rgb_to_z(pixel)

    # If not in any of the mappings, return null_value
    return null_value

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
    ranges = map_from_file(rgb_text_file)
    arcpy.AddMessage("RGB Range objects created from text file")

    # Create rgb raster numPy array
    rgb_raster_array = arcpy.RasterToNumPyArray(in_raster, nodata_to_value=no_data)
    arcpy.AddMessage("NumPy Array created from raster")

    # Re-stack array into rows, columns, and channels
    rgb_raster_array = np.dstack((rgb_raster_array[0], rgb_raster_array[1], rgb_raster_array[2]))
    # Run z-value function along channel axis
    z_raster_array = np.apply_along_axis(_return_z, 2, rgb_raster_array, ranges, no_data)
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
