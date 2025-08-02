# Skipping Stones - Flask Web Application

A simple Flask web application for playing the Skipping Stones game with a modern, responsive UI.

## Features

- 🎮 Skipping Stones game
- 🎨 Modern, responsive Bootstrap UI
- 📱 Mobile-friendly design
- 🔐 Optional Google OIDC authentication

## Prerequisites

- Python 3.7 or higher

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Environment Setup (Optional)

For Google OIDC authentication, create a `.env` file with the following variables:

```bash
# Flask Secret Key (required for sessions)
SECRET_KEY=your-secret-key-change-this

# Google OIDC Configuration (optional)
# Get these from https://console.developers.google.com/
# Create a new project and enable Google+ API
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

**To set up Google OIDC:**
1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Create OAuth 2.0 credentials
5. Add your domain to authorized redirect URIs (e.g., `https://yourdomain.com/callback`)
6. Copy the Client ID and Client Secret to your `.env` file

### 3. Run the Application

```bash
python3 app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Home Page**: Visit the homepage to start playing the game
2. **Authentication**: Click "Login" in the navigation bar to sign in with Google (optional)
3. **Game**: The game is available to play with or without authentication

## Project Structure

```
skippingstones/
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── env.example           # Environment variables template
├── README.md            # This file
└── templates/           # HTML templates
    ├── base.html        # Base template with navigation
    ├── index.html       # Home page
    ├── login.html       # Login page
    └── skipping_stones.html  # Game page
```

## Security Features

- ✅ HTTPS-ready configuration
- ✅ Optional Google OIDC authentication
- ✅ Secure session management

## Customization



### Styling

The application uses Bootstrap 5 with custom CSS for a modern look. You can modify the styles in `templates/base.html`.



## Troubleshooting

### Common Issues

1. **Game not loading**: Ensure all JavaScript files are properly loaded

### Debug Mode

The application runs in debug mode by default. For production, set `debug=False` in `app.py`.

## License

This project is open source and available under the MIT License.

## Contributing

Feel free to submit issues and enhancement requests! 