#Flask Project
import os
from flask import Flask
from flask import render_template
from flask import request
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime
from datetime import timedelta

import geoip2.database

# initialize GeoLite database for matching IP addresses and location
geoip_reader = geoip2.database.Reader('./geoipDB/GeoLite2-City.mmdb')


app = Flask(__name__)
app.config.from_object(os.environ['APP_SETTINGS'])
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

from models import *


@app.before_request
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
    if not latest_access or latest_access.time_stamp < datetime.now()-timedelta(minutes=30):

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
                                time_stamp = datetime.now())


        db.session.add(newPageView)
        db.session.commit()


@app.route('/', methods=['GET'])
def home_page():
    '''
    Home page for Flask Project, displays a welcome message
    '''

    return render_template('index.html')


@app.route('/page_views', methods=['GET'])
def page_views():
    '''
    Displays the view number, location, and timestamp of every web page view
    using the databases jquery plug-in with Bootstrap4 theming
    '''
    all_page_views = db.session.query(PageViews).all()

    client_IP = request.remote_addr

    return render_template('page_views.html', all_page_views=all_page_views, client_IP=client_IP)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('page_not_found.html'), 404


if __name__ == '__main__':
    # listening for incoming network connections
    app.run(host='0.0.0.0')
