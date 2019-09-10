# Flask Project
In-Progress project utilizing Python3, Flask, Bootstrap4, Datatables, and PostgreSQL.
Stay tuned for updates. 


# Current Features

**Website view tracking:** when a unique visitor (with a per-IP cooldown of 30 minutes) accesses the Flask Project website, the visit number, IP address, geolocation, and timestamp are recorded in a PostgreSQL table. Data for each visit (not including the IP address) is viewable on the Page Views portal.

# Usage:

Set the following environment variables before starting the server:

```
export DATABASE_URL="postgresql://db_username:db_password@localhost/db_name"
export APP_SETTINGS="config.{TestingConfig|DevelopmentConfig|StagingConfig|ProductionConfig}"
export SECRET_KEY="your secret key here"
```

Install dependencies:

```
pip3 install -r requirements.txt
```

Run Server:

```
python3 app.py
```
