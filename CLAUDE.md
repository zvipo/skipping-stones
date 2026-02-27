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

# Solve queue CLI (requires AWS credentials)
python3 solve_queue.py           # solve one pending item
python3 solve_queue.py --all     # solve all pending items
python3 solve_queue.py --stats   # show queue statistics
python3 solve_queue.py --cleanup # remove solved/failed items from queue
```

Tests use a custom runner (not pytest). Some tests (Google login, logout) require the Flask app running on localhost:5000. Compression tests run standalone.

## Architecture

**Backend modules:**
- `app.py` — Flask app with all routes, Google OIDC auth flow (JWT verification against Google's public keys), Flask-Login session management, security headers middleware, hint endpoint (calls solver), and a share image generator (Pillow)
- `board_shapes.py` — Single source of truth for all board geometries. Defines 5 shapes (Wiegleb, English, European, Asymmetrical, Diamond) with grid dimensions, valid cell positions, and center cell. `SHAPE_ORDER` controls display order. Level configurations in `app.py` reference these shapes by ID.
- `database.py` — DynamoDB client wrapper (`db` singleton) with board/move compression utilities. Compression converts boolean boards to binary strings (`9x9:000...`). Handles backward compatibility with old uncompressed JSON data.
- `solver.py` — DFS backtracking peg solitaire solver using bitmask representation. Supports multiple board shapes via `shape_id` parameter (defaults to `'wiegleb'`). Per-shape solver data (valid cells, cell index, precomputed moves) is lazily built and cached in `_SOLVER_DATA_CACHE`. Each board state is a single integer bitmask. Transposition table (set of failed bitmask states) for pruning. Configurable time limit (default 5s). `DIRECTIONS` currently supports only orthogonal moves: up, down, left, right.
- `solver_cache.py` — DynamoDB cache (`solver_cache` singleton) for solver solutions. Keys are bitmask integers for Wiegleb, or `"{shape_id}:{bitmask}"` for other shapes. Supports write-through caching of entire solution paths (every intermediate state along a solved path is also cached). Sentinel values: `"NO_SOLUTION"` (definitively unsolvable), `"QUEUED"` (pending background solve).
- `solver_queue.py` — DynamoDB queue (`solver_queue` singleton) for board states that timed out. Items have status: pending → solving → solved/failed. Stale "solving" items auto-reset after 1 hour.
- `solve_queue.py` — CLI utility for processing queued states with multiprocessing support.

**Hint pipeline:** Player clicks Hint → `app.py` checks solver cache → on miss, runs `solver.solve()` with 10s limit → on timeout, enqueues to solver queue and returns "solving in background" → background worker (daemon thread in app or `solve_queue.py` CLI) solves without time limit → result cached for instant future hints.

**Frontend (all in templates/):**
- `skipping_stones.html` — Contains the entire game engine in vanilla JavaScript (~73KB). Handles board rendering, move validation, drag-and-drop, level selection, and state management via API calls.
- `base.html` — Shared layout with Bootstrap 5, navigation, and auth UI
- `login.html` / `index.html` — Login and home pages

**Key design decisions:**
- Authentication is optional — the game is fully playable without login; state saving requires auth
- Single Gunicorn worker in production to avoid session sharing issues (server-side session state)
- All three DynamoDB tables auto-create on first run if they don't exist
- Level configurations are defined in the `/api/skipping-stones/configs` endpoint in `app.py`, referencing board shapes from `board_shapes.py`

## Environment Variables

Configured via `.env` file (see README.md for full list). Key vars: `SECRET_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REDIRECT_URI`, AWS credentials, `DYNAMODB_TABLE_NAME`, `SOLVER_CACHE_TABLE_NAME`, `SOLVER_QUEUE_TABLE_NAME`.

## API Structure

Web routes: `/` (redirect), `/login`, `/callback`, `/logout`, `/skipping-stones`

API endpoints under `/api/`:
- `game-state/save`, `game-state/load`, `game-state/save-all-levels`, `game-state/load-all-levels`, `game-state/complete-level` — Game persistence
- `auth/status`, `auth/logout`, `auth/refresh-session` — Auth management
- `skipping-stones/configs` — Level configurations
- `skipping-stones/hint` — Solver-powered hint (returns next move or status)
- `user/stats` — User statistics
- `share/level-completed` — Generates shareable PNG image
