# Skipping Stones - Flask Web Application

A simple Flask web application for playing the Skipping Stones game with a modern, responsive UI.

## Features

- 🎮 Skipping Stones game
- 🎨 Modern, responsive Bootstrap UI
- 📱 Mobile-friendly design
- 🔐 Optional Google OIDC authentication
- 💾 AWS DynamoDB state persistence
- 📊 User progress tracking
- 🔄 Automatic game state saving
- 🏆 Level completion tracking
- 💡 Hint system with DFS solver and shared DynamoDB cache
- ⏳ Background solve queue for complex boards that time out

## Prerequisites

- Python 3.7 or higher

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 2. Environment Setup

Create a `.env` file with the following variables:

```bash
# Flask Secret Key (required for sessions)
SECRET_KEY=your-secret-key-change-this

# Google OIDC Configuration (optional)
# Get these from https://console.developers.google.com/
# Create a new project and enable Google+ API
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/callback

# AWS Configuration (for state persistence)
# See SETUP.md for detailed AWS setup instructions
AWS_ACCESS_KEY_ID=your-aws-access-key-id
AWS_SECRET_ACCESS_KEY=your-aws-secret-access-key
AWS_DEFAULT_REGION=us-east-1
DYNAMODB_TABLE_NAME=skipping-stones-game-state
```

**To set up Google OIDC:**
1. Go to [Google Cloud Console](https://console.developers.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API
4. Create OAuth 2.0 credentials
5. Add your domain to authorized redirect URIs (e.g., `https://yourdomain.com/callback`)
6. Copy the Client ID and Client Secret to your `.env` file

**To set up AWS DynamoDB:**
See [SETUP.md](SETUP.md) for detailed instructions on configuring AWS credentials and DynamoDB.

### 3. Run the Application

```bash
python3 app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Home Page**: Visit the homepage to start playing the game
2. **Authentication**: Click "Login" in the navigation bar to sign in with Google (optional)
3. **Game**: The game is available to play with or without authentication
4. **State Persistence**: When logged in, your game state is automatically saved and restored
5. **Progress Tracking**: Completed levels are tracked and displayed with checkmarks

## Hint System

The game includes a solver-powered hint system. When a player clicks "Hint", the server runs a DFS backtracking solver to find a path to 1 stone remaining, then highlights the next move.

- **Solver cache**: Solutions are cached in a shared DynamoDB table (`skipping-stones-solver-cache`). Every intermediate state along a solution path is also cached, so subsequent hints from the same game are instant.
- **Background solve queue**: If the solver times out (10 seconds), the board state is queued in a DynamoDB table (`skipping-stones-solver-queue`) and solved asynchronously by a background worker thread — with no time limit. Once solved, the result is written to the solver cache for instant future hints.
- **Negative caching**: States that are definitively unsolvable (exhaustive search, no timeout) are cached so repeat requests return immediately with "No solution exists."

### Solve Queue CLI

A local CLI utility is provided for manually solving queued states (often faster than the background worker):

```bash
python3 solve_queue.py           # solve one pending item
python3 solve_queue.py --all     # solve all pending items
python3 solve_queue.py --stats   # show queue statistics
python3 solve_queue.py --cleanup # remove solved/failed items from queue
```

### Environment Variables (Hint System)

| Variable | Default | Description |
|----------|---------|-------------|
| `SOLVER_CACHE_TABLE_NAME` | `skipping-stones-solver-cache` | DynamoDB table for cached solutions |
| `SOLVER_QUEUE_TABLE_NAME` | `skipping-stones-solver-queue` | DynamoDB table for the background solve queue |

## Project Structure

```
skippingstones/
├── app.py                 # Main Flask application
├── database.py            # DynamoDB database operations
├── solver.py              # DFS backtracking peg solitaire solver
├── solver_cache.py        # DynamoDB cache for solver solutions
├── solver_queue.py        # DynamoDB queue for timed-out board states
├── solve_queue.py         # CLI utility for solving queued states
├── requirements.txt       # Python dependencies
├── SETUP.md               # AWS setup instructions
├── README.md              # This file
└── templates/             # HTML templates
    ├── base.html          # Base template with navigation
    ├── index.html         # Home page
    ├── login.html         # Login page
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