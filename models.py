from app import db


class PageViews(db.Model):
    __tablename__ = 'PageViews'

    view_num = db.Column(db.Integer, primary_key=True, autoincrement=True)
    ip_address = db.Column(db.String(), index=True)
    location = db.Column(db.String())
    time_stamp = db.Column(db.DateTime)

    def __init__(self, ip_address, location, time_stamp):
        self.ip_address = ip_address
        self.location = location
        self.time_stamp = time_stamp

    def __repr__(self):
        return '<View #{} from {} [{}] at {}>'.format(self.view_num, self.location,
                                                self.ip_address, self.time_stamp)

db.create_all()
