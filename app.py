import json
from db import db
from flask import Flask, request
from db import Trips, Users, Ratings
import users_dao
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy import distance 
from geopy.distance import geodesic

geolocator = Nominatim(user_agent = "BigRedRide")
app = Flask(__name__)
db_filename = "hack_challenge.db"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ECHO"] = True

CORNELL_COORDS = (42.4534, -76.475266)

db.init_app(app)
with app.app_context():
    db.create_all()

def extract_token(request):
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return False, json.dumps({"error":"Missing Authorization header"}), 400
    
    bearer_token = auth_header.replace("Bearer","").strip()
    if not bearer_token:
        return False, json.dumps({"error":"Invalid Authorization header"}), 400
    return True, bearer_token


def success_response(data, code=200):
    return json.dumps(data), code

def failure_response(message, code=404):
    return json.dumps({"error": message}), code

#session routes

@app.route("/register/", methods=["POST"])
def register_account():
    body = json.loads(request.data)
    name = body.get("name")
    username = body.get("username")
    password = body.get("password")

    if name is None or username is None or password is None:
        return json.dumps({"error":"Invalid body"}), 400
    
    created, user = users_dao.create_user(name, username, password)
    if not created:
        return json.dumps({"error":"User already exists"}), 400
    
    return json.dumps({
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "refresh_token": user.refresh_token
    })

@app.route("/login/", methods=["POST"])
def login():
    body = json.loads(request.data)
    username = body.get("username")
    password = body.get("password")

    if username is None or password is None:
        return json.dumps({"error":"Invalid body"}), 400
    
    success, user = users_dao.verify_credentials(username, password)
    if not success:
        return json.dumps({"error":"Invalid credentials"}), 400
    
    user.renew_session()
    db.session.commit()
    return json.dumps({
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "refresh_token": user.refresh_token
    })

@app.route("/logout/", methods=["POST"])
def logout():
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response

    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error":"Invalid session token"}), 400
    user.session_expiration = datetime.now()
    db.session.commit()
    return json.dumps({"message":"You have been logged out"}), 200

@app.route("/session/", methods=["POST"])
def refresh_session():
    success, response = extract_token(request)
    if not success:
        return response
    refresh_token = response

    user = users_dao.renew_session(refresh_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error":"Invalid session token"}), 400
    
    return json.dumps({
        "session_token": user.session_token,
        "session_expiration": str(user.session_expiration),
        "refresh_token": user.refresh_token
    })

# @app.route("/secret/", methods=["GET"])
# def secret_message():
#     success, response = extract_token(request)
#     if not success:
#         return response
#     session_token = response
#     user = users_dao.get_user_by_session_token(session_token)
#     if not user or not user.verify_session_token(session_token):
#         return json.dumps({"error":"Invalid session token"}), 400
# use this beginning for every endpoint that a user must be LOGGED IN FOR (like
# posting a trip)


#all other routes

@app.route("/trips/")
def get_trips():
    """Endpoint for getting all UNCOMPLETED trips"""
    # trips = [t.serialize() for t in Trips.query.all()]
    # return json.dumps({"trips":trips}), 200
    current_date = datetime.now().date()
    trips = []
    for t in Trips.query.all():
        if t.datetime < current_date:
            t.setCompleted()
        else:
            trips.append(t.serialize())

    return json.dumps({"trips":trips}), 200

@app.route("/trips/", methods = ["POST"])
def create_trip():
    """Endpoint to post a trip"""
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error":"Invalid session token"}), 400
    
    body = json.loads(request.data)
    destination = body.get("destination")
    dest = geolocator.geocode(destination)
    dest_long_lat = (dest.latitude, dest.longitude)
    date = datetime.strptime(body.get("date"), '%m-%d-%Y').date()
    driver = body.get("user_id")
    user = Users.query.filter_by(id = driver).first()     
    distance = geodesic(CORNELL_COORDS, dest_long_lat).miles
    gas_price = body.get("gas_price")
    new_trip = Trips(destination = destination, date = date, distance = distance,
                     gas_price = gas_price)
    new_trip.drivers.append(user)
    db.session.add(new_trip)
    db.session.commit()
    return json.dumps(new_trip.serialize()), 201


@app.route("/users/<int:user_id>/")
def get_user(user_id):
    """
    Endpoint for getting a specific user
    """
    user = Users.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    return success_response(user.serialize())


@app.route("/trips/<int:trip_id>/add/",methods=["POST"])
def add_rider(trip_id):
    """
    Endpoint for adding rider to a specific trip
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error":"Invalid session token"}), 400
    
    body = json.loads(request.data)
    user_id = body.get("user_id")
    user = Users.query.filter_by(id=user_id).first()
    if user is None:
        return failure_response("User not found!")
    
    trip = Trips.query.filter_by(id=trip_id).first()
    trip.riders.append(user)
    db.session.add(trip)
    
    db.session.commit()
    return success_response(trip.serialize())


@app.route('/trips/<int:trip_id>/',methods=["DELETE"])
def delete_trip(trip_id):
    """
    Endpoint for deleting a trip
    User deleting a trip must be the driver
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    user = users_dao.get_user_by_session_token(session_token)
    if not user or not user.verify_session_token(session_token):
        return json.dumps({"error":"Invalid session token"}), 400

    body = json.loads(request.data)
    user_id = body.get("user_id")
    user = Users.query.filter_by(id=user_id).first()
    
    trip = Trips.query.filter_by(id=trip_id).first()
    if trip is None:
        return failure_response("Trip not found!")
    if user not in trip.drivers:
        return failure_response("Trip can only be deleted by driver!")
    db.session.delete(trip)
    db.session.commit()
    return success_response(trip.serialize())


@app.route('/users/<int:reviewee_id>/rating/', methods = ["POST"])
def add_rating(reviewee_id):
    """
    Endpoint for creating an anonymous rating for a specific user
    """
    success, response = extract_token(request)
    if not success:
        return response
    session_token = response
    reviewee =  Users.query.filter_by(id=reviewee_id).first()
    if users_dao.get_user_by_session_token(session_token) == reviewee:
        return failure_response('Cannot create self rating',403)
    if reviewee is None:
        return failure_response("User not found!")
    
    body = json.loads(request.data)
    rating_value = body.get("rating")
    review = body.get("review", "")

    if isinstance(int(rating_value),int) == False:
        return failure_response('Rating must be an integer between 1-5!',400)
    if not (0 <= int(rating_value) <=5 ):
        return failure_response('Rating must be an integer between 1-5!',400)
    review = body.get("review", "")

    new_rating = Ratings(
        rating=rating_value,
        review=review,
        user_id=reviewee_id
    )
    
    db.session.add(new_rating)
    db.session.commit()
    
    return json.dumps(new_rating.serialize()), 201




if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)



