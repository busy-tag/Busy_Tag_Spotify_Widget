import requests
import imageio
import pygifsicle
import os
import subprocess
import time
import numpy as np 
from io import BytesIO
from utils import delete_file
from PIL import Image, ImageDraw, ImageFont, ImageSequence
from serial_operations import open_serial_connection, find_busy_tag_device, close_serial_connection, send_serial_command

def get_track_image(track_info):
    try:
        image_url = track_info['item']['album']['images'][0]['url']
        response = requests.get(image_url)
        response.raise_for_status()

        image = Image.open(BytesIO(response.content))
        return image

    except requests.exceptions.RequestException as e:
        print(f"Error fetching the image: {e}")
        return None

def save_image(image, path):
    try:
        image.save(path)
    except Exception as e:
        print(f"Error saving the image: {e}")

def handle_image_text(track_info, draw, album_image_height, font_path):
    track_name = track_info.get('item', {}).get('name', None)
    if track_name is None:
        print("Track name not found in track_info.")
        return None

    artist_name = track_info.get('item', {}).get('album', {}).get('artists', [{}])[0].get('name', "Unknown Artist")

    if "(feat." in track_name:
        track_name = track_name.split("(feat.")[0].strip()

    if len(track_name) < 13:
        track_font_size = 24
        artist_font_size = 18
    elif 13 <= len(track_name) <= 16:
        track_font_size = 20
        artist_font_size = 14
    elif 16 < len(track_name) <= 20:
        track_font_size = 16
        artist_font_size = 12
    else:
        track_font_size = 16
        artist_font_size = 10

    track_font = ImageFont.truetype(font_path, track_font_size)
    artist_font = ImageFont.truetype(font_path, artist_font_size)

    text_y_track = album_image_height + 2
    text_y_artist = text_y_track + track_font_size +2 

    if len(track_name) > 20:
        split_index = track_name.rfind(' ', 0, 21)
        if split_index == -1:
            split_index = 20

        first_line = track_name[:split_index]
        second_line = track_name[split_index:].strip()

        draw.text((50, text_y_track), first_line, font=track_font, fill=(255, 255, 255))
        text_y_second_line = text_y_track + track_font_size + 5
        draw.text((50, text_y_second_line), second_line, font=track_font, fill=(255, 255, 255))
        text_y_artist = text_y_second_line + track_font_size + 5
    else:
        draw.text((50, text_y_track), track_name, font=track_font, fill=(255, 255, 255))

    draw.text((50, text_y_artist), artist_name, font=artist_font, fill=(128, 128, 128))

def create_image_with_text(track_info, image_path, drive_letter):
    canvas_width = 240
    canvas_height = 280

    canvas = Image.new('RGB', (canvas_width, canvas_height), (0, 0, 0))

    try:
        track_image = Image.open(image_path)
    except IOError:
        print(f"Error opening the image at {image_path}")
        return

    album_image_height = 225
    album_image_width = 240

    track_image = track_image.resize((album_image_width, album_image_height))

    x_offset = (canvas_width - album_image_width) // 2
    y_offset = 0

    canvas.paste(track_image, (x_offset, y_offset))

    draw = ImageDraw.Draw(canvas)

    font_path = "MontserratBlack-3zOvZ.ttf"

    handle_image_text(track_info, draw, album_image_height, font_path)

    try:
        spotify_logo = Image.open("spotify_logo.png")
        logo_size = (30, 30)
        spotify_logo = spotify_logo.resize(logo_size)

        logo_x = 13
        logo_y = canvas_height - 49

        canvas.paste(spotify_logo, (logo_x, logo_y), spotify_logo)
    except IOError:
        print("Error opening the Spotify logo image.")

    output_path = f"{drive_letter}//current_track_image.png"
    canvas.save(output_path)

