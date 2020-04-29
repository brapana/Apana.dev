# Flask Project
In-progress multi-purpose project utilizing Python3, Flask, Bootstrap4, Datatables, PostgreSQL, and the Spotify API.
Stay tuned for updates. 


# Current Features

**Website view tracking:** when a unique visitor (with a per-IP cooldown of 30 minutes) accesses the Flask Project website, the visit number, IP address, geolocation, and timestamp are recorded in a PostgreSQL table. Data for each visit (not including the IP address) is viewable on the Page Views portal.

**Spotify playlist information:** Spotify playlist info page where a user enters their Spotify username to see a list of their public playlists. Clicking a playlist displays the average track length, track popularity, and percentage of explicit tracks of the playlist. Uses the [Spotify Web API](https://developer.spotify.com/documentation/web-api/) and [Spotipy API Wrapper](https://spotipy.readthedocs.io/en/latest/)

# Usage:

Create a file named secrets.py at the root of the project folder (alongside app.py) containing the following lines:

```
DATABASE_URL="postgresql://db_username:db_password@localhost/db_name"
APP_SETTINGS="config.{TestingConfig|DevelopmentConfig|StagingConfig|ProductionConfig}"
SECRET_KEY="Your Secret Key Here" (set a key unique to you)
SPOTIFY_CLIENT_ID="Your Spotify API Client ID Here"
SPOTIFY_CLIENT_SECRET="Your Spotify API Client Secret Here"
```

Install Dependencies:

```
pip3 install -r requirements.txt
```

Run Server:

```
python3 app.py
```
