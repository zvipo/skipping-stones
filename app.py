from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import requests
import os
from dotenv import load_dotenv
from datetime import datetime
import jwt
import json

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Google OIDC configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/callback')

# Google OIDC endpoints
GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://oauth2.googleapis.com/token'
GOOGLE_JWKS_ENDPOINT = 'https://www.googleapis.com/oauth2/v3/certs'

# Cache for Google's public keys
google_public_keys = None

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Simple in-memory user database (in production, use a real database)
users_db = {}

# Simple user class for Flask-Login
class User(UserMixin):
    def __init__(self, user_id, email, name, picture, created_at=None, is_new_user=False):
        self.id = user_id
        self.email = email
        self.name = name
        self.picture = picture
        self.created_at = created_at or datetime.now()
        self.is_new_user = is_new_user

@login_manager.user_loader
def load_user(user_id):
    # Load user from our simple database
    if user_id in users_db:
        user_data = users_db[user_id]
        return User(
            user_data['id'], 
            user_data['email'], 
            user_data['name'], 
            user_data['picture'],
            user_data.get('created_at'),
            user_data.get('is_new_user', False)
        )
    return None

def get_google_public_keys():
    """Fetch Google's public keys for JWT verification"""
    global google_public_keys
    if google_public_keys is None:
        response = requests.get(GOOGLE_JWKS_ENDPOINT)
        if response.status_code == 200:
            google_public_keys = response.json()
        else:
            raise Exception("Failed to fetch Google public keys")
    return google_public_keys

def verify_google_id_token(id_token):
    """Verify Google ID token using Google's public keys"""
    try:
        print(f"Starting token verification...")
        print(f"Client ID: {GOOGLE_CLIENT_ID}")
        print(f"Token length: {len(id_token)}")
        
        # Decode the JWT header to get the key ID
        header = jwt.get_unverified_header(id_token)
        kid = header.get('kid')
        
        if not kid:
            print("Error: No key ID in token header")
            print(f"Header: {header}")
            return None
        
        print(f"Token key ID: {kid}")
        
        # Get Google's public keys
        keys = get_google_public_keys()
        print(f"Available keys: {[key.get('kid') for key in keys['keys']]}")
        
        # Find the correct public key
        public_key = None
        for key in keys['keys']:
            if key['kid'] == kid:
                try:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key))
                    print(f"Found matching public key for kid: {kid}")
                    break
                except Exception as e:
                    print(f"Error creating public key from JWK: {e}")
                    continue
        
        if not public_key:
            print(f"Error: No matching public key found for kid: {kid}")
            return None
        
        # Verify and decode the token
        print("Attempting to decode token...")
        decoded = jwt.decode(
            id_token,
            public_key,
            algorithms=['RS256'],
            audience=GOOGLE_CLIENT_ID,
            issuer='https://accounts.google.com'
        )
        
        print(f"Token verified successfully for user: {decoded.get('email', 'unknown')}")
        print(f"Token claims: {list(decoded.keys())}")
        return decoded
    except jwt.ExpiredSignatureError:
        print("Error: Token has expired")
        return None
    except jwt.InvalidAudienceError:
        print(f"Error: Invalid audience. Expected: {GOOGLE_CLIENT_ID}")
        print(f"Token audience: {jwt.get_unverified_header(id_token)}")
        return None
    except jwt.InvalidIssuerError:
        print("Error: Invalid issuer. Expected: https://accounts.google.com")
        return None
    except jwt.InvalidSignatureError:
        print("Error: Invalid token signature")
        return None
    except Exception as e:
        print(f"Token verification failed: {e}")
        print(f"Exception type: {type(e)}")
        return None

@app.route('/')
def index():
    return redirect(url_for('skipping_stones'))

@app.route('/login')
def login():
    if not GOOGLE_CLIENT_ID:
        flash('Google OIDC is not configured. Please set GOOGLE_CLIENT_ID environment variable.', 'warning')
        return redirect(url_for('skipping_stones'))
    
    # Generate Google OIDC URL for authentication
    google_auth_url = (
        f'{GOOGLE_AUTH_ENDPOINT}?'
        'response_type=code&'
        f'client_id={GOOGLE_CLIENT_ID}&'
        f'redirect_uri={GOOGLE_REDIRECT_URI}&'
        'scope=openid%20email%20profile&'
        'access_type=offline&'
        'prompt=select_account'
    )
    return redirect(google_auth_url)

