# LeRobot Panorama

A web-based control interface for the LeRobot Panorama system, allowing you to control robotic arms for taking panoramic photos.

## Features

- Web-based control interface
- Real-time log monitoring
- Support for both panorama and debug scripts
- Configurable robot parameters
- Automatic log updates

## Setup

1. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Running the Web UI

1. Make sure your virtual environment is activated:
```bash
source venv/bin/activate  # On Windows use: venv\Scripts\activate
```

2. Start the Flask application:
```bash
python app.py
```

3. Open your web browser and navigate to:
```
http://localhost:5000
```

## Using the Interface

1. Configure the robot parameters in the left panel:
   - Robot Type (default: so101_follower)
   - Robot Port (default: COM4)
   - Robot ID
   - Step Folder
   - Photo Folder
   - Other parameters as needed

2. Choose which script to run:
   - "Run Panorama Script" for taking panoramic photos
   - "Run Debug Script" for debugging robot movements

3. Monitor the execution in the right panel:
   - Logs are automatically updated every 5 seconds
   - Click "Refresh" to manually update logs
   - Logs are saved in the `logs` directory

## Scripts

- `take_panorama_images.py`: Main script for taking panoramic photos
- `debug_shell.py`: Debug script for testing robot movements
- `app.py`: Web interface application

## Requirements

- Python 3.8 or higher
- Flask
- Other dependencies listed in `requirements.txt`