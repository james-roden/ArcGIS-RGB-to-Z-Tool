# ArcGIS-RGB-to-Z-Tool
*Created by James M Roden*

An ArcGIS toolbox to convert RGB values to their corresponding z-values as denoted in the map’s legend.

![RGB IMAGE](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/RGB-image.png?raw=true)
*Georectified composite RGB image*

![Z IMAGE](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/Z-image.png?raw=true9)
*Z-Value raster derived from composite RGB image*

1. [Background](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/README.md#background-1)
2. Methodology
3. [Linear or Histogram Equalise](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/README.md#histogram-equalise)
4. How to Use

## Background
Composite images, like that in figure 1, more often than not contain three channels: red, green, blue (RGB). In a 24-bit RGB image each channel has 8-bits – in other words the image is composed of three images (one for each channel). Each of these channels has varying intensities between 0 and 255. The combination of these 3 channels results in a possible 16,777,216 colours. 

When the original map was created in GIS software however, the raster (the bathymetry in figure 1) would have been a single channel raster where its values would not have been representing intensities of red, green or blue; but representing the sea floor depth in meters (z-value). The map creator will have chosen a colour-ramp to stretch over the raster’s z-values, in this example where red corresponds to a z-value of 0, yellow corresponds to a z-value of -50 and so on. Only when the map was exported to an image format did it become an RGB composite image, but this means we don’t have access to the original z-values to use in GIS or 3D modelling software. This tool aims to reverse engineer the image to its original single band z-value raster by mapping the pixels RGB value to its z-value equivalent by using the map legend as a guide. 

## Histogram Equalise
Text here.
