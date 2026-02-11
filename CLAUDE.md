# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Skipping Stones is a Flask web application for playing a peg solitaire puzzle game. Players jump stones over adjacent stones to remove them, trying to leave as few as possible. The app supports optional Google OIDC authentication and persists game state to AWS DynamoDB.

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app (serves on http://localhost:5000)
python3 app.py

# Run all tests
python3 run_tests.py

# Run a single test file
python3 tests/test_compression.py

# Deploy with Docker
./deploy.sh
```

Tests use a custom runner (not pytest). Some tests (Google login, logout) require the Flask app running on localhost:5000. Compression tests run standalone.

## Architecture

**Two-file backend:**
- `app.py` — Flask app with all routes, Google OIDC auth flow (JWT verification against Google's public keys), Flask-Login session management, security headers middleware, and a share image generator (Pillow)
- `database.py` — DynamoDB client wrapper (`db` singleton) with board/move compression utilities. Compression converts boolean boards to binary strings (`9x9:000...`) achieving 80-90% size reduction. Handles backward compatibility with old uncompressed JSON data.

**Frontend (all in templates/):**
- `skipping_stones.html` — Contains the entire game engine in vanilla JavaScript (~73KB). Handles board rendering, move validation, drag-and-drop, level selection, and state management via API calls.
- `base.html` — Shared layout with Bootstrap 5, navigation, and auth UI
- `login.html` / `index.html` — Login and home pages

**Key design decisions:**
- Authentication is optional — the game is fully playable without login; state saving requires auth
- Single Gunicorn worker in production to avoid session sharing issues (server-side session state)
- DynamoDB table auto-creates on first run if it doesn't exist
- All game level configurations (7 levels: Cross, Triangle, Arrow, Diamond, Square, Full Board, etc.) are defined in `/api/skipping-stones/configs` endpoint in `app.py`

## Environment Variables

Configured via `.env` file (see README.md for full list). Key vars: `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, AWS credentials, `DYNAMODB_TABLE_NAME`.

## API Structure

Web routes: `/` (redirect), `/login`, `/callback`, `/logout`, `/skipping-stones`

API endpoints under `/api/`:
- `game-state/save`, `game-state/load`, `game-state/save-all-levels`, `game-state/load-all-levels`, `game-state/complete-level` — Game persistence
- `auth/status`, `auth/logout`, `auth/refresh-session` — Auth management
- `skipping-stones/configs` — Level configurations
- `user/stats` — User statistics
- `share/level-completed` — Generates shareable PNG image
