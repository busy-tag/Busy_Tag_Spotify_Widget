import os
import shutil

def prompt_for_client_id():
    client_id = input("Please enter your Spotify CLIENT_ID: ")

    return client_id

def check_busy_tag_connection():
    is_connected = input("Is the BusyTag connected? (y/n): ").strip().lower() == 'y'
    drive_letter = None
    if is_connected:
        drive_letter = input("Please enter the drive letter of the BusyTag (e.g., E): ").strip().upper()
        if not os.path.exists(f"{drive_letter}:/"):
            print(f"Drive {drive_letter}:/ does not exist. Please check the drive letter and try again.")

            return None, None
    return is_connected, drive_letter

def get_drive_letter():
    while True:
        drive_letter = input("Please enter the drive letter assigned to Busy Tag (e.g., D): ").upper()
        if len(drive_letter) == 1 and drive_letter.isalpha():
            drive_letter = f"{drive_letter}:"
            if os.path.exists(f"{drive_letter}\\"):
                print(f"Ok.")

                return drive_letter
            else:
                print(f"Drive {drive_letter} does not exist. Please enter a valid drive letter.")
        else:
            print("Invalid input. Please enter a single letter (e.g., D).")

def transfer_file(source_path, destination_folder, new_name):
    try:
        if not os.path.exists(source_path):
            print(f"Error: Source file not found at {source_path}")
            return None
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
        destination_path = os.path.join(destination_folder, new_name)
        shutil.move(source_path, destination_path)

        return destination_path

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def delete_file(file_path):
    try:
        if os.path.exists(file_path):
            os.remove(file_path)

            return True
        else:
            return False
    except Exception as e:
        print(f"An error occurred while deleting the file: {e}")

        return False