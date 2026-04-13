from shapely.geometry import Point as ShapelyPoint
from shapely.geometry.polygon import Polygon as ShapelyPolygon
from ipyleaflet import Rectangle


class MowedPixel:
    """
    A class representing a rectangular area defined by two corners, with properties for mowing amount, sea status,
    and the number of times it has been passed through. It provides methods to calculate the center, generate Shapely geometries,
    and create visual representations in different formats such as RGB color, HTML color, RGBA string color, ipyleaflet rectangle,
    and GeoJSON rectangle.
    """
    def __init__(self, corner_1: tuple, corner_2: tuple):
        """
        Initialize a MowedPixel object.

        :param corner_1: Coordinates of the first corner (latitude, longitude).
        :param corner_2: Coordinates of the second corner (latitude, longitude).
        """
        self.corner_1 = corner_1
        self.corner_2 = corner_2
        self.in_sea = False
        self.mowes_ammount = 0.0
        self.number_pass_through = 0

    def to_array(self):
        return [self.corner_1, self.corner_2, self.mowes_ammount, self.in_sea, self.number_pass_through]

    def to_dict(self):
        return {
            "corner_1": self.corner_1,
            "corner_2": self.corner_2,
            "mowes_ammount": self.mowes_ammount,
            "in_sea": self.in_sea,
            "number_pass_through": self.number_pass_through
        }

    def get_center(self) -> tuple:
        """
        Calculate the center of the pixel.

        :return: Coordinates of the center (latitude, longitude).
        """
        return ((self.corner_1[0] + self.corner_2[0]) / 2, (self.corner_1[1] + self.corner_2[1]) / 2)
    
    def get_shapely_point(self) -> ShapelyPoint:
        """
        Get the center of the pixel as a Shapely Point object.

        :return: Shapely Point object representing the center of the pixel.
        """
        center = self.get_center()
        return ShapelyPoint(center)
    
    def get_shapely_polygon(self) -> ShapelyPolygon:
        """
        Get the pixel as a Shapely Polygon object.

        :return: Shapely Polygon object representing the pixel.
        """
        return ShapelyPolygon([self.corner_1, (self.corner_1[0], self.corner_2[1]), self.corner_2, (self.corner_2[0], self.corner_1[1])])
    
    def get_rgb_color(self) -> tuple:
        """
        Get the RGB color representation of the pixel.
        Here, green indicates mowed areas, blue indicates sea areas, and black indicates other areas.

        :return: Tuple representing the RGB color (R, G, B).
        """
        if self.mowes_ammount > 0:
            return (0, 255, 0)  # Green for mowed areas
        elif self.in_sea: 
            return (0, 0, 255)  # Blue for sea areas
        else:
            return (0, 0, 0)  # Black for other areas
    
    def get_html_color(self) -> str:
        """
        Get the HTML color representation of the pixel.

        :return: HTML color string (e.g., '#00ff00').
        """
        color = self.get_rgb_color()
        return f'#{color[0]:02x}{color[1]:02x}{color[2]:02x}'
    
    def get_rgba_string_color(self, alpha: float = 0.05) -> str:
        """
        Get the RGBA color representation of the pixel as a string.

        :param alpha: Alpha value for transparency (default is 0.05).
        :return: RGBA color string (e.g., 'rgba(0, 255, 0, 0.05)').
        """
        color = self.get_rgb_color()
        return f'rgba({color[0]}, {color[1]}, {color[2]}, {alpha})'

    def get_ipyleaflet_rectangle(self) -> Rectangle:
        """
        Get the pixel as an ipyleaflet Rectangle object.

        :return: ipyleaflet Rectangle object representing the pixel.
        """
        rectangle = Rectangle(bounds=(self.corner_1, self.corner_2))
        rectangle.color = self.get_rgba_string_color()  # Border color
        rectangle.fill_color = self.get_html_color()  # Fill color
        return rectangle
    
    def get_geojson_rectangle(self, with_color_properties: bool = True) -> dict:
        """
        Get the pixel as a GeoJSON rectangle.

        :param with_color_properties: If True, include color properties in the GeoJSON (default is True).
        :return: Dictionary representing the GeoJSON rectangle.
        """
        corner_1 = [self.corner_1[1], self.corner_1[0]]  # Swap lat/lon for GeoJSON format
        corner_2 = [self.corner_2[1], self.corner_2[0]]
        coordinats = [[
            corner_1, [corner_1[0], corner_2[1]], corner_2, [corner_2[0], corner_1[1]], corner_1
        ]]

        geojson_rectangle = {
            "type": "Feature",
            "properties": {
                "mowes_ammount": self.get_mowed_ammount(),
            },
            "geometry": {
                "coordinates": [],
                "type": "Polygon",
            },
        }

        if with_color_properties:
            geojson_rectangle["properties"]["fill"] = self.get_html_color()
            geojson_rectangle["properties"]["fill-opacity"] = 0.5
            geojson_rectangle["properties"]["stroke"] = self.get_html_color()
            geojson_rectangle["properties"]["stroke-opacity"] = 1
            geojson_rectangle["properties"]["stroke-width"] = 1

        geojson_rectangle["geometry"]["coordinates"] = coordinats
        return geojson_rectangle
    
    def get_mowed_ammount(self) -> float:
        """
        Get the rounded mowing amount for the pixel.

        :return: Rounded mowing amount as a float.
        """
        return round(float(self.mowes_ammount), 4)
