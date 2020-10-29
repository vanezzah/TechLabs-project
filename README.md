# StartDistancing
Our solution allows people to make data and fact driven decisions regarding restaurant choices during the covid-19 crisis and enables smart social distancing. Our solution takes in several arguments from the user, such as his current location, the date and time at which he wants to go out and the preferred restaurant category.The algorithm makes an API call to Foursquare to find restaurants in the area and filters the results to show the restaurants that are open and not busy at that time (meaning that the time given is not inside the popular hours timeframe returned by the API). After some data cleaning, it then filters therestaurants by category and orders them by distance to the user. They are plotted on a map and a visualization of opening and popular hours is shown. If there are not enough results, suitable venues for slightly different times are searched.Additionally, the covid-19 data for the area is shown to raise awareness of the current situation and to make it easier for the user to assess if he should go out at all. This information is retrieved through the data published by the RKI and matched with the user’s administrative area

## Get started
### Make shure that the following packages are installed
  - json
  - requests
  - pandas
  - numpy
  - sqlalchemy
  - googlemaps
  - datetime
  - gmplot
  - matplotlib

### Execute Algorithm
After pulling the master branch you could execute the venue search algorithm by running the venueSearch.py file. The algorithm will use the examplary user request that is defined in the userRequest.json file. To redefine the search parameters 
{"request_ID": "277f7sk392h", "datetime": "2020-11-01 18:00:00", "lat": 52.5186, "lng": 13.401552, "search_radius": 2, "search_input": "restaurant"}

## 
The venueSearch.py file is the master file of the program. The functions that

## Database Errors
If any errors occur during the processiong of the venue search algorithm try again after deleting the venue.db database file from your directory. A fresh database will be created automaticly.
