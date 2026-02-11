from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import requests
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
import jwt
import json
from database import db
from solver import get_hint, _board_to_bits
from solver_cache import solver_cache
from functools import wraps
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

# Configure session to be more persistent but with reasonable limits
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # 24 hours instead of 30 days
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Note: Using single worker to avoid session sharing issues between workers

# Initialize database
try:
    db.create_table_if_not_exists()
except Exception as e:
    print(f"Database initialization error: {e}")

# Initialize solver cache
try:
    solver_cache.create_table_if_not_exists()
except Exception as e:
    print(f"Solver cache initialization error: {e}")

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

# Session management
session_activity = {}  # Track session activity for cleanup
request_count = 0  # Track total requests for monitoring

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Security headers middleware
@app.after_request
def add_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; img-src 'self' data: https:; font-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com;"
    return response

# Simple in-memory user database (in production, use a real database)
users_db = {}

# Custom decorator for API endpoints that need authentication
def api_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

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
        # Decode the JWT header to get the key ID
        header = jwt.get_unverified_header(id_token)
        kid = header.get('kid')
        
        if not kid:
            return None
        
        # Get Google's public keys
        keys = get_google_public_keys()
        
        # Find the correct public key
        public_key = None
        for key in keys['keys']:
            if key['kid'] == kid:
                try:
                    # Use cryptography library to create the public key
                    from cryptography.hazmat.primitives.asymmetric import rsa
                    import base64
                    
                    # Extract the key components from JWK
                    n = int.from_bytes(base64.urlsafe_b64decode(key['n'] + '=='), 'big')
                    e = int.from_bytes(base64.urlsafe_b64decode(key['e'] + '=='), 'big')
                    
                    # Create the public key
                    public_numbers = rsa.RSAPublicNumbers(e, n)
                    public_key = public_numbers.public_key()
                    break
                except Exception as e:
                    continue
        
        if not public_key:
            return None
        
        # Verify and decode the token
        decoded = jwt.decode(
            id_token,
            public_key,
            algorithms=['RS256'],
            audience=GOOGLE_CLIENT_ID,
            issuer='https://accounts.google.com'
        )
        
        return decoded
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidAudienceError:
        return None
    except jwt.InvalidIssuerError:
        return None
    except jwt.InvalidSignatureError:
        return None
    except Exception as e:
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
    code = request.args.get('code')
    
    if not code:
        flash('Authorization failed', 'error')
        return redirect(url_for('skipping_stones'))
    
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
        flash('Failed to get tokens', 'error')
        return redirect(url_for('skipping_stones'))
    
    token_info = response.json()
    id_token = token_info.get('id_token')
    
    if not id_token:
        flash('No ID token received', 'error')
        return redirect(url_for('skipping_stones'))
    
    # Verify the ID token
    user_info = verify_google_id_token(id_token)
    if not user_info:
        flash('Invalid ID token - JWT verification failed', 'error')
        return redirect(url_for('skipping_stones'))
    
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
    
    # If no picture in ID token, try userinfo endpoint as fallback
    if not picture and token_info.get('access_token'):
        try:
            userinfo_url = 'https://www.googleapis.com/oauth2/v2/userinfo'
            headers = {'Authorization': f'Bearer {token_info["access_token"]}'}
            userinfo_response = requests.get(userinfo_url, headers=headers)
            
            if userinfo_response.status_code == 200:
                userinfo_data = userinfo_response.json()
                picture = userinfo_data.get('picture', picture)  # Use userinfo picture if available
        except Exception as e:
            pass
    
    if not user_id:
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
    
    # Make session permanent (24 hours)
    session.permanent = True
    
    login_user(user)
    
    return redirect(url_for('skipping_stones'))

@app.route('/logout')
def logout():
    """Logout route that handles both authenticated and unauthenticated users"""
    # Clear the session and logout user
    logout_user()
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('skipping_stones'))



@app.route('/api/auth/logout', methods=['POST'])
def api_logout():
    """API endpoint for logout that can be called from JavaScript"""
    # Clear the session and logout user
    logout_user()
    session.clear()
    return jsonify({'message': 'Logged out successfully'}), 200

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

@app.route('/api/skipping-stones/hint', methods=['POST'])
def get_game_hint():
    data = request.get_json()
    board = data.get('board')  # 9x9 boolean array
    stone_count = sum(1 for row in board for cell in row if cell)

    # Check solver cache first
    bits = _board_to_bits(board)
    try:
        cached = solver_cache.get_solution(bits)
        if cached:
            return jsonify({'hint': cached[0]})
    except Exception:
        pass

    # Cache miss — solve live
    time_limit = 5.0 if stone_count <= 20 else 10.0
    from solver import solve
    solution = solve(board, time_limit=time_limit)
    if solution and len(solution) > 0:
        # Write-through: cache the entire solution path
        try:
            solver_cache.cache_solution_path(bits, solution, stone_count)
        except Exception:
            pass
        return jsonify({'hint': solution[0]})
    return jsonify({'hint': None})

