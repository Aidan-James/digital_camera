#!/usr/bin/env python3
"""Digital camera - captures photos and videos to SD card."""

import os, sys, subprocess, time

if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0.0'

import cv2
import numpy as np
import Jetson.GPIO as GPIO
from GPIO_interface import Switch

# Config
SCREEN_WIDTH, SCREEN_HEIGHT = 570, 320
OVERLAY_FONT = cv2.FONT_HERSHEY_SIMPLEX

# Global state
current_mode = 0  # 0=cam, 1=video
last_frame = None
is_recording = False
video_writer = None
video_filepath = None
camera_fps = 10.0
recording_start_time = None
recording_frame_count = 0

def get_sd_path():
    """Mount SD card and return path, or None."""
    try:
        result = subprocess.run(["udisksctl", "mount", "-b", "/dev/sda1"],
                                capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if "Mounted" in line and "at" in line:
                    return line.split("at")[-1].strip().rstrip('.')
        if "already mounted" in result.stderr.lower():
            mount_result = subprocess.run(["findmnt", "-n", "-o", "TARGET", "/dev/sda1"],
                                          capture_output=True, text=True)
            if mount_result.returncode == 0:
                return mount_result.stdout.strip()
    except:
        pass
    return None

def get_next_filename(dcim_path, prefix, ext):
    """Get next available numbered filename with prefix."""
    highest = 0
    for f in os.listdir(dcim_path):
        if f.startswith(prefix) and f.endswith(ext):
            num_part = f[len(prefix):-len(ext)]
            if num_part.isdigit():
                highest = max(highest, int(num_part))
    return os.path.join(dcim_path, f"{prefix}{highest + 1:03d}{ext}")

def trigger_callback():
    """Handle trigger button press."""
    global last_frame, is_recording, video_writer, video_filepath
    global recording_start_time, recording_frame_count, camera_fps
    
    if last_frame is None:
        return
    
    mount_path = get_sd_path()
    if mount_path is None:
        print("No SD card")
        return
    
    dcim_path = os.path.join(mount_path, "DCIM")
    os.makedirs(dcim_path, exist_ok=True)
    
    if current_mode == 0:  # Photo mode
        filepath = get_next_filename(dcim_path, "img_", ".jpg")
        cv2.imwrite(filepath, last_frame)
        os.sync()
        print(f"Saved: {filepath}")
    else:  # Video mode
        if not is_recording:
            video_filepath = get_next_filename(dcim_path, "mov_", ".mp4")
            h, w = last_frame.shape[:2]
            video_writer = cv2.VideoWriter(video_filepath, 
                cv2.VideoWriter_fourcc(*'mp4v'), camera_fps, (w, h))
            is_recording = True
            recording_start_time = time.time()
            recording_frame_count = 0
            print(f"Recording: {video_filepath}")
        else:
            if video_writer:
                video_writer.release()
                video_writer = None
                os.sync()
                elapsed = time.time() - recording_start_time
                if elapsed > 0 and recording_frame_count > 0:
                    camera_fps = recording_frame_count / elapsed
                    print(f"Stopped: {recording_frame_count} frames, {elapsed:.1f}s, {camera_fps:.1f} fps")
            is_recording = False

def rebuild_overlay(overlay, elements):
    """Redraw overlay text."""
    overlay[:] = 0
    for elem in elements.values():
        cv2.putText(overlay, elem["text"], elem["pos"], OVERLAY_FONT, 1.0, (255,255,255), 2)
    overlay[np.any(overlay[:,:,:3] > 0, axis=2), 3] = 255

def main():
    global camera_fps, current_mode, last_frame, recording_frame_count
    
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open camera")
        sys.exit(1)
    
    # Calibrate FPS
    print("Calibrating FPS...")
    start = time.time()
    frames = 0
    while time.time() - start < 1.0:
        if cap.read()[0]: frames += 1
    camera_fps = frames / (time.time() - start) if frames > 0 else 10.0
    print(f"Camera FPS: {camera_fps:.1f}")
    
    # Setup window
    cv2.namedWindow('cam', cv2.WINDOW_NORMAL)
    cv2.moveWindow('cam', 0, 0)
    cv2.resizeWindow('cam', SCREEN_WIDTH, SCREEN_HEIGHT)
    cv2.setWindowProperty('cam', cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
    
    # Setup inputs
    mode_switch = Switch(31)
    trigger = Switch(32, callback=trigger_callback)
    
    # Setup overlay
    overlay = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 4), dtype=np.uint8)
    overlay_elements = {"mode": {"text": "cam", "pos": (10, SCREEN_HEIGHT - 10)}}
    prev_mode = None
    
    print("Running. Press 'q' to quit.")
    
    try:
        while True:
            mode_switch.update()
            trigger.update()
            
            if mode_switch.state != prev_mode:
                current_mode = mode_switch.state
                overlay_elements["mode"]["text"] = "cam" if current_mode == 0 else "video"
                rebuild_overlay(overlay, overlay_elements)
                prev_mode = mode_switch.state
            
            ret, frame = cap.read()
            if not ret:
                break
            
            last_frame = frame.copy()
            
            if is_recording and video_writer:
                video_writer.write(frame)
                recording_frame_count += 1
            
            # Display with overlay
            frame = cv2.resize(frame, (SCREEN_WIDTH, SCREEN_HEIGHT))
            alpha = overlay[:,:,3:4].astype(np.float32) / 255.0
            alpha3 = np.repeat(alpha, 3, axis=2)
            frame = (frame.astype(np.float32) * (1 - alpha3) + 
                     overlay[:,:,:3].astype(np.float32) * alpha3).astype(np.uint8)
            
            cv2.imshow('cam', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
    
    except KeyboardInterrupt:
        pass
    
    finally:
        if video_writer:
            video_writer.release()
            os.sync()
        cap.release()
        cv2.destroyAllWindows()
        GPIO.cleanup()

if __name__ == "__main__":
    main()
