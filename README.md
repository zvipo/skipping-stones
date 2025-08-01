# Skipping Stones - Flask Web Application

A simple Flask web application for playing the Skipping Stones game with a modern, responsive UI.

## Features

- 🎮 Skipping Stones game
- 🎨 Modern, responsive Bootstrap UI
- 📱 Mobile-friendly design

## Prerequisites

- Python 3.7 or higher

## Setup Instructions

### 1. Clone and Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python3 app.py
```

The application will be available at `http://localhost:5000`

## Usage

1. **Home Page**: Visit the homepage to see the welcome screen
2. **Game**: Click "Play Skipping Stones" to start the game

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