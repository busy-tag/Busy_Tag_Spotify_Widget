from save_canvas import save_canvas, process_canvas
from auth import authorize_user, get_access_token
from spotify_API import get_current_track
from image_operations import create_image_with_text, get_track_image, process_track_image
from utils import get_drive_letter, delete_file
from serial_operations import send_serial_command, find_busy_tag_device, open_serial_connection, close_serial_connection
from setup_gifsicle import setup_gifsicle, run_gifsicle
import time
import threading

track_changed_flag = threading.Event()
stop_thread_event = threading.Event()

def handle_track_change(track_info, current_track_name):
    new_track_name = track_info.get('item', {}).get('name')
    if new_track_name and new_track_name != current_track_name:
        return new_track_name
    return current_track_name

def main():
    default_client_id = "1f2af53deb5d4338b7dc8dd2bc1d2c96"
    client_id = input("Please enter your Spotify CLIENT_ID (or press Enter to use the default): ").strip()
    if not client_id:
        client_id = default_client_id
        print(f"Using default CLIENT_ID: {client_id}")
    else:
        print(f"Using provided CLIENT_ID: {client_id}")

    drive_letter = get_drive_letter()
    auth_code, code_verifier = authorize_user(client_id)
    if auth_code:
        access_token = get_access_token(client_id, auth_code, code_verifier)
    else:
        print("Failed to authorize. Exiting...")
        return

    current_track_name = None
    track_paused_printed = False
    track_resumed_printed = False

    gifsicle_path = setup_gifsicle()

    if gifsicle_path is None:
        print("Gifsicle setup failed. Exiting...")
        return

    time.sleep(2)

    test_args = ["--version"]
    output = run_gifsicle(test_args)

    if output is None:
        print("Failed to run gifsicle. Exiting...")
        return

    try:
        while True:
            stop_thread_event.clear()
            track_info, status_code = get_current_track(access_token)

            if status_code == 401:
                auth_code, code_verifier = authorize_user(client_id)
                if auth_code:
                    access_token = get_access_token(client_id, auth_code, code_verifier)
                    if not access_token:
                        print("Failed to reauthorize. Exiting...")
                        break
                else:
                    print("Failed to reauthorize. Exiting...")
                    break

            if track_info and 'item' in track_info:
                is_playing = track_info.get('is_playing', False)

                if not is_playing:
                    if not track_paused_printed:
                        print("Track Paused.")
                        track_paused_printed = True
                        track_resumed_printed = False
                    time.sleep(0.5)
                    continue

                if is_playing and not track_resumed_printed:
                    print("Track Resumed.")
                    track_resumed_printed = True
                    track_paused_printed = False

                new_track_name = handle_track_change(track_info, current_track_name)

                if new_track_name != current_track_name:
                    stop_thread_event.set()
                    track_changed_flag.clear()
                    time.sleep(0.5)
                    current_track_name = new_track_name
                    print(f"Track changed, now playing -\n {new_track_name} by {track_info['item']['artists'][0]['name']}")
                    process_track_image(track_info, drive_letter)
                    success = save_canvas(track_info, "track_video")
                    if success:
                        time.sleep(0.5)
                        canvas_thread = threading.Thread(target=process_canvas, args=(gifsicle_path, drive_letter, track_info, track_changed_flag, stop_thread_event))
                        canvas_thread.start()

                    track_paused_printed = False
                    track_resumed_printed = True

            time.sleep(0.5)

    except KeyboardInterrupt:
        print("\nProgram terminated by user.")

if __name__ == "__main__":
    main()