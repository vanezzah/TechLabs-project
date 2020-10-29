from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime
from sqlalchemy import Table
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship
import pandas as pd
import googlemaps
import json, requests
from datetime import datetime, timedelta, date
import gmplot
import matplotlib.pyplot as plt

Base = declarative_base()

class Api(Base):
    """
    Contains all API keys that are needed for the venueSearch algorithm.

    ...

    Attributes
    ----------
    id : integer
        Used to identify the API.
    name : string
        Name of the API.
    key : string
        Key for the request from the database.

    """
    __tablename__ = 'api'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    key = Column(String)
    client_id = Column(String)
    client_secret = Column(String)

class Venue(Base):
    __tablename__ = 'venue'

    id = Column(String, primary_key=True)
    name = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    distance = Column(Integer)
    category = Column(String)

    # rating = Column(Float)
    # description = Column(String)
    # current_visitors = Column(Integer)

    def request_venues(userRequest, session):
        """
        Requests venues that fit to the user request and returns a DataFrame
        of these venues that contains basic information for every venue.

        Parameters
        ----------
        session :
            The session that is created by the sqlalchemy sessionmaker and
            and acts as a link to the database and contains the data that are
            needed tho proceed the venue search algorithm.
        userRequest :
            Dictionary that contains the search parameters of the user.

        """

        # Load API detail
        api = session.query(Api).filter(Api.name == 'foursquare').first()

        # Define coordinates
        lat = userRequest['lat']
        lng = userRequest['lng']

        # Get todays date
        today = date.today()
        version = today.strftime("%Y%m%d")

        # Set search parameters
        params = dict(
            client_id=api.client_id,
            client_secret=api.client_secret,
            v=version,
            ll=str(lat) + ', ' + str(lng),
            query=[userRequest['search_input']],
            limit=150,
            suggestedRadius=userRequest['search_radius']
        )

        # Request venues from foursquare API
        url='https://api.foursquare.com/v2/venues/explore'
        resp = requests.get(url=url, params=params)
        venues = json.loads(resp.text)['response']['groups'][0]['items']

        # Format results with all needed values into a dictionary
        venues_dict = {
            venue['venue']['id']: [
                venue['venue']['name'],
                venue['venue']['location']['lat'],
                venue['venue']['location']['lng'],
                venue['venue']['location']['distance'],
                venue['venue']['categories'][0]['name']
            ]
            for venue in venues
        }

        # Create venue DataFrame
        venue_details_df = pd.DataFrame.from_dict(
            venues_dict,
            orient='index',
            columns=[
                'name', 'lat', 'lng', 'distance', 'categorie'
            ]
        )

        return venue_details_df

    def get_hour_details(session, venues_df):
        """
            Gets the opening and popular hours of a DataFrame of venues from the
            foursquare API and returns a dataframe that contains the hour
            details per venue.

            Parameters
            ----------
            session :
                The session that is created by the sqlalchemy sessionmaker and
                and acts as a link to the database and contains the data that are
                needed tho proceed the venue search algorithm.
            venuse_df :
                DataFrame that contains basic information for all venues that
                fit to the user request.

        """

        # Load API detail
        api = session.query(Api).filter(Api.name == 'foursquare').first()

        # Get todays date
        today = date.today()
        version = today.strftime("%Y%m%d")

        params = dict(
            client_id=api.client_id,
            client_secret=api.client_secret,
            v=version,
        )

        # Loop over every venue ID
        opening_hours = {}
        popular_hours = {}
        for venue_id in venues_df.index.to_list():
            hours_url = 'https://api.foursquare.com/v2/venues/{}/hours'.\
                format(venue_id)
            resp = requests.get(url=hours_url, params=params)
            response = json.loads(resp.text)['response']

            # Only consider venues with available opening hours and popular hours
            if 'timeframes' in response['hours'] and response['popular']:
                # Get opening hours per day sorted by venue_id
                opening_hours[venue_id] = {
                    day: {
                        'start': time_slot['start'],
                        'end': time_slot['end']
                    }
                    for data in response['hours']['timeframes']
                    for day in data['days']
                    for time_slot in data['open']
                }

                # Get popular hours per day sorted by venue_id
                popular_hours[venue_id] = {
                    day: {
                        'start': time_slot['start'],
                        'end': time_slot['end']
                    }
                    for data in response['popular']['timeframes']
                    for day in data['days']
                    for time_slot in data['open']
                }

        hour_details = {'open': opening_hours, 'popular': popular_hours}

        # Create DataFrame that contains the hour details of the venues
        hour_details_dict = {
            venue_id : [
                int(hour_details[hour_type][venue_id][day][x])
                for day in hour_details['open'][venue_id]
                for hour_type in ['open', 'popular']
                for x in ['start', 'end']
            ]
            for venue_id in hour_details['open']
        }

        hour_details_df = pd.DataFrame.from_dict(
            hour_details_dict,
            orient='index',
            columns=[
                'monday_open', 'monday_close', 'monday_popular_start',
                'monday_popular_end',
                'tuesday_open', 'tuesday_close', 'tuesday_popular_start',
                'tuesday_popular_end',
                'wensday_open', 'wensday_close', 'wensday_popular_start',
                'wensday_popular_end',
                'thursday_open', 'thursday_close', 'thursday_popular_start',
                'thursday_popular_end',
                'friday_open', 'friday_close', 'friday_popular_start',
                'friday_popular_end',
                'saturday_open', 'saturday_close', 'saturday_popular_start',
                'saturday_popular_end',
                'sunday_open', 'sunday_close', 'sunday_popular_start',
                'sunday_popular_end',
            ]
        )

        return hour_details_df

    def filter_results(userRequest, venues_df, hours_df):
        """
        Filters for results that normally have no peak time in a two-hour period
        from the requested visit time. If there are less than five results after
        filtering the algorithm searches for suitable venues for slightly
        different times.

        Parameters
        ----------
            userRequest :
                Dictionary that contains the search parameters of the user.
            venues_df :
                DataFrame that contains basic information for all venues that
                fit to the user request.
            hour_df:
                DataFrame that contains all the hour details of the possible
                venues that fit the users request.
            delta : integer
                Defines the postponement of the visit time

        """
        from datetime import datetime

        # Get Weekday name as a string
        weekdays = [
            'monday','tuesday','wensday','thursday','friday','saturday','sunday'
        ]
        datetime = datetime.strptime(
            userRequest['datetime'], '%Y-%m-%d %H:%M:%S')
        weekday = weekdays[datetime.weekday()]

        # Define the names for the relevant columns of the hours_df DataFrame
        day_open = weekday + "_open"
        day_close = weekday + "_close"
        day_pops = weekday + "_popular_start"
        day_pope = weekday + "_popular_end"

        # Converts the
        time = datetime.hour * 100

        results = hours_df[
            (hours_df[day_open] <= time)
            & ((hours_df[day_close] >= time + 200) | (hours_df[day_close] <= 300))
            & ((hours_df[day_pops] >= time + 200) | (hours_df[day_pope] <= time))
        ]

        venue_results = venues_df[venues_df.index.isin(results.index)]

        # Get venue suggestions for slightly different times
        if len(results) < 5:
            suggestions_hours = pd.DataFrame()

            # Get suggestions for different visit times
            for delta in [1, -1, 2, -2]:
                suggestions_hours = suggestions_hours.append(hours_df[
                    (hours_df[day_open] <= time)
                    & ((hours_df[day_close] >= time + delta) | (hours_df[day_close] <= 300))
                    & ((hours_df[day_pops] >= time + delta) | (hours_df[day_pope] <= time))
                ])

            # Delete dupklicate rows
            suggestions_hours = suggestions_hours.reset_index().\
                    drop_duplicates(subset='index', keep='first').\
                    set_index('index')

            # Get the venue details of by the index suggestions_hours
            venue_suggestions = venues_df[
                venues_df.index.isin(suggestions_hours.index)]

        return venue_results, venue_suggestions



