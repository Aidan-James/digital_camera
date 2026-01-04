#!/usr/bin/env python3
"""
Video display script for /dev/video0
Displays video feed from video0 device to the desktop.

For SSH sessions: Set DISPLAY=:0.0 before running, or use ssh -X
Example: DISPLAY=:0.0 python3 video_test.py
"""

import os
import sys

# Set DISPLAY environment variable if not set (for SSH sessions)
# This assumes the HDMI desktop is on display :0.0
if 'DISPLAY' not in os.environ:
    os.environ['DISPLAY'] = ':0.0'
    print(f"DISPLAY not set, using {os.environ['DISPLAY']}")

import cv2

def main():
    # Check display connection
    display = os.environ.get('DISPLAY', 'not set')
    print(f"Using DISPLAY: {display}")
    
    # Test if we can create a window (this will fail if display is not accessible)
    try:
        test_window = cv2.namedWindow('test', cv2.WINDOW_NORMAL)
        cv2.destroyWindow('test')
    except Exception as e:
        print(f"\nError: Cannot connect to X11 display ({display})")
        print("\nPossible solutions:")
        print("1. If running from SSH, set DISPLAY before running:")
        print("   export DISPLAY=:0.0")
        print("   python3 video_test.py")
        print("\n2. Or allow X11 access (run on the local machine):")
        print("   xhost +local:")
        print("\n3. Or use X11 forwarding with SSH:")
        print("   ssh -X user@host")
        sys.exit(1)
    
    # Open video capture device (video0)
    # On Linux, this is typically /dev/video0
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("Error: Could not open video device /dev/video0")
        print("Make sure the device exists and is not being used by another application.")
        sys.exit(1)
    
    # Set video properties (optional, adjust as needed)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    print("Video feed started. Press 'q' to quit.")
    
    try:
        while True:
            # Read frame from video capture
            ret, frame = cap.read()
            
            if not ret:
                print("Error: Failed to read frame from video device")
                break
            
            # Display the frame in a window
            cv2.imshow('Video Feed - video0', frame)
            
            # Exit on 'q' key press
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Quitting...")
                break
    
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    
    finally:
        # Clean up
        cap.release()
        cv2.destroyAllWindows()
        print("Video feed closed.")

if __name__ == "__main__":
    main()