# import json
# from db import db
# from flask import Flask, request
# from db import Trips, Users, Ratings
# import users_dao
# from datetime import datetime
# from geopy.geocoders import Nominatim
# from geopy import distance 
# from geopy.distance import geodesic

# geolocator = Nominatim(user_agent = "BigRedRide")
# app = Flask(__name__)
# db_filename = "hack_challenge.db"

# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///%s" % db_filename
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# app.config["SQLALCHEMY_ECHO"] = True

# CORNELL_COORDS = (42.4534, -76.475266)

# db.init_app(app)
# with app.app_context():
#     db.create_all()

# def extract_token(request):
#     auth_header = request.headers.get("Authorization")
#     if auth_header is None:
#         return False, json.dumps({"error":"Missing Authorization header"}), 400
    
#     bearer_token = auth_header.replace("Bearer","").strip()
#     if not bearer_token:
#         return False, json.dumps({"error":"Invalid Authorization header"}), 400
#     return True, bearer_token


# def success_response(data, code=200):
#     return json.dumps(data), code

# def failure_response(message, code=404):
#     return json.dumps({"error": message}), code

# #session routes

# @app.route("/register/", methods=["POST"])
# def register_account():
#     body = json.loads(request.data)
#     name = body.get("name")
#     username = body.get("username")
#     password = body.get("password")

#     if name is None or username is None or password is None:
#         return json.dumps({"error":"Invalid body"}), 400
    
#     created, user = users_dao.create_user(name, username, password)
#     if not created:
#         return json.dumps({"error":"User already exists"}), 400
    
#     return json.dumps({
#         "session_token": user.session_token,
#         "session_expiration": str(user.session_expiration),
#         "refresh_token": user.refresh_token
#     })

# @app.route("/login/", methods=["POST"])
# def login():
#     body = json.loads(request.data)
#     username = body.get("username")
#     password = body.get("password")

#     if username is None or password is None:
#         return json.dumps({"error":"Invalid body"}), 400
    
#     success, user = users_dao.verify_credentials(username, password)
#     if not success:
#         return json.dumps({"error":"Invalid credentials"}), 400
    
#     user.renew_session()
#     db.session.commit()
#     return json.dumps({
#         "session_token": user.session_token,
#         "session_expiration": str(user.session_expiration),
#         "refresh_token": user.refresh_token
#     })

# @app.route("/logout/", methods=["POST"])
# def logout():
#     success, response = extract_token(request)
#     if not success:
#         return response
#     session_token = response

#     user = users_dao.get_user_by_session_token(session_token)
#     if not user or not user.verify_session_token(session_token):
#         return json.dumps({"error":"Invalid session token"}), 400
#     user.session_expiration = datetime.now()
#     db.session.commit()
#     return json.dumps({"message":"You have been logged out"}), 200

# @app.route("/session/", methods=["POST"])
# def refresh_session():
#     success, response = extract_token(request)
#     if not success:
#         return response
#     refresh_token = response

#     try:
#         user = users_dao.renew_session(refresh_token)
#     except Exception as e:
#         return json.dumps({"error":"Invalid refresh token"})
    
#     return json.dumps({
#         "session_token": user.session_token,
#         "session_expiration": str(user.session_expiration),
#         "refresh_token": user.refresh_token
#     })

