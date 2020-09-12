#Flask Project
import os
from collections import defaultdict
from flask import Flask
from flask import render_template
from flask import request
from flask import flash
from flask import redirect
from flask import url_for
from flask import session
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime
from datetime import timedelta

# Python file containing credentials
import secrets

# matching IP address to location
import geoip2.database

# spotify API wrapper
import spotipy
# from spotipy.oauth2 import SpotifyClientCredentials

# tarfile extraction (for GeoLite database)
import tarfile

# file downloader (for GeoLite database)
import urllib.request

# initialize GeoLite database to empty object
geoip_reader = None

application = Flask(__name__)
application.config.from_object(secrets.APP_SETTINGS)
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(application)

from models import *


@application.before_first_request
def before_first_request():
    '''
    Download, extract, and initialize GeoLite database for matching IP addresses
    and location, this is run on server start (before first request).
    '''

    global geoip_reader

    urllib.request.urlretrieve(secrets.GEOIP2_DB_PERMALINK, "GeoLite2-City.tar.gz")

    tar = tarfile.open("GeoLite2-City.tar.gz", "r")

    # extract only the .mmdb GeoLite database from the .tar.gz into geoipDB folder
    names = tar.getnames()

    name = [i for i in names if i.endswith(".mmdb")][0]

    member = tar.getmember(name)
    member.name = "geoipDB/GeoLite2-City.mmdb"

    tar.extract(member)

    tar.close()

    # delete tar when done with extraction
    if os.path.exists("GeoLite2-City.tar.gz"):
        os.remove("GeoLite2-City.tar.gz")

    geoip_reader = geoip2.database.Reader('./geoipDB/GeoLite2-City.mmdb')


@application.before_request
def before_request():
    '''
    Tracks website visits (accesses from unique IPs with a cooldown of 30 minutes)
    by placing their view number, IP address, location, and timestamp into a PSQL table
    '''

    global geoip_reader

    # retrieve client IP (through SSL proxy if necessary)
    if request.headers.getlist("X-Forwarded-For"):
        client_IP = request.headers.getlist("X-Forwarded-For")[0]
    else:
        client_IP = request.remote_addr

    location = ''

    try:
        latest_access = db.session.query(PageViews).filter_by(ip_address=client_IP).order_by(PageViews.time_stamp.desc()).first()
    except SQLAlchemy.exc:
        print("DB connection failed. Skipping visit tracking.")
        return


    # if this IP address has never visited the home page before, or if it has been 30 min since its last visit...
    if not latest_access or latest_access.time_stamp < datetime.utcnow()-timedelta(minutes=30):

        # gather location results based on client's IP address
        try:
            geoip_results = geoip_reader.city(str(client_IP))
            country_name = geoip_results.country.name if geoip_results.country.name else "Unknown"
            area_name = geoip_results.subdivisions.most_specific.name if geoip_results.subdivisions.most_specific.name else "Unknown"
            city_name = geoip_results.city.name if geoip_results.city.name else "Unknown"
            location = '{}, {}, {}'.format(city_name, area_name, country_name)

        # if client's IP address is not in the GeoLite2 database fill in location value
        except(geoip2.errors.AddressNotFoundError):
            if client_IP == '127.0.0.1':
                location = 'Localhost'
            elif client_IP.startswith('192.168') or client_IP.startswith('10.'):
                location = 'Local Network'
            else:
                location = 'Unknown'

        # if the Maxminddb reader returns corrupt data
        except(maxminddb.errors.InvalidDatabaseError):
            location = 'Unknown'
            print("Maxminddb reader encountered an error, data section corrupt.")


        newPageView = PageViews(ip_address=client_IP, location=location,
                                time_stamp = datetime.utcnow())


        db.session.add(newPageView)
        db.session.commit()


@application.route('/', methods=['GET'])
def home_page():
    '''
    Home page for Flask Project, displays a welcome message
    '''

    return render_template('index.html')


@application.route('/page_views', methods=['GET'])
def page_views():
    '''
    Displays the view number, location, and timestamp of every web page view
    using the databases jquery plug-in with Bootstrap4 theming
    '''
    all_page_views = db.session.query(PageViews).all()

    # retrieve client IP (through proxy if necessary)
    if request.headers.getlist('X-Forwarded-For'):
        client_IP = request.headers.getlist('X-Forwarded-For')[0]
    else:
        client_IP = request.remote_addr

    return render_template('page_views.html', all_page_views=all_page_views, client_IP=client_IP)



