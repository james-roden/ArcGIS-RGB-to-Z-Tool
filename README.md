# ArcGIS-RGB-to-Z-Tool
*Created by James M Roden*

An ArcGIS toolbox to convert RGB values to their corresponding z-values as denoted in the map’s legend.

[DOWNLOAD](http://)

![RGB IMAGE](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/RGB-image.png?raw=true)
*Figure 1: Georectified composite RGB image*

![Z IMAGE](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/Z-image.png?raw=true9)
*Figure 2: Z-Value raster derived from composite RGB image*

## Index
1. [Background](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/README.md#background-1)
2. [Methodology](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/README.md#methodology)
3. [Histogram Equalise](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/README.md#histogram-equalise)
4. [How to Use](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/README.md#how-to-use)

## Background
Composite images, like that in figure 1, more often than not contain three channels: red, green, blue (RGB). In a 24-bit RGB image each channel has 8-bits – in other words the image is composed of three images (one for each channel). Each of these channels has varying intensities between 0 and 255. The combination of these 3 channels results in a possible 16,777,216 colours. 

When the original map was created in GIS software however, the raster (the bathymetry in figure 1) would have been a single channel raster where its values would not have been representing intensities of red, green or blue; but representing the sea floor depth in meters (z-value). The map creator will have chosen a colour-ramp to stretch over the raster’s z-values, in this example where red corresponds to a z-value of 0, yellow corresponds to a z-value of -50 and so on. Only when the map was exported to an image format did it become an RGB composite image, but this means we don’t have access to the original z-values to use in GIS or 3D modelling software. This tool aims to reverse engineer the image to its original single band z-value raster by mapping the pixels RGB value to its z-value equivalent by using the map legend as a guide. 

## Methodology
* Create *range* objects corresponding to the range of RGB colours between two z-values from text file. These objects contain a RGB minimum, RGB maximum, Z minimum, z maximum, RGB range, and z range attributes. From these we are able to calculate if a pixel's RGB value is within their range, and if it is, calculate it's corresponding z value. If it isn't, NoData is returned.
* Convert the raster to a NumPy array for manipulation.
* Re-stack the array into rows, columns and channels so that we can effectively run our functions through the 3 channels of the image.
* Loop over each pixel in the image and check if its RGB value falls within any of our previously made RGB range objects. If it does, call the RGB to Z method for that particular object. This method first calculates the *spectral position*, this is how far away from the RGB minimum the pixel's RGB channels sit. We take the largest range to allow more variance in the RGB to Z comparison. If using the *Linear Histogram* option the RGB and Z values are normalised and a Z value is returned in place of the 3 channels.
* Using the spatial data (CRS, cell width, cell height, etc.) from the original raster the new Z value NumpPy is converted back to raster format (and additional Points dataset).

## Histogram Equalise
Alternatively the *histogram equalise* stretch can be used opposed to *linear histogram* stretch.
Histogram equalisation is a method in image processing of contrast adjustment using the image’s histogram. The benefit of using this method is it allows for areas of lower local contrast to gain a higher contrast. It accomplishes this by effectively spreading out the most frequent intensity values. [Here](https://en.wikipedia.org/wiki/Histogram_equalization#Examples) is an example on how Histogram Equalisation works from Wikipedia. 

The general histogram equalization formula is:

![Histogram Equalise Formula](https://raw.githubusercontent.com/GISJMR/ArcGIS-RGB-to-Z-Tool/master/histogram-equalise-equation.png)

*Figure 3: General histogram equalise formula*

By rearranging the formula in figure 3 the histogram equalise formula can be reverse engineered to find the original pixel value.

![Rearranged equation](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/histogram-equalise-rearranged.png?raw=true)

*Figure 4: Rearranged histogram equalise formula*

* Create bins for histogram and subsequently 3 histograms for the three channels (RGB).
* Calculate the cumulative sums for each of the histograms
* Calculate the CDF minimums
* Using the rearranged formula from figure 3 calculate the CDF for each pixel.
* Return the index of the histogram bin with the minimum difference between the CDF value and CDF sum. This bin is the original *pixel value*

## How to Use
1. Georectify the RGB composite image in ArcMap
2. Using the eye-dropper tool carefully select RGB colours along the grids colour ramp in the legend. Copy and paste the RGB value into a new line in a blank text document followed by its corresponding Z value. Each new RGB-to-Z pairing needs to be on a new line as in figure 5 below. If you do not have the eye-dropper available in your toolbar already, please find instructions [here](http://www.esri.com/esri-news/arcwatch/1214/finding-colors-on-maps-is-easy-using-the-eye-dropper-tool)
3. Once all RGB to Z values are ready and your text file is saved, follow the instructions in the ArcGIS Toolbox.

![Text File](https://github.com/GISJMR/ArcGIS-RGB-to-Z-Tool/blob/master/textfileeg.png?raw=true)

*Figure 5: Text File Example*
