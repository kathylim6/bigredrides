from db import db, Users

def get_user_by_username(username):
    return Users.query.filter(Users.username == username).first()

def get_user_by_session_token(session_token):
    return Users.query.filter(Users.session_token == session_token).first()

def get_user_by_refresh_token(refresh_token):
    return Users.query.filter(Users.refresh_token == refresh_token).first()

def verify_credentials(username, password):
    possible_user = get_user_by_username(username)

    if possible_user is None:
        return False, None
    
    return possible_user.verify_password(password), possible_user

def create_user(name, username, password):
    possible_user = get_user_by_username(username)
    if possible_user is not None:
        return False, possible_user
    
    user = Users(name=name, username=username, password=password)
    db.session.add(user)
    db.session.commit()
    return True, user

def renew_session(refresh_token):
    possible_user = get_user_by_refresh_token(refresh_token)
    if possible_user is None:
        raise Exception("Invalid refresh token")
    possible_user.renew_session()
    db.session.commit()
    return possible_user