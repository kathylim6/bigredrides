import bcrypt
from bcrypt import _bcrypt
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import hashlib
import os

db = SQLAlchemy()

# association tables
drivers_trips = db.Table(
    "drivers_trips",
    db.Model.metadata,
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("trip_id", db.Integer, db.ForeignKey("trips.id"), primary_key=True)
)

riders_trips = db.Table(
    "riders_trips",
    db.Model.metadata,
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("trip_id", db.Integer, db.ForeignKey("trips.id"), primary_key=True)
)


class Trips(db.Model):
    """Trips model
    Has a many-to-many relationship with Users model
    Has a many-to-many relationship with riders
    Has a one-to-many relaionship with drivers"""
    __tablename__ = "trips"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)
    destination = db.Column(db.String, nullable = False)
    date = db.Column(db.Date,nullable=False) 
    drivers = db.relationship("Users", secondary=drivers_trips, back_populates="trips_as_driver")
    riders = db.relationship("Users", secondary=riders_trips, back_populates="trips_as_rider")
    distance = db.Column(db.Integer, nullable = False)
    gas_price = db.Column(db.String, nullable = False) #string because easier for frontend

    def __init__(self, **kwargs):
        """Initializes a trip object"""
        self.destination = kwargs.get("destination", "")
        self.date = kwargs.get("date","")
        self.distance = kwargs.get("distance", 0)
        self.gas_price = kwargs.get("gas_price")


    def serialize(self):
        """Serializes a trip object"""
        return {
            "id": self.id,
            "destination": self.destination,
            "date": self.date.strftime("%m-%d-%Y"), 
            "distance": self.distance,
            "gas_price": self.gas_price,
            "drivers": [d.simple_serialize() for d in self.drivers],
            "riders": [r.simple_serialize() for r in self.riders]
        }
    
    def simple_serialize(self):
        """Serializes a trip object without the passengers"""
        return {
            "id": self.id,
            "destination": self.destination,
            "date": self.date.strftime("%m-%d-%Y"),
            "distance": self.distance,
            "gas_price": self.gas_price
        }


class Users(db.Model):
    """
    User model
    Has a many-to-many relationship with the Trips model
    Has a one-to-many relationship with the Ratings model
    """
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key = True, autoincrement = True)

    #user information
    name = db.Column(db.String, nullable = False)
    username = db.Column(db.String, nullable = False, unique=True)
    balance = db.Column(db.Float, default =0.0, nullable=False )
    password_digest = db.Column(db.String, nullable = False)
    trips_as_driver = db.relationship("Trips", secondary=drivers_trips, back_populates="drivers")
    trips_as_rider = db.relationship("Trips", secondary=riders_trips, back_populates="riders")
    ratings = db.relationship("Ratings", back_populates="user")

    #session information
    session_token = db.Column(db.String, nullable=False, unique=False)
    session_expiration = db.Column(db.DateTime, nullable=False, unique=False)
    refresh_token = db.Column(db.String, nullable=False, unique=False)

    def __init__(self, **kwargs):
        """Initializes a user object"""
        self.name = kwargs.get("name", "")
        self.username = kwargs.get("username", "")
        self.password_digest = bcrypt.hashpw(kwargs.get("password", "").encode("utf8"), bcrypt.gensalt(rounds=13)) #i put bcrypt into requirements
        self.renew_session()
        self.balance = kwargs.get("balance", 0.0)


    def _urlsafe_base_64(self):
        """Used to randomly generate session/refresh tokens"""
        return hashlib.sha1(os.urandom(64)).hexdigest() #import


    def renew_session(self):
        """Generates new tokens, and resets expiration time"""
        self.session_token = self._urlsafe_base_64()
        self.refresh_token = self._urlsafe_base_64()
        self.session_expiration = datetime.now() + timedelta(days=1)


    def verify_password(self, password):
        return bcrypt.checkpw(password.encode("utf8"), self.password_digest)
    

    def verify_session_token(self, session_token):
        """Checks if session token is valid and hasn't expired"""
        return session_token == self.session_token and datetime.now() < self.session_expiration


    def verify_refresh_token(self, refresh_token):
        return refresh_token == self.refresh_token #do we need for this to have an expiration time? demo did not so just asking
    

    def serialize(self):
        """serializes a user object without the password"""
        all_trips = list(set(self.trips_as_driver + self.trips_as_rider))
        
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username,
            "balance": self.balance,
            "trips": [trip.simple_serialize() for trip in all_trips],
            "average_rating": self.average_rating()
        }
    
    def simple_serialize(self):
        """serializes a user object without the trips or password"""
        return {
            "id": self.id,
            "name": self.name,
            "username": self.username
        }
    
    def increase_balance(self, amount):
        """
        Adds money to a user's balance
        """
        self.balance += amount
        db.session.commit()

    def decrease_balance(self,amount):
        """
        Removes money to a user's balance
        """
        self.balance -= amount
        db.session.commit()

    def average_rating(self):
        """
        Returns the average rating of a user
        Returns -1.0 if the user is unrated
        """
        if not self.ratings:
            return -1.0
        
        total_ratings = 0
        for rating in self.ratings:
            total_ratings += rating.rating
        return total_ratings / len(self.ratings)
    
    
class Ratings(db.Model):
    """
    Ratings Model
    Has a one-to-many relationship with the Users model
    """
    __tablename__ = "Ratings"
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rating = db.Column(db.Integer, nullable=False)
    review = db.Column (db.String, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    user = db.relationship("Users", back_populates="ratings")
    # not sure how you could do this where you have a reviewer user and a reviewee user if that makes sense 

    def __init__(self,**kwargs):
        """
        Initialize a ratings object
        """
        self.rating = kwargs.get("rating")
        self.review = kwargs.get("review")
        self.user_id = kwargs.get("user_id")


    def serialize(self):
        """
        Serialize an ratings object
        """
        return {
            "id": self.id,
            "user": self.user.simple_serialize(),
            "rating": self.rating,
            "review": self.review
        }


    def simple_serialize(self):
        """
        Serializes a ratings object without user field
        """
        return {
            "id": self.id,
            "rating": self.rating,
            "review": self.review
        }
