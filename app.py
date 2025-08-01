from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('skipping_stones'))

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/callback')
def callback():
    flash('Authentication not available', 'error')
    return redirect(url_for('skipping_stones'))





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
            'description': 'Small triange',
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
                (0, 3), (0, 4), (0, 5),
                (1, 3), (1, 4), (1, 5),
                (2, 3), (2, 4), (2, 5),
                (3, 1), (3, 2), (3, 3), (3, 4), (3, 5), (3, 6), (3, 7),
                (4, 1), (4, 2), (4, 3), (4, 5), (4, 6), (4, 7),
                (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7),
                (6, 3), (6, 4), (6, 5),
                (7, 3), (7, 4), (7, 5),
                (8, 3), (8, 4), (8, 5)
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