@app.route('/api/game-state/save', methods=['POST'])
@api_login_required
def save_game_state():
    """Save the current game state for the authenticated user"""
    global request_count
    request_count += 1
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Save to database
        success = db.save_game_state(current_user.id, data)
        
        if success:
            # Also save to session for immediate access
            session['current_game_state'] = data
            return jsonify({'message': 'Game state saved successfully'}), 200
        else:
            return jsonify({'error': 'Failed to save game state'}), 500
            
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/game-state/load')
def load_game_state():
    """Load the game state for the authenticated user"""
    try:
        if current_user.is_authenticated:
            game_state = db.load_game_state(current_user.id)
            
            if game_state:
                # Save to session for immediate access
                session['current_game_state'] = game_state
                return jsonify(game_state), 200
            else:
                # Return default state for new users
                default_state = {
                    'current_level': 'level1',
                    'board_state': [],
                    'move_history': [],
                    'marbles_left': 0,
                    'moves_count': 0,
                    'game_status': 'Playing',
                    'completed_levels': []
                }
                session['current_game_state'] = default_state
                return jsonify(default_state), 200
        else:
            # Return default state for non-authenticated users
            default_state = {
                'current_level': 'level1',
                'board_state': [],
                'move_history': [],
                'marbles_left': 0,
                'moves_count': 0,
                'game_status': 'Playing',
                'completed_levels': []
            }
            return jsonify(default_state), 200
            
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/game-state/complete-level', methods=['POST'])
@api_login_required
def complete_level():
    """Mark a level as completed for the authenticated user"""
    try:
        data = request.get_json()
        level = data.get('level')
        
        if not level:
            return jsonify({'error': 'No level specified'}), 400
        
        success = db.mark_level_completed(current_user.id, level)
        
        if success:
            return jsonify({'message': f'Level {level} marked as completed'}), 200
        else:
            return jsonify({'error': 'Failed to mark level as completed'}), 500
            
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/auth/debug-session')
def debug_session():
    """Debug endpoint to check session configuration"""
    return jsonify({
        'session_id': session.get('_id', 'No session ID'),
        'session_permanent': session.permanent,
        'session_modified': session.modified,
        'user_authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'session_lifetime': str(app.config['PERMANENT_SESSION_LIFETIME']),
        'session_cookie_secure': app.config['SESSION_COOKIE_SECURE'],
        'session_cookie_httponly': app.config['SESSION_COOKIE_HTTPONLY'],
        'session_cookie_samesite': app.config['SESSION_COOKIE_SAMESITE']
    }), 200

@app.route('/api/debug/performance')
def debug_performance():
    """Debug endpoint to check performance metrics"""
    global request_count
    return jsonify({
        'total_requests': request_count,
        'active_sessions': len(session_activity),
        'memory_usage_mb': len(users_db) * 0.001,  # Rough estimate
        'worker_info': 'Single worker - handles multiple users efficiently'
    }), 200

@app.route('/api/auth/status')
def auth_status():
    """Check if user is authenticated"""
    global request_count
    request_count += 1
    
    return jsonify({
        'authenticated': current_user.is_authenticated,
        'user_id': current_user.id if current_user.is_authenticated else None,
        'email': current_user.email if current_user.is_authenticated else None,
        'name': current_user.name if current_user.is_authenticated else None
    }), 200

@app.route('/api/auth/refresh-session', methods=['POST'])
def refresh_session():
    """Refresh the user's session to prevent expiration"""
    
    if current_user.is_authenticated:
        # Touch the session to extend its lifetime
        session.modified = True
        
        # Track session activity for cleanup
        session_activity[current_user.id] = datetime.now()
        
        return jsonify({'message': 'Session refreshed successfully'}), 200
    else:
        return jsonify({'error': 'No active session to refresh'}), 401

def cleanup_old_sessions():
    """Clean up old session activity records"""
    cutoff_time = datetime.now() - timedelta(hours=24)
    expired_sessions = [
        user_id for user_id, last_activity in session_activity.items()
        if last_activity < cutoff_time
    ]
    for user_id in expired_sessions:
        del session_activity[user_id]

