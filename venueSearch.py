import json, requests
import pandas as pd
import numpy as np
import schema as s
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create database and its sqlalchemy session
engine = create_engine('sqlite:///venues.db')
s.Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Define the API keys
session.add_all([
    s.Api(
        name='googlemaps',
        key='AIzaSyBrKCuyTCW0GTqzMDb2bwQRpca3LgWBvr0'
    ),
    s.Api(
        name='foursquare',
        client_id='JBYMNGLXZZI4IHZ3OHDSSUD4IA3VAJKWBGABDYNEE5VLHVRJ',
        client_secret='5LSXECLEBXMOSGCIFHWBT3PRSQTFDJCXNP0505325RUTZU54'
    )
])
session.commit()

# Load the user request from json file
with open('userRequest.json') as jsonfile:
    userRequest = json.load(jsonfile)

# Define the users request by importing it into the database
session.add(
    s.UserRequest(
        lat=userRequest['lat'],
        lng=userRequest['lng'],
        search_radius=userRequest['search_radius'],
        search_input=userRequest['search_input'],
    )
)
session.commit()

# Request the actual covid-19 data from the RKI API
s.CovidData.request_data(userRequest=userRequest, session=session)

# Request venues that fit to the user request
venues_df = s.Venue.request_venues(userRequest, session)
print(venues_df)
venues_df.to_csv('venues_df.csv')

# Request the hour details of these venues
hours_df = s.Venue.get_hour_details(session=session, venues_df=venues_df)
print(hours_df)

# venues_df.to_csv('venues_df.csv')
hours_df.to_csv('hours_df.csv')

# Filters for results that normally have no peak time in a two-hour period
# from the requested visit time. If there are less than five results after
# filtering the algorithm searches for suitable venues for slightly
# different times.
venue_results, venue_suggestions = s.Venue.filter_results(
    userRequest,
    venues_df,
    hours_df)

# Create maps plot
s.CreateImages.maps_plot(session, venue_results, venue_suggestions)

# Creates a plot that gives an overview of when the venues are
# colesd, open and highly frequented.
s.CreateImages.plot_results_hours(userRequest, venue_results, hours_df)