class UserRequest(Base):
    __tablename__ = 'userrequest'

    id = Column(Integer, primary_key=True)
    city = Column(String)
    datetime = Column(DateTime)
    lat = Column(Float)
    lng = Column(Float)
    search_input = Column(String)
    search_radius = Column(Integer)
    categorie = Column(String)
    venue_name = Column(String)


class CovidData(Base):
    """
    A class used to represent the covid-19 data for the area of the users
    search

    ...

    Attributes
    ----------
    id : integer
        Used for the unique identification of a covid-19 dataset.
    user_request_id : integer
        Used for the identification of the related user request.
    county : String
        Name of the area the covid-19 data are related to.
    cases : integer
        Number of cases
    cases_7_days_per_100K : Float
        Number of cases in the last seven days per 100K residents

    Methods
    -------
    request_data
        Requests the covid-19 data for the location given by the
        users request.

    """
    __tablename__ = 'coviddata'

    id = Column(Integer, primary_key=True)
    user_request_id = Column(Integer, ForeignKey('userrequest.id'))
    area_name = Column(String)
    county = Column(String)
    cases = Column(Integer)
    deaths = Column(Integer)
    cases_7_days_per_100K = Column(Float)

    def request_data(userRequest, session):
        """
        Requests the covid-19 data for the location given by the
        users request.

        Parameters
        ----------
        session :
            The session that is created by the sqlalchemy sessionmaker and
            and acts as a link to the database and contains the data that are
            needed tho proceed the venue search algorithm.
        userRequest :
            Dictionary that contains the search parameters of the user.

        """

        # Read the list that contains all areas with its related googlemaps_key
        # that are considered in the RKI covid-19 database.
        areas_df = pd.read_csv('areas_with_googlemaps_key.csv', index_col=0)

        # Define coordinates
        lat = userRequest['lat']
        lng = userRequest['lng']

        # Create googlemaps client
        api = session.query(Api).filter(Api.name == 'googlemaps').first()
        client = googlemaps.Client(key=api.key)
        geocode = client.reverse_geocode((lat, lng))

        # Format the google geocode into a dictionary
        geocode_dict = {
            type: element['long_name']
            for element in geocode[0]['address_components']
            for type in element['types']
        }

        # Extract the necessery key value pairs in the geocode dictionary
        necessery_keys = [
            'sublocality', 'locality', 'administrative_area_level_3'
        ]
        geocode_dict = {
            key : geocode_dict[key]
            for key in necessery_keys
            if key in geocode_dict
        }

        # Find the googlemaps_key for the covid-19 database in the given geocode
        googlemaps_key = areas_df[
            areas_df['googlemaps_key'].isin(geocode_dict.values())]['GEN']
        googlemaps_key = googlemaps_key.iloc[0]

        # Request Covid-19 data
        url = "https://services7.arcgis.com/mOBPykOjAyBO2ZKk/arcgis/\
rest/services/RKI_Landkreisdaten/FeatureServer/0/query\
?where=GEN = '{}'&outFields=GEN,cases,deaths,county,\
cases7_per_100k,BEZ,BL&f=json".format(googlemaps_key)
        resp = requests.get(url=url)
        covid_data = json.loads(resp.text)

        # Create DataFrame that contains the covid data and save it into a
        # .csv file
        covid_data = [row['attributes'] for row in covid_data['features']]
        covid_data_df = pd.DataFrame(covid_data)
        covid_data_df.to_csv('covid_data.csv')
        print(covid_data_df)

        # Write results to database
        session.add(
            CovidData(
                user_request_id=userRequest['request_ID'],
                area_name = covid_data_df.loc[0, 'GEN'],
                county = covid_data_df.loc[0, 'county'],
                cases = covid_data_df.loc[0, 'cases'],
                deaths = covid_data_df.loc[0, 'deaths'],
                cases_7_days_per_100K = covid_data_df.loc[0, 'cases7_per_100k']
            )
        )
        session.commit()