@app.route('/callback')
def callback():
    print(f"Callback received. Request URL: {request.url}")
    print(f"Redirect URI configured: {GOOGLE_REDIRECT_URI}")
    
    code = request.args.get('code')
    
    if not code:
        print("Error: No authorization code received")
        flash('Authorization failed', 'error')
        return redirect(url_for('skipping_stones'))
    
    print(f"Authorization code received: {code[:10]}...")
    
    # Exchange authorization code for access token and ID token
    token_url = GOOGLE_TOKEN_ENDPOINT
    token_data = {
        'client_id': GOOGLE_CLIENT_ID,
        'client_secret': GOOGLE_CLIENT_SECRET,
        'code': code,
        'grant_type': 'authorization_code',
        'redirect_uri': GOOGLE_REDIRECT_URI
    }
    
    response = requests.post(token_url, data=token_data)
    if response.status_code != 200:
        print("Error: Failed to get tokens")
        print(f"Token response keys: {list(response.json().keys())}")
        flash('Failed to get tokens', 'error')
        return redirect(url_for('skipping_stones'))
    
    token_info = response.json()
    id_token = token_info.get('id_token')
    
    if not id_token:
        print("Error: No ID token in response")
        print(f"Token response keys: {list(token_info.keys())}")
        flash('No ID token received', 'error')
        return redirect(url_for('skipping_stones'))
    
    print(f"Received ID token length: {len(id_token)}")
    
    # Verify the ID token
    user_info = verify_google_id_token(id_token)
    if not user_info:
        print("Error: ID token verification failed")
        flash('Invalid ID token - JWT verification failed', 'error')
        return redirect(url_for('skipping_stones'))
    
    print(f"All OIDC claims: {list(user_info.keys())}")
    
    # Extract user information from ID token
    user_id = user_info.get('sub')  # OIDC standard claim for user ID
    email = user_info.get('email', '')
    name = user_info.get('name', '')
    picture = user_info.get('picture', '')
    
    # Check for alternative picture field names
    if not picture:
        picture = user_info.get('picture_url', '')
    if not picture:
        picture = user_info.get('avatar', '')
    if not picture:
        picture = user_info.get('avatar_url', '')
    
    print(f"User info from OIDC: ID={user_id}, Email={email}, Name={name}, Picture={picture}")
    print(f"Picture field check: picture='{user_info.get('picture', '')}', picture_url='{user_info.get('picture_url', '')}', avatar='{user_info.get('avatar', '')}'")
    
    # If no picture in ID token, try userinfo endpoint as fallback
    if not picture and token_info.get('access_token'):
        print("No picture in ID token, trying userinfo endpoint...")
        try:
            userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {token_info["access_token"]}'}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            
            if userinfo_response.status_code == 200:
                userinfo_data = userinfo_response.json()
                picture = userinfo_data.get('picture', picture)  # Use userinfo picture if available
                print(f"Userinfo picture: {picture}")
            else:
                print(f"Userinfo endpoint failed: {userinfo_response.status_code}")
        except Exception as e:
            print(f"Error fetching userinfo: {e}")
    
    if not user_id:
        print(f"Error: No 'sub' claim found in user_info: {list(user_info.keys())}")
        flash('Invalid user information - missing user ID', 'error')
        return redirect(url_for('skipping_stones'))
    
    # Check if user exists in our database
    is_new_user = user_id not in users_db
    
    if is_new_user:
        # Create new user record
        users_db[user_id] = {
            'id': user_id,
            'email': email,
            'name': name,
            'picture': picture,
            'created_at': datetime.now(),
            'is_new_user': True
        }
        flash('Welcome! Your account has been created successfully.', 'success')
    else:
        # Update existing user's information
        users_db[user_id].update({
            'name': name,
            'picture': picture,
            'is_new_user': False
        })
        flash('Welcome back!', 'success')
    
    # Create user object
    user = User(
        user_id=user_id,
        email=email,
        name=name,
        picture=picture,
        created_at=users_db[user_id]['created_at'],
        is_new_user=is_new_user
    )
    
    # Store user data in session
    session['user_data'] = {
        'id': user.id,
        'email': user.email,
        'name': user.name,
        'picture': user.picture,
        'created_at': user.created_at.isoformat(),
        'is_new_user': user.is_new_user
    }
    
    login_user(user)
    
    return redirect(url_for('skipping_stones'))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('skipping_stones'))

@app.route('/switch-account')
def switch_account():
    # Clear current session
    session.clear()
    logout_user()
    # Redirect to login with account selection
    return redirect(url_for('login'))

@app.route('/skipping-stones')
def skipping_stones():
    return render_template('skipping_stones.html')

@app.route('/api/skipping-stones/configs')
def get_game_configs():
    """Return the 7 classic configurations for the skipping stones game"""
    configs = {
        'level1': {
            'name': 'Level 1',
            'description': 'Cross',
            'marbles': [
                (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
                (2, 4), (3, 4), (5, 4), (6, 4)
            ]
        },
        'level2': {
            'name': 'Level 2',
            'description': 'Small triangle',
            'marbles': [
                (2, 4),
                (3, 3), (3, 4), (3, 5),
                (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
                (5 ,1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7)
            ]
        },
        'level3': {
            'name': 'Level 3',
            'description': 'Arrow',
            'marbles': [
                (1, 4),
                (2, 3), (2, 4), (2, 5),
                (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
                (4, 4),
                (5, 4),
                (6, 3), (6, 4), (6, 5),
                (7, 3), (7, 4), (7, 5)
            ]
        },
        'level4': {
            'name': 'Level 4',
            'description': 'Diamond',
            'marbles': [
                (1, 4),
                (2, 3), (2, 4), (2,5),
                (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
                (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7),
                (5, 2), (5, 3), (5, 4), (5, 5), (5, 6),
                (6, 3), (6, 4), (6, 5),
                (7, 4)
            ]
        },
        'level5': {
            'name': 'Level 5',
            'description': 'Big triangle',
            'marbles': [
                (1, 4),
                (2, 3), (2, 4), (2, 5),
                (3, 2), (3, 3), (3, 4), (3, 5), (3, 6),
                (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6), (4, 7),
                (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8)
            ]
        },
        'level6': {
            'name': 'Level 6',
            'description': 'Small square',
            'marbles': [
                (1, 3), (1, 4), (1, 5),
                (2, 3), (2, 4), (2, 5),
                (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7),
                (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7),
                (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7),
                (6, 3), (6, 4), (6, 5),
                (7, 3), (7, 4), (7, 5)
            ]
        },
        'level7': {
            'name': 'Level 7',
            'description': 'Full board',
            'marbles': [
                (0, 3), (0, 4), (0, 5),
                (1, 3), (1, 4), (1, 5),
                (2, 3), (2, 4), (2, 5),
                (3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7), (3, 8),
                (4, 0), (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7), (4, 8),
                (5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8),
                (6, 3), (6, 4), (6, 5),
                (7, 3), (7, 4), (7, 5),
                (8, 3), (8, 4), (8, 5)
            ]
        }
    }
    return configs

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
