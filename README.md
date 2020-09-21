# Apana.dev
In-progress multi-purpose web project utilizing Python3, Flask, Bootstrap4, Datatables, SQLAlchemy, PostgreSQL, GeoLite2, and the Spotify API.
This code is hosted at [Apana.dev](https://apana.dev/) via AWS EC2, Elastic Beanstalk, and RDS.
Stay tuned for updates. 


# Current Features


**Website view tracking:** when a unique visitor (with a per-IP cooldown of 30 minutes) accesses the Flask Project website, the visit number, geolocation, and timestamp are recorded in a PostgreSQL table (via SQLAlchemy). Data for each visit is viewable on the Page Views portal. Geolocation from Maxmind free GeoLite2 databases, for download permalink create an account [here](https://www.maxmind.com/en/geolite2/signup)

![Website Views](https://i.imgur.com/p7efU9Y.png "Website Views")

**Spotify playlist statistics:** Spotify playlist statistics page where a user can log in to see a list of their playlists. Clicking a playlist displays the average track length, track popularity, and percentage of explicit tracks of the playlist. Also displays averages of Spotify audio features such as danceability and energy (see [here](https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/)). Uses the [Spotify Web API](https://developer.spotify.com/documentation/web-api/) and [Spotipy API Wrapper](https://spotipy.readthedocs.io/en/latest/)

![Spotify Playlist Stats](https://i.imgur.com/1KCOecm.png "Spotify Playlist Stats")

# Usage:

Create a file named secrets.py at the root of the project folder (alongside app.py) containing the following lines:

```
DATABASE_URL="postgresql://db_username:db_password@ip_address/db_name"
APP_SETTINGS="config.{TestingConfig|DevelopmentConfig|StagingConfig|ProductionConfig}"
SECRET_KEY="Your Secret Key Here" (set a key unique to you)
SPOTIFY_CLIENT_ID="Your Spotify API Client ID Here"
SPOTIFY_CLIENT_SECRET="Your Spotify API Client Secret Here"
GEOIP2_DB_PERMALINK="Permalink to Maxmind's GeoIP2 DB (requires license)"
SPOTIFY_REDIRECT_URI="Redirect Callback Link as Configured in your Spotify API Dashboard"
```

Install Dependencies:

```
pip3 install -r requirements.txt
```

Run Server:

```
python3 app.py
```