@application.route('/playlist_info', methods=['GET', 'POST'])
def playlist_info():
    '''
    After logging in to Spotify via oauth2 and selecting a playlist, display stats about it.
    Displayed stats:
    Average track length
    Average track popularity (percentage)
    Average track release year
    Number of explicit tracks (and percentage)
    '''

    scopes = "user-library-read playlist-read-private"

    sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id=secrets.SPOTIFY_CLIENT_ID, client_secret=secrets.SPOTIFY_CLIENT_SECRET, redirect_uri=secrets.SPOTIFY_REDIRECT_URI, scope=scopes, cache_path=None)

    access_token = ""
    auth_url = ""

    url = request.url
    code = sp_oauth.parse_response_code(url)

    # TODO: solidify response code check logic
    if '?logout=true' in url:
        session.clear()
        return redirect(url_for('playlist_info'))


    if 'token_info' in session and not sp_oauth.is_token_expired(session['token_info']):
        print ("Found valid token from session")
        access_token = session['token_info']['access_token']

    else:
        auth_url = sp_oauth.get_authorize_url()

        # TODO: solidify response code check logic
        # if url contains a callback response code
        if '?code=' in url:
            print("Requesting oauth token")
            try:
                token_info = sp_oauth.get_access_token(code,check_cache=False)
                session['token_info'] = token_info
                print("Successfully received oauth token")
            except spotipy.oauth2.SpotifyOauthError:
                flash('Invalid/expired authorization code received, please attempt sign in again', 'danger')
                print("Error in receiving oauth token")
                return redirect(url_for('playlist_info'))

            return redirect(url_for('playlist_info'))


    user_info = dict()

    user_playlists = []

    playlist_stats = dict()


    if access_token:
        sp = spotipy.Spotify(access_token)
        current_user = sp.current_user()
        print(f'Logged in {current_user["id"]} : {current_user["display_name"]}')
        username = current_user['id']

        # if a playlist is selected, generate and push statistics
        if 'playlist_selection' in request.form:
            selected_playlist = request.form['playlist_selection']

            # gather information on the selected playlist, only request fields we need
            user_playlist = sp.user_playlist(username, selected_playlist,
                                                  fields='tracks.items(track(id, duration_ms, \
                                                  explicit, popularity, album(release_date))), \
                                                  tracks(total, next), images, name')


            # audio feature documentation:
            # https://developer.spotify.com/documentation/web-api/reference/tracks/get-audio-features/
            playlist_stats = {'avg_track_length': 0.0, 'num_explicit': 0,
                              'avg_popularity': 0.0, 'release_year_freqs': defaultdict(int),
                              'num_tracks': user_playlist['tracks']['total'], 'name': user_playlist['name'],
                              'cover_image': user_playlist['images'][0]['url'], 'avg_release_year': 0, 'avg_modality': 0.0,
                              'avg_acousticness': 0.0, 'avg_danceability': 0.0, 'avg_energy': 0.0, 'avg_instrumentalness': 0.0,
                              'avg_liveness': 0.0, 'avg_loudness': 0.0, 'avg_speechiness': 0.0, 'avg_valence': 0.0, 'avg_tempo': 0.0, }
            total_track_lengths = 0
            total_track_popularities = 0

            track_ids = []
            audio_features = []

            counter = 1

            # Spotify API only returns 100 songs at a time, check for the presence
            # of more tracks after processing current batch and continue until complete
            while True:
                for item in user_playlist['tracks']['items']:

                    total_track_lengths += item['track']['duration_ms']

                    if item['track']['explicit']:
                        playlist_stats['num_explicit'] += 1

                    total_track_popularities += item['track']['popularity']

                    if item['track']['album']['release_date']:
                        release_year = item['track']['album']['release_date'].split('-')[0]
                        playlist_stats['release_year_freqs'][release_year] += 1

                    # collect track ids for use by audio features API call
                    if item['track']['id'] is not None:
                        track_ids.append(item['track']['id'])

                    # print(f'Track processed: {counter} length: {item["track"]["duration_ms"] / 60000}')

                    counter += 1

                audio_features.extend(sp.audio_features(track_ids[:100]))
                track_ids = []

                if user_playlist['tracks']['next']:
                    user_playlist['tracks'] = sp.next(user_playlist['tracks'])
                else:
                    break


            num_audio_features = len(audio_features)

            print(f'Tracks processed: {counter}')
            print(f'Audio features processed: {num_audio_features}')

            # calculate and store averages for the following fields
            num_tracks = playlist_stats['num_tracks']

            playlist_stats['avg_track_length'] = total_track_lengths / num_tracks
            playlist_stats['avg_popularity'] = total_track_popularities / num_tracks

            # given the release_year_freqs dictonary, calculates the rounded average release year across all tracks with a release date
            try:
                playlist_stats['avg_release_year'] = round(sum((int(year) * freq for year, freq in playlist_stats['release_year_freqs'].items())) / sum(playlist_stats['release_year_freqs'].values()))
            except(ZeroDivisionError):
                playlist_stats['avg_release_year'] = "N/A"


            # process audio features into averages
            for track in audio_features:
                if track:
                    playlist_stats['avg_modality'] += track['mode']
                    playlist_stats['avg_acousticness'] += track['acousticness']
                    playlist_stats['avg_danceability'] += track['danceability']
                    playlist_stats['avg_energy'] += track['energy']
                    playlist_stats['avg_instrumentalness'] += track['instrumentalness']
                    playlist_stats['avg_liveness'] += track['liveness']
                    playlist_stats['avg_loudness'] += track['loudness']
                    playlist_stats['avg_speechiness'] += track['speechiness']
                    playlist_stats['avg_valence'] += track['valence']
                    playlist_stats['avg_tempo'] += track['tempo']


            audio_feature_avgs = ('avg_modality', 'avg_acousticness', 'avg_danceability', 'avg_energy', 'avg_instrumentalness',
                                  'avg_liveness', 'avg_loudness', 'avg_speechiness', 'avg_valence', 'avg_tempo')

            for avg in audio_feature_avgs:
                playlist_stats[avg] = playlist_stats[avg] / num_audio_features

        try:
            user_info = sp.user(username)
            # TODO: playlist image length check is hack atm
            for playlist in sp.current_user_playlists(offset=0,limit=50)['items']:
                if playlist['tracks']['total'] > 0 and len(playlist['images']) > 0:
                    user_playlists.append({'cover_image': playlist['images'][0]['url'], 'name': playlist['name'], 'id': playlist['id']})


        except(spotipy.client.SpotifyException):
            flash('No Spotify users found for "{}"'.format(username), 'danger')


    return render_template('playlist_info.html', user_info=user_info,
                                       user_playlists=user_playlists,
                                       playlist_stats=playlist_stats, auth_url=auth_url, access_token=access_token)


@application.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


# uncomment below to run app.py locally without WSGI engine
if __name__ == '__main__':
    application.run(host='0.0.0.0', port=5000, debug=True)
