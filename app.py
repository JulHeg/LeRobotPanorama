from flask import Flask, render_template, request, jsonify
import subprocess
import os
import sys
from datetime import datetime

app = Flask(__name__)

# Default values for arguments
DEFAULTS = {
    'robot_type': 'so101_follower',
    'robot_port': 'COM4',
    'robot_id': 'my_awesome_follower_arm',
    'step_folder': 'robot_steps',
    'photo_folder': 'photos',
    'seconds_per_step': '4',
    'fps': '60',
    'num_steps': '6',
    'interp_seconds': '1.0',
}

@app.route('/')
def index():
    return render_template('index.html', defaults=DEFAULTS)

@app.route('/run_script', methods=['POST'])
def run_script():
    script_type = request.form.get('script_type')
    if script_type not in ['panorama', 'debug']:
        return jsonify({'error': 'Invalid script type'}), 400

    # Get form data
    args = {
        'robot_type': request.form.get('robot_type', DEFAULTS['robot_type']),
        'robot_port': request.form.get('robot_port', DEFAULTS['robot_port']),
        'robot_id': request.form.get('robot_id', DEFAULTS['robot_id']),
        'step_folder': request.form.get('step_folder', DEFAULTS['step_folder']),
        'photo_folder': request.form.get('photo_folder', DEFAULTS['photo_folder']),
        'seconds_per_step': request.form.get('seconds_per_step', DEFAULTS['seconds_per_step']),
        'fps': request.form.get('fps', DEFAULTS['fps']),
        'num_steps': request.form.get('num_steps', DEFAULTS['num_steps']),
        'interp_seconds': request.form.get('interp_seconds', DEFAULTS['interp_seconds']),
    }

    # Build command based on script type
    if script_type == 'panorama':
        cmd = [
            sys.executable, 'take_panorama_images.py',
            f'--robot.type={args["robot_type"]}',
            f'--robot.port={args["robot_port"]}',
            '--robot.cameras={}',
            f'--robot.id={args["robot_id"]}',
            f'--step_folder={args["step_folder"]}',
            f'--photo_folder={args["photo_folder"]}',
            f'--seconds_per_step={args["seconds_per_step"]}',
            f'--fps={args["fps"]}',
        ]
    else:  # debug
        cmd = [
            sys.executable, 'debug_shell.py',
            f'--robot.type={args["robot_type"]}',
            f'--robot.port={args["robot_port"]}',
            '--robot.cameras={}',
            f'--robot.id={args["robot_id"]}',
            f'--step_folder={args["step_folder"]}',
            f'--num_steps={args["num_steps"]}',
            f'--interp_seconds={args["interp_seconds"]}',
            f'--fps={args["fps"]}',
        ]

    try:
        # Create a log file for this run
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = f'logs/run_{timestamp}.log'
        os.makedirs('logs', exist_ok=True)

        # Run the script and redirect output to the log file
        with open(log_file, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=f,
                stderr=subprocess.STDOUT,
                text=True
            )

        return jsonify({
            'success': True,
            'message': f'Script started successfully. Log file: {log_file}',
            'pid': process.pid
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get_logs')
def get_logs():
    try:
        logs_dir = 'logs'
        if not os.path.exists(logs_dir):
            return jsonify([])
        
        logs = []
        for filename in sorted(os.listdir(logs_dir), reverse=True):
            if filename.endswith('.log'):
                filepath = os.path.join(logs_dir, filename)
                with open(filepath, 'r') as f:
                    content = f.read()
                logs.append({
                    'filename': filename,
                    'content': content
                })
        return jsonify(logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000) 