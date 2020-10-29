import googlemaps
import pandas as pd
import numpy as np

class CreateEnvironment(object):
    """
    Contains functions that are used to preperate the data for the venue search
    algorithm

    Methods
    -------
    googlemapsKeyForCovidDatabase
        Creates a key (googlemaps_key) to identify the related area that
        is considered in the covid-19 database of a googlemaps geocode.

    """

    def googlemapsKeyForCovidDatabase():
        """
        Creates a key (googlemaps_key) to identify the related area that
        is considered in the covid-19 database of a googlemaps geocode.
        Therefore the geocode of every covid-19 area is requested from
        the googlemaps geocode API. The value of the geocode that identifies
        the related area is then used as the googlemaps_key of the covid-19
        database. The result is stored in a .csv file.

        """

        # Create googlemaps client
        client = googlemaps.Client(key='AIzaSyBrKCuyTCW0GTqzMDb2bwQRpca3LgWBvr0')

        # Read locations from csv
        areas_df = pd.read_csv('areas.csv')

        # Request geocodes of all locations from google Geocoding API
        locations =  areas_df['GEN'].to_list()
        geocodes = {loc: client.geocode(loc) for loc in locations}

        # Format the google geocodes into a dictionary
        geocodes_dict = {
            location :
            {
                type: element['long_name']
                for element in geocodes[location][0]['address_components']
                for type in element['types']
            }
            for location in geocodes
        }

        # Format and save the google geocodes into a DataFrame
        geocodes_df = pd.DataFrame.from_dict(geocodes_dict, orient='index')
        geocodes_df.to_csv('geocodes.csv')

        # Get googlemaps merging key for covid database entrys
        areas_df['googlemaps_key'] = np.nan
        for index, area in areas_df.iterrows():
            # The if-querys are used to identify the different administrations
            # levels of the areas for which the covid-19 data are provided.
            # This differentiation is needed to get the value from the googlemaps
            # geocode that clearly identifys every area.
            if area['BEZ'] in ['Landkreis', 'Kreis']:
                if type(geocodes_df.loc[area['GEN']]['administrative_area_level_3']) == str:
                    areas_df.loc[index, 'googlemaps_key'] = geocodes_df.\
                        loc[area['GEN']]['administrative_area_level_3']
                else:
                    areas_df.loc[index, 'googlemaps_key'] = geocodes_df.\
                        loc[area['GEN']]['locality']
            if area['BEZ'] in ['Kreisfreie Stadt', 'Stadtkreis']:
                areas_df.loc[index, 'googlemaps_key'] = geocodes_df.\
                    loc[area['GEN']]['locality']
            if area['BEZ'] in ['Bezirk']:
                areas_df.loc[index, 'googlemaps_key'] = geocodes_df.\
                    loc[area['GEN']]['sublocality']

        # Save results in .csv file
        areas_df.to_csv('areas_with_googlemaps_key.csv')