# # @app.route("/secret/", methods=["GET"])
# # def secret_message():
# #     success, response = extract_token(request)
# #     if not success:
# #         return response
# #     session_token = response
# #     user = users_dao.get_user_by_session_token(session_token)
# #     if not user or not user.verify_session_token(session_token):
# #         return json.dumps({"error":"Invalid session token"}), 400
# # use this beginning for every endpoint that a user must be LOGGED IN FOR (like
# # posting a trip)


# #all other routes

# @app.route("/trips/")
# def get_trips():
#     """Endpoint for getting all trips"""
#     current_date = datetime.now().date()
#     trips = []
#     for t in Trips.query.all():
#         if t.datetime > current_date:
#             trips.append(t.serialize())

#     return json.dumps({"trips":trips}), 200

# @app.route("/trips/", methods = ["POST"])
# def create_trip():
#     """Endpoint to post a trip"""
#     success, response = extract_token(request)
#     if not success:
#         return response
#     session_token = response
#     user = users_dao.get_user_by_session_token(session_token)
#     if not user or not user.verify_session_token(session_token):
#         return json.dumps({"error":"Invalid session token"}), 400
    
#     body = json.loads(request.data)
#     destination = body.get("destination")
#     dest = geolocator.geocode(destination)
#     dest_long_lat = (dest.latitude, dest.longitude)
#     date = datetime.strptime(body.get("date"),'%m-%d-%y')
#     driver = body.get("user_id")
#     user = Users.query.filter_by(id = driver).first()     
#     distance = geodesic(CORNELL_COORDS, dest_long_lat).miles
#     gas_price = body.get("gas_price")
#     new_trip = Trips(destination = destination, date = date, distance = distance,
#                      gas_price = gas_price)
#     new_trip.drivers.append(user)
#     db.session.add(new_trip)
#     db.session.commit()
#     return json.dumps(new_trip.serialize()), 201


# @app.route("/users/<int:user_id>/")
# def get_user(user_id):
#     """
#     Endpoint for getting a specific user
#     """
#     user = Users.query.filter_by(id=user_id).first()
#     if user is None:
#         return failure_response("User not found!")
#     return success_response(user.serialize())


# @app.route("/trips/<int:trip_id>/add/",methods=["POST"])
# def add_rider(trip_id):
#     """
#     Endpoint for adding rider to a specific trip
#     """
#     success, response = extract_token(request)
#     if not success:
#         return response
#     session_token = response
#     user = users_dao.get_user_by_session_token(session_token)
#     if not user or not user.verify_session_token(session_token):
#         return json.dumps({"error":"Invalid session token"}), 400
    
#     body = json.loads(request.data)
#     user_id = body.get("user_id")
#     user = Users.query.filter_by(id=user_id).first()
#     if user is None:
#         return failure_response("User not found!")
    
#     trip = Trips.query.filter_by(id=trip_id).first()
#     trip.riders.append(user)
#     db.session.add(trip)
    
#     db.session.commit()
#     return success_response(trip.serialize())


# @app.route('/trips/<int:trip_id>/',methods=["DELETE"])
# def delete_trip(trip_id):
#     """
#     Endpoint for deleting a trip
#     User deleting a trip must be the driver
#     """
#     success, response = extract_token(request)
#     if not success:
#         return response
#     session_token = response
#     user = users_dao.get_user_by_session_token(session_token)
#     if not user or not user.verify_session_token(session_token):
#         return json.dumps({"error":"Invalid session token"}), 400

#     body = json.loads(request.data)
#     user_id = body.get("user_id")
#     user = Users.query.filter_by(id=user_id).first()
    
#     trip = Trips.query.filter_by(id=trip_id).first()
#     if trip is None:
#         return failure_response("Trip not found!")
#     if user not in trip.drivers:
#         return failure_response("Trip can only be deleted by driver!")
#     db.session.delete(trip)
#     db.session.commit()
#     return success_response(trip.serialize())


# @app.route('/users/<int:reviewee_id>/rating/', methods = ["POST"])
# def add_rating(reviewee_id):
#     """
#     Endpoint for creating an anonymous rating for a specific user
#     """
#     success, response = extract_token(request)
#     if not success:
#         return response
#     session_token = response
#     reviewee =  Users.query.filter_by(id=reviewee_id).first()
#     if users_dao.get_user_by_session_token(session_token) == reviewee:
#         return failure_response('Cannot create self rating',403)
#     if reviewee is None:
#         return failure_response("User not found!")
#     body = json.loads(request.data)
#     rating_value = body.get("rating")
#     if isinstance(int(rating_value),int) == False:
#         return failure_response('Rating must be an integer between 1-5!',400)
#     if not (0 <= int(rating_value) <=5 ):
#         return failure_response('Rating must be an integer between 1-5!',400)
#     review = body.get("review", "")

#     new_rating = Ratings(
#         rating=rating_value,
#         review=review,
#         user_id=reviewee_id
#     )
    
#     db.session.add(new_rating)
#     db.session.commit()
    
#     return json.dumps(new_rating.serialize()), 201
    

# if __name__ == "__main__":
#     app.run(host="0.0.0.0", port=8000, debug=True)