class CreateImages(object):
    """
    Contains methods that are used to create images to picture the results.

    ...

    Methods
    -------
    maps_plot
        Creates a html element that contains a adjustable google maps map
        on which the venues are marked.
    """

    def maps_plot(session, venue_results, venue_suggestions):
        """
        Creates a html element that contains a adjustable google maps map
        on which the venues are marked.

        Parameters
        ----------
        venue_results
            Contains details of the venues that fit completly to users request.
        venue_suggestions
            Contains details of suitable venues for slightly different times.

        """

        # Delete duplicate rows
        index = venue_suggestions.append(venue_results).index.drop_duplicates(keep=False).to_list()
        venue_suggestions = venue_suggestions.loc[index]

        # Get coordinates
        venue_results_lat = venue_results["lat"].to_list()
        venue_results_lng = venue_results["lng"].to_list()
        venue_suggestions_lat = venue_suggestions['lat'].to_list()
        venue_suggestions_lng = venue_suggestions['lng'].to_list()

        #declare the center of the map, and how much we want the map zoomed in
        gmap = gmplot.GoogleMapPlotter(52.518600, 13.401552, 13)

        # Scatter map
        gmap.scatter(
            venue_results_lat,
            venue_results_lng,
            '#FF0000',
            size=50,
            marker=True
        )
        gmap.scatter(
            venue_suggestions_lat,
            venue_suggestions_lng,
            '#0000FF',
            size=50,
            marker=True
        )

        #Your Google_API_Key
        api = session.query(Api).filter(Api.name == 'googlemaps').first()
        gmap.apikey = "AIzaSyBrKCuyTCW0GTqzMDb2bwQRpca3LgWBvr0"

        # save it to html
        gmap.draw("scatter.html")

    def plot_results_hours(userRequest, venue_results, hours_df):
        """
        Creates a plot that gives an overview of when the venues are
        colesd, open and highly frequented.

        Parameters
        ----------
        venue_results
            Contains details of the venues that fit completly to users request.
        userRequest :
            Dictionary that contains the search parameters of the user.
        hours_df:
            DataFrame that contains all the hour details of the possible
            venues that fit the users request.

        """
        # Get Weekday name as a string
        weekdays = [
            'monday','tuesday','wensday','thursday','friday','saturday','sunday'
        ]
        visit_datetime = datetime.strptime(
            userRequest['datetime'], '%Y-%m-%d %H:%M:%S')
        weekday = weekdays[visit_datetime.weekday()]

        # Create Figure and Axis
        fig, ax = plt.subplots()

        # Create hours plot for every restaurant
        offset = range(0, len(venue_results.index.to_list()), 1)
        count = 0
        for venue_id in venue_results.index.to_list():
            open = hours_df.loc[venue_id, weekday + "_open"]*0.01
            close = hours_df.loc[venue_id, weekday + "_close"]*0.01
            popular_hours_start = hours_df.loc[venue_id, weekday+"_popular_start"]*0.01
            popular_hours_end = hours_df.loc[venue_id, weekday+"_popular_end"]*0.01

            if open > close:
                close = 24

            # Create bar plots
            ax.broken_barh(
                [(0, 24)],
                (offset[count]-0.35, 0.7),
                facecolors='tab:grey'
            )
            ax.broken_barh(
                [(open, close-open)],
                (offset[count]-0.35, 0.7),
                facecolors='tab:green'
            )
            ax.broken_barh(
                [(popular_hours_start, popular_hours_end-popular_hours_start)],
                (offset[count]-0.35, 0.7),
                facecolors='tab:red'
            )

            count = count+1

        # Plot the planned visit time of the user
        ax.axvline(int(visit_datetime.hour))

        # Set general plot parameters
        plt.xlim(0, 24)
        plt.title('Overview')
        ax.set_xlabel('Time')
        ax.set_yticks(offset)
        ax.set_yticklabels(venue_results['name'].to_list())
        ax.set_ylabel('Restaurant name')

        # get rid of the frame and ticks
        for spine in plt.gca().spines.values():
            spine.set_visible(False)
        ax.tick_params(axis='both', which='both', length=0)

        # Create Space on the side for the legend
        box = ax.get_position()
        ax.set_position([box.x0, box.y0, box.width * 0.8, box.height])

        # Create legend
        ax.legend(
            ['planned visit', 'closed', 'open', 'popular'],
            loc='center left',
            bbox_to_anchor=(1, 0.5))

        plt.xlim(0, 24)
        plt.savefig('Overview.png')
