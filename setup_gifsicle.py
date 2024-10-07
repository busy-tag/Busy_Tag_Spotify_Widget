import os
import sys
import shutil
import subprocess

def setup_gifsicle():
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.dirname(os.path.abspath(__file__))

    bundled_gifsicle_path = os.path.join(exe_dir, 'resources', 'gifsicle', 'gifsicle.exe')
    destination = os.path.join(os.environ['USERPROFILE'], 'gifsicle')
    gifsicle_exe_path = os.path.join(destination, 'gifsicle.exe')

    try:
        if os.path.exists(bundled_gifsicle_path):
            os.makedirs(destination, exist_ok=True)
            shutil.copy(bundled_gifsicle_path, gifsicle_exe_path)

    except Exception as e:
        print(f"Error setting up gifsicle: {e}")
        return None

    return gifsicle_exe_path

def run_gifsicle(command_args):
    gifsicle_path = setup_gifsicle()

    if not gifsicle_path:
        print("Gifsicle setup failed. Cannot proceed with running gifsicle.")
        return None

    command = [gifsicle_path] + command_args
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        return result.stdout

    except subprocess.CalledProcessError as e:
        print(f"Gifsicle command failed with error: {e.stderr}")
        return None

    except Exception as e:
        print(f"Error running gifsicle: {e}")
        return None