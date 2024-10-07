import requests
import os
import time
from urllib.parse import urlencode
from canvas_API import get_canvases
from utils import delete_file
from image_operations import convert_mp4_to_gif, create_background_with_text, overlay_gif_on_background
from serial_operations import open_serial_connection, find_busy_tag_device, close_serial_connection, send_serial_command

def request(url, method='get', data=None, headers={}):
    try:
        if method.lower() == 'post':
            response = requests.post(url, data=urlencode(data), headers=headers)
        else:
            response = requests.get(url, params=data, headers=headers)
        
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        print(f"ERROR {url}: {error}")
        if error.response:
            print(f"Status: {error.response.status_code} {error.response.reason}")
            if 'error' in error.response.json():
                print(error.response.json()['error'])
        return None


def get_canvas_token():
    url = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'
    data = request(url)
    return data['accessToken'] if data else None


def download_canvas(url, name):
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        working_directory = os.getcwd()
        filename = f"{name}.mp4"
        canvas_path = os.path.join(working_directory, filename)

        with open(canvas_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True
    except requests.RequestException as error:
        print(f"Failed to download the canvas video from {url}: {error}")
        return False


def get_canvas_url(track_id):
    canvas_token = get_canvas_token()
    if not canvas_token:
        print("Failed to get access token")

        return None

    unique_tracks = [{'track': {'uri': track_id}}]
    canvas_response = get_canvases(unique_tracks, canvas_token)

    if canvas_response and canvas_response.canvases:
        canvas_url = canvas_response.canvases[0].canvas_url

        return canvas_url
    else:
        print("Current track has no video.")

        return None

def save_canvas(track_info, name):
    track_uri = track_info['item']['uri']
    canvas_url = get_canvas_url(track_uri)
    if canvas_url:

        return download_canvas(canvas_url, name)
    else:
        return False

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 4:
        print("Usage: python save_canvas.py <track_id> <save_to_directory> <file_name>")
        sys.exit(1)

    track_id = sys.argv[1]
    save_to = sys.argv[2]
    name = sys.argv[3]

    save_canvas(track_id, save_to, name)

def process_canvas(gifsicle_path, drive_letter, track_info, track_changed_flag, stop_thread_event):
    print("Track video detected and being processed")
    mp4_file_path = "track_video.mp4"
    gif_file_path = "unedited_gif.gif"
    output_gif = f"{drive_letter}//current_track_gif.gif"

    try:
        convert_mp4_to_gif(mp4_file_path, gif_file_path, target_fps=10, resize=(240, 320), colors=128)
        time.sleep(0.2)

        if stop_thread_event.is_set():
            return

        background_canvas = create_background_with_text(track_info, drive_letter)
        overlay_gif_on_background(gifsicle_path, gif_file_path, output_gif, background_canvas)
        time.sleep(4)

        if stop_thread_event.is_set():
            return

        ser = open_serial_connection(find_busy_tag_device())
        if ser is None:
            print("No Busy Tag device found.")
            return

        try:
            time.sleep(1)
            send_serial_command(ser, "AT+SP=current_track_gif.gif")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error sending track image to device: {e}")
        finally:
            close_serial_connection(ser)

        delete_file(mp4_file_path)
        delete_file(gif_file_path)
    except Exception as e:
        print(f"Error processing canvas: {e}")
    finally:
        track_changed_flag.clear()