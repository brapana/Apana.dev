#Flask Project
import os
from collections import defaultdict
from flask import Flask
from flask import render_template
from flask import request
from flask import flash
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime
from datetime import timedelta

# Python file containing credentials
import secrets


# matching IP address to location
import geoip2.database

# spotify API wrapper
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials


# initialize GeoLite database for matching IP addresses and location
geoip_reader = geoip2.database.Reader('./geoipDB/GeoLite2-City.mmdb')


# initialize Spotify API wrapper
client_credentials_manager = SpotifyClientCredentials(client_id=secrets.SPOTIFY_CLIENT_ID,client_secret=secrets.SPOTIFY_CLIENT_SECRET)
spotify = spotipy.Spotify(client_credentials_manager=client_credentials_manager)


application = Flask(__name__)
application.config.from_object(secrets.APP_SETTINGS)
application.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(application)

from models import *


@application.before_request
def before_request():
    '''
    Tracks website visits (accesses from unique IPs with a cooldown of 30 minutes)
    by placing their view number, IP address, location, and timestamp into a PSQL table
    '''

    global geoip_reader

    client_IP = request.remote_addr

    location = ''

    latest_access = db.session.query(PageViews).filter_by(ip_address=client_IP).order_by(PageViews.time_stamp.desc()).first()


    # if this IP address has never visited the home page before, or if it has been 30 min since its last visit...
    if not latest_access or latest_access.time_stamp < datetime.utcnow()-timedelta(minutes=30):

        # gather location results based on client's IP address
        try:
            geoip_results = geoip_reader.city(client_IP)
            country_name = geoip_results.country.name
            area_name = geoip_results.subdivisions.most_specific.name
            city_name = geoip_results.city.name
            location = '{}, {}, {}'.format(city_name, area_name, country_name)

        # if client's IP address is not in the GeoLite2 database fill in location value
        except(geoip2.errors.AddressNotFoundError):
            if client_IP == '127.0.0.1':
                location = 'Localhost'
            elif client_IP.startswith('192.168') or client_IP.startswith('10.'):
                location = 'Local Network'
            else:
                location = 'Unknown'


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

    client_IP = request.remote_addr

    return render_template('page_views.html', all_page_views=all_page_views, client_IP=client_IP)


@application.route('/album_art/<query>', methods=['GET', 'POST'])
def get_album_art(query):
    '''
    Given a search query, returns a downloadable album art image from Spotify.
    '''

    global spotify

    results = spotify.search(q=query,offset=0,limit=1,type='album')

    album_art=None


    if len(results['albums']['items']) > 0:
        if len(results['albums']['items'][0]['images']) > 0:
            album_art = results['albums']['items'][0]['images'][0]['url']


    return render_template('get_album_art.html', album_art=album_art)


@application.route('/playlist_info', methods=['GET', 'POST'])
def playlist_info():
    '''
    Given a Spotify username and selecting a playlist, display stats about it.
    '''

    global spotify


    user_info = dict()

    user_playlists = []

    playlist_stats = dict()


    if request.method == 'POST':
        username = request.form['username']

        # if a playlist is selected, generate and push statistics
        if 'playlist_selection' in request.form:
            selected_playlist = request.form['playlist_selection']


            # gather information on the selected playlist, only request fields we need
            user_playlist = spotify.user_playlist(username, selected_playlist,
                                                  fields='tracks.items(track(duration_ms, \
                                                  explicit, popularity, album(release_date))), \
                                                  tracks(total, next), images, name')



            print(selected_playlist)




            playlist_stats = {'avg_track_length': 0.0, 'num_explicit': 0,
                              'avg_popularity': 0.0, 'release_year_freqs': defaultdict(int),
                              'num_tracks': user_playlist['tracks']['total'], 'name': user_playlist['name'],
                              'cover_image': user_playlist['images'][0]['url'], 'avg_release_year': 0}
            total_track_lengths = 0
            total_track_popularities = 0


            counter = 1


            # Spotify API only returns 100 songs at a time, check for the presence
            # of more tracks after processing current batch and continue until complete
            while True:
                for item in user_playlist['tracks']['items']:

                    if item['track']['explicit']:
                        playlist_stats['num_explicit'] += 1

                    total_track_lengths += item['track']['duration_ms']

                    total_track_popularities += item['track']['popularity']

                    if item['track']['album']['release_date']:
                        release_year = item['track']['album']['release_date'].split('-')[0]

                        playlist_stats['release_year_freqs'][release_year] += 1


                    print(f'Track processed: {counter} length: {item["track"]["duration_ms"] / 60000}')
                    counter += 1


                if user_playlist['tracks']['next']:
                    user_playlist['tracks'] = spotify.next(user_playlist['tracks'])
                else:
                    break

            # calculate and store averages for the following fields
            num_tracks = playlist_stats['num_tracks']

            playlist_stats['avg_track_length'] = total_track_lengths / num_tracks
            playlist_stats['avg_popularity'] = total_track_popularities / num_tracks

            # given the release_year_freqs dictonary, calculates the rounded average release year across all tracks with a release date
            playlist_stats['avg_release_year'] = round(sum((int(year) * freq for year, freq in playlist_stats['release_year_freqs'].items())) / sum(playlist_stats['release_year_freqs'].values()))


        try:
            user_info = spotify.user(username)

            for playlist in spotify.user_playlists(username,offset=0,limit=50)['items']:
                if playlist['tracks']['total'] > 0:
                    user_playlists.append({'cover_image': playlist['images'][0]['url'], 'name': playlist['name'], 'id': playlist['id']})


        except(spotipy.client.SpotifyException):
            flash('No Spotify users found for "{}"'.format(username), 'danger')






    return render_template('playlist_info.html', user_info=user_info,
                                       user_playlists=user_playlists,
                                       playlist_stats=playlist_stats)


@application.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


#if __name__ == '__main__':
#    application.run(host='0.0.0.0', port=80)