def create_background_with_text(track_info, drive_letter):
    logo_path = "spotify_logo.png"
    canvas_width = 240
    canvas_height = 280
    album_image_height = 225

    canvas = Image.new('RGBA', (canvas_width, canvas_height), (0, 0, 0, 255))

    draw = ImageDraw.Draw(canvas)
    font_path = "MontserratBlack-3zOvZ.ttf"

    handle_image_text(track_info, draw, album_image_height, font_path)

    try:
        spotify_logo = Image.open(logo_path).convert("RGBA")
        spotify_logo = spotify_logo.resize((30, 30))
        logo_x = 13
        logo_y = canvas_height - 49
        canvas.paste(spotify_logo, (logo_x, logo_y), spotify_logo)
    except IOError:
        print("Error opening the Spotify logo image.")

    return canvas


def overlay_gif_on_background(gifsicle_path, input_gif, output_gif, background_canvas):
    with Image.open(input_gif) as img:
        new_gif_frames = []
        album_image_height = 225
        album_image_width = 240

        for frame in ImageSequence.Iterator(img):
            frame_image = frame.convert("RGB")
            frame_image = frame_image.resize((album_image_width, album_image_height))

            new_frame = background_canvas.copy()
            new_frame.paste(frame_image, (0, 0))

            quantized_frame = new_frame.convert("P", palette=Image.ADAPTIVE, colors = 256)
            new_gif_frames.append(quantized_frame)

        temp_gif_path = "temp_overlay.gif"
        new_gif_frames[0].save(
            temp_gif_path,
            save_all=True,
            append_images=new_gif_frames[1:],
            duration=img.info['duration'],
            loop=0,
            optimize=True
        )

    command = [
            gifsicle_path,
            '--dither',
            '--lossy=80',
            '--optimize=3',
            '--output', output_gif, 
            temp_gif_path
        ]

    try:
        subprocess.run(command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running gifsicle: {e}")
    finally:
        if os.path.exists(temp_gif_path):
            os.remove(temp_gif_path)
     


def convert_mp4_to_gif(mp4_file_path, gif_file_path, start_time=None, end_time=10, target_fps=10, resize=None, colors=256):
    try:
        if not os.path.exists(mp4_file_path):
            print(f"Error: MP4 file not found at {mp4_file_path}")
            return

        reader = imageio.get_reader(mp4_file_path)
        original_fps = reader.get_meta_data()['fps']
        frame_step = max(1, int(original_fps / target_fps))
        frames = []

        for i, frame in enumerate(reader):
            timestamp = i / original_fps
            if (start_time is None or timestamp >= start_time) and (end_time is None or timestamp <= end_time):
                if i % frame_step == 0:
                    if resize:
                        pil_image = Image.fromarray(frame)
                        pil_image = pil_image.resize(resize, Image.LANCZOS)
                        frame = np.array(pil_image)

                    frames.append(frame)

        imageio.mimsave(gif_file_path, frames, fps=target_fps, palettesize=colors, loop=0)

    except Exception as e:
        print(f"An error occurred: {e}")

def process_track_image(track_info, drive_letter):
    new_track_name = track_info['item']['name']
    artist_name = track_info['item']['artists'][0]['name']
    track_image = get_track_image(track_info)

    ser = open_serial_connection(find_busy_tag_device())
    if ser is None:
        print("No Busy Tag device found.")
        return
    try:
        send_serial_command(ser, "AT+SP=current_track_image.png")
        time.sleep(0.5)
        delete_file(f"{drive_letter}//current_track_gif.gif")
    except Exception as e:
        print(f"Error sending track image to device: {e}")

    if track_image:
        save_image(track_image, "track_image.png")
        create_image_with_text(track_info, "track_image.png", drive_letter)
        time.sleep(3.5)

        try:
            send_serial_command(ser, "AT+SP=current_track_image.png")
            time.sleep(0.5)
        except Exception as e:
            print(f"Error sending track image to device: {e}")
        finally:
            close_serial_connection(ser)
    else:
        print("No track image found for the current track.")