@app.route('/api/game-state/save-all-levels', methods=['POST'])
@api_login_required
def save_all_levels_state():
    """Save all levels' state for the authenticated user"""
    global request_count
    request_count += 1
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Save to database
        success = db.save_all_levels_state(current_user.id, data)
        
        if success:
            return jsonify({'message': 'All levels state saved successfully'}), 200
        else:
            return jsonify({'error': 'Failed to save all levels state'}), 500
            
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/game-state/load-all-levels')
def load_all_levels_state():
    """Load all levels' state for the authenticated user"""
    try:
        if current_user.is_authenticated:
            print(f"Loading all levels state for user: {current_user.id}")
            all_levels_state = db.load_all_levels_state(current_user.id)
            
            if all_levels_state:
                print(f"Loaded all levels state: {all_levels_state}")
                return jsonify(all_levels_state), 200
            else:
                print(f"No saved state found for user: {current_user.id}")
                # Return default state for new users
                default_state = {
                    'level_states': {},
                    'completed_levels': [],
                    'current_level': 'level1',
                    'last_updated': None
                }
                return jsonify(default_state), 200
        else:
            print("User not authenticated, returning default state")
            # Return default state for non-authenticated users
            default_state = {
                'level_states': {},
                'completed_levels': [],
                'current_level': 'level1',
                'last_updated': None
            }
            return jsonify(default_state), 200
            
    except Exception as e:
        print(f"Error loading all levels state: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/user/stats')
def get_user_stats():
    """Get user statistics"""
    try:
        if current_user.is_authenticated:
            stats = db.get_user_stats(current_user.id)
            return jsonify(stats), 200
        else:
            # Return empty stats for non-authenticated users
            return jsonify({
                'completed_levels': 0,
                'total_levels': 7,
                'progress_percentage': 0
            }), 200
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/share/level-completed', methods=['POST'])
@api_login_required
def generate_share_image():
    """Generate a shareable image for a completed level"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data received'}), 400
            
        level = data.get('level')
        board_state = data.get('board_state', [])
        moves_count = data.get('moves_count', 0)
        marbles_left = data.get('marbles_left', 1)
        
        if not level:
            return jsonify({'error': 'No level specified'}), 400
        
        # Get level configuration
        configs = get_game_configs()
        level_config = configs.get(level, {})
        level_name = level_config.get('name', level)
        level_description = level_config.get('description', '')
        
        # Create the share image
        image_data = create_share_image(
            level_name=level_name,
            level_description=level_description,
            board_state=board_state,
            moves_count=moves_count,
            marbles_left=marbles_left,
            user_name=current_user.name,
            user_email=current_user.email,
            level=level
        )
        
        # Convert to base64 for easy sharing
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        return jsonify({
            'image_data': image_base64,
            'level': level,
            'level_name': level_name
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal server error'}), 500

def create_share_image(level_name, level_description, board_state, moves_count, marbles_left, user_name, user_email, level):
    """Create a shareable image for a completed level"""
    try:
        # Image dimensions - make it square
        width, height = 800, 800
        
        # Create image with gradient background
        image = Image.new('RGB', (width, height), color='#1a1a2e')
        draw = ImageDraw.Draw(image)
        
        # Test basic drawing
        try:
            draw.rectangle([0, 0, width, height], fill='#1a1a2e')
        except Exception as e:
            raise e
        
        # Use default fonts for reliability across different environments
        # Create a simple font that works across all environments
        try:
            # Try to use a basic font that should be available
            title_font = ImageFont.load_default()
            subtitle_font = ImageFont.load_default()
            body_font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        except Exception as e:
            # Fallback to basic text drawing without custom fonts
            title_font = None
            subtitle_font = None
            body_font = None
            small_font = None
        
        # Draw gradient background
        try:
            for y in range(height):
                r = int(26 + (y / height) * 20)
                g = int(26 + (y / height) * 30)
                b = int(46 + (y / height) * 40)
                draw.line([(0, y), (width, y)], fill=(r, g, b))
        except Exception as e:
            # Fallback to solid background
            draw.rectangle([0, 0, width, height], fill='#1a1a2e')
        
        # Title
        title_text = f"{level_name} Completed!"
        if title_font:
            title_bbox = draw.textbbox((0, 0), title_text, font=title_font)
            title_width = title_bbox[2] - title_bbox[0]
        else:
            title_width = len(title_text) * 10  # Approximate width
        title_x = (width - title_width) // 2
        draw.text((title_x, 40), title_text, fill='#ffffff', font=title_font)
        
        # Subtitle
        subtitle_text = f"Puzzle: {level_description}"
        if subtitle_font:
            subtitle_bbox = draw.textbbox((0, 0), subtitle_text, font=subtitle_font)
            subtitle_width = subtitle_bbox[2] - subtitle_bbox[0]
        else:
            subtitle_width = len(subtitle_text) * 8  # Approximate width
        subtitle_x = (width - subtitle_width) // 2
        draw.text((subtitle_x, 80), subtitle_text, fill='#cccccc', font=subtitle_font)
        
        # Draw the game board - make it bigger
        board_size = 500
        board_x = (width - board_size) // 2
        board_y = 120
        
        # Board background
        draw.rectangle([board_x-10, board_y-10, board_x+board_size+10, board_y+board_size+10], 
                      fill='#2d2d44', outline='#4a4a6a', width=3)
        
        # Draw board cells
        cell_size = board_size // 9
        
        # Get initial configuration for this level
        configs = get_game_configs()
        level_config = configs.get(level, {})
        initial_marbles = level_config.get('marbles', [])
        
        for i in range(9):
            for j in range(9):
                x = board_x + j * cell_size
                y = board_y + i * cell_size
                
                # Determine cell color
                if i < 3 and j < 3 or i > 5 and j > 5 or i < 3 and j > 5 or i > 5 and j < 3:
                    # Invalid cells
                    cell_color = '#1a1a2e'
                else:
                    cell_color = '#f8f9fa'
                
                # Draw cell
                draw.rectangle([x, y, x+cell_size, y+cell_size], 
                             fill=cell_color, outline='#dee2e6', width=1)
                
                # Draw initial marble positions as lightly shaded squares
                if (i, j) in initial_marbles:
                    # Draw medium light orange square for initial marble positions
                    draw.rectangle([x+2, y+2, x+cell_size-2, y+cell_size-2], 
                                 fill='#ffd8a8', outline='#ffc078', width=1)
                
                # Draw current marble if present
                if i < len(board_state) and j < len(board_state[i]) and board_state[i][j]:
                    marble_radius = cell_size // 3
                    marble_x = x + cell_size // 2
                    marble_y = y + cell_size // 2
                    
                    # Draw marble with gradient effect
                    for r in range(marble_radius, 0, -1):
                        alpha = int(255 * (1 - (marble_radius - r) / marble_radius))
                        color = (0, 123, 255, alpha)
                        draw.ellipse([marble_x-r, marble_y-r, marble_x+r, marble_y+r], 
                                   fill=color, outline='#0056b3', width=2)
        
        # Stats section
        stats_y = board_y + board_size + 20
        
        # Stats background - make it tighter
        stats_bg_y = stats_y - 8
        stats_bg_height = 80
        draw.rectangle([80, stats_bg_y, width-80, stats_bg_y+stats_bg_height], 
                      fill='#2d2d44', outline='#4a4a6a', width=2)
        
        # Calculate initial marbles count from level config
        configs = get_game_configs()
        level_config = configs.get(level, {})
        initial_marbles = level_config.get('marbles', [])
        initial_marbles_count = len(initial_marbles)
        
        # Stats text
        stats_text = [
            f"Puzzle Size: {initial_marbles_count}",
            f"Player: {user_name or 'Anonymous'}"
        ]
        
        for i, text in enumerate(stats_text):
            y_pos = stats_y + i * 30
            draw.text((100, y_pos), text, fill='#ffffff', font=body_font)
        
        # Link section
        link_y = stats_bg_y + stats_bg_height + 20
        
        # Link text
        link_text = "https://skipping-stones.onrender.com"
        if body_font:
            link_bbox = draw.textbbox((0, 0), link_text, font=body_font)
            link_width = link_bbox[2] - link_bbox[0]
        else:
            link_width = len(link_text) * 6  # Approximate width
        link_x = (width - link_width) // 2
        draw.text((link_x, link_y), link_text, fill='#007bff', font=body_font)
        
        # Footer
        footer_text = "Skipping Stones Puzzle Game"
        if small_font:
            footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
            footer_width = footer_bbox[2] - footer_bbox[0]
        else:
            footer_width = len(footer_text) * 5  # Approximate width
        footer_x = (width - footer_width) // 2
        draw.text((footer_x, height - 30), footer_text, fill='#888888', font=small_font)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        
        return img_byte_arr.getvalue()
        
    except Exception as e:
        raise e

if __name__ == '__main__':
    # Set up periodic cleanup (every hour)
    import threading
    import time
    
    def periodic_cleanup():
        while True:
            time.sleep(3600)  # Run every hour
            cleanup_old_sessions()
    
    # Start cleanup thread
    cleanup_thread = threading.Thread(target=periodic_cleanup, daemon=True)
    cleanup_thread.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)
