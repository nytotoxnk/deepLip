import cv2
import mediapipe as mp
import numpy as np

def check_rotations_for_face_detection(video_path, num_frames_to_check=10, model_selection=0, min_detection_confidence=0.6):
    mp_face_detection = mp.solutions.face_detection
    
    print(f"Checking video: {video_path}")
    print(f"Will check the first {num_frames_to_check} frames for face detection across rotations.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {video_path}. Please check the path.")
        return

    # Using model_selection=1 for general case, can try 0 if faces are very close
    with mp_face_detection.FaceDetection(
        model_selection=model_selection, min_detection_confidence=min_detection_confidence) as face_detection:
        
        frame_count = 0
        while cap.isOpened() and frame_count < num_frames_to_check:
            ret, frame = cap.read()
            if not ret:
                print(f"Reached end of video or failed to read frame {frame_count}.")
                break

            print(f"\n--- Checking Frame {frame_count} ---")
            
            # Define rotations to try (clockwise)
            rotations = {
                0: "0 degrees (Original)",
                90: "90 degrees clockwise",
                180: "180 degrees clockwise",
                270: "270 degrees clockwise"
            }
            
            # OpenCV's rotate codes
            cv_rot_codes = {
                0: None, # No rotation
                90: cv2.ROTATE_90_CLOCKWISE,
                180: cv2.ROTATE_180,
                270: cv2.ROTATE_90_COUNTERCLOCKWISE # 270 CW is 90 CCW
            }

            face_detected_in_frame = False
            for degrees, description in rotations.items():
                rotated_frame = frame.copy()
                if cv_rot_codes[degrees] is not None:
                    rotated_frame = cv2.rotate(frame, cv_rot_codes[degrees])
                
                # Convert the BGR image to RGB.
                image_rgb = cv2.cvtColor(rotated_frame, cv2.COLOR_BGR2RGB)
                image_rgb.flags.writeable = False # To improve performance
                results = face_detection.process(image_rgb)
                image_rgb.flags.writeable = True

                if results.detections:
                    print(f"  Face detected at {description}!")
                    face_detected_in_frame = True
                    # Optionally, you can display the frame with detection for visual confirmation
                    # mp_drawing = mp.solutions.drawing_utils
                    # annotated_image = rotated_frame.copy()
                    # for detection in results.detections:
                    #     mp_drawing.draw_detection(annotated_image, detection)
                    # cv2.imshow(f'Frame {frame_count} - {description}', annotated_image)
                    # cv2.waitKey(0) # Wait for a key press
                    # cv2.destroyAllWindows()
                    break # Stop checking rotations for this frame once a face is found
                else:
                    print(f"  No face detected at {description}.")

            if not face_detected_in_frame:
                print(f"No face detected in Frame {frame_count} at any tested rotation.")

            frame_count += 1
            
    cap.release()
    cv2.destroyAllWindows()
    print("\nFinished checking frames.")

# --- Example Usage ---
# Replace 'path/to/your/video.mp4' with the actual path to your video.
# Use the video that you had rotated 180 degrees for your script, as it was the last attempt.
# Or, use your absolute original video to see which rotation (0, 90, 180, 270) helps.
check_rotations_for_face_detection('videos/rotated_180_cropped.mp4')
# You can also test with the original video:
# check_rotations_for_face_detection('videos/20250429_115126.mp4')