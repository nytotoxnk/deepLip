import cv2
import mediapipe as mp
import numpy as np

def crop_and_center_face(input_video_path, output_video_path, target_size=512, target_fps=25):
    mp_face_detection = mp.solutions.face_detection
    mp_drawing = mp.solutions.drawing_utils

    # Initialize video capture
    cap = cv2.VideoCapture(input_video_path)
    if not cap.isOpened():
        print(f"Error: Could not open video {input_video_path}")
        return

    original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    original_fps = cap.get(cv2.CAP_PROP_FPS)

    # Define the codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_video_path, fourcc, target_fps, (target_size, target_size))

    with mp_face_detection.FaceDetection(
        model_selection=0, min_detection_confidence=0.6) as face_detection:
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Convert the BGR image to RGB.
            image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # To improve performance, optionally mark the image as not writeable to pass by reference.
            image_rgb.flags.writeable = False
            results = face_detection.process(image_rgb)
            image_rgb.flags.writeable = True

            cropped_frame = None
            if results.detections:
                # Assuming only one face for simplicity, or pick the largest
                detection = results.detections[0]
                bbox_norm = detection.location_data.relative_bounding_box

                # Convert normalized bounding box to pixel coordinates
                x_min = int(bbox_norm.xmin * original_width)
                y_min = int(bbox_norm.ymin * original_height)
                width = int(bbox_norm.width * original_width)
                height = int(bbox_norm.height * original_height)

                # Calculate center of the face
                face_center_x = x_min + width // 2
                face_center_y = y_min + height // 2

                # Calculate crop boundaries to center the face
                crop_x1 = max(0, face_center_x - target_size // 2)
                crop_y1 = max(0, face_center_y - target_size // 2)
                crop_x2 = min(original_width, face_center_x + target_size // 2)
                crop_y2 = min(original_height, face_center_y + target_size // 2)

                # Adjust if crop goes out of bounds at the edges
                if crop_x2 - crop_x1 < target_size:
                    if crop_x1 == 0:
                        crop_x2 = target_size
                    elif crop_x2 == original_width:
                        crop_x1 = original_width - target_size

                if crop_y2 - crop_y1 < target_size:
                    if crop_y1 == 0:
                        crop_y2 = target_size
                    elif crop_y2 == original_height:
                        crop_y1 = original_height - target_size

                # Ensure the final crop size is exactly target_size
                crop_x2 = crop_x1 + target_size
                crop_y2 = crop_y1 + target_size

                # Perform the crop
                cropped_frame = frame[crop_y1:crop_y2, crop_x1:crop_x2]

                # Resize if the cropped frame is not exactly target_size (e.g., at edges)
                if cropped_frame.shape[0] != target_size or cropped_frame.shape[1] != target_size:
                    cropped_frame = cv2.resize(cropped_frame, (target_size, target_size))

            else:
                # If no face is detected, you might choose to:
                # 1. Skip the frame
                # 2. Crop from the center of the original frame (fallback)
                # 3. Use the last known face position
                # For this example, we'll just center crop if no face detected
                print(f"Warning: No face detected in frame {frame_count}. Applying central crop.")
                center_x = original_width // 2
                center_y = original_height // 2
                crop_x1 = max(0, center_x - target_size // 2)
                crop_y1 = max(0, center_y - target_size // 2)
                cropped_frame = frame[crop_y1 : crop_y1 + target_size, crop_x1 : crop_x1 + target_size]
                if cropped_frame.shape[0] != target_size or cropped_frame.shape[1] != target_size:
                    cropped_frame = cv2.resize(cropped_frame, (target_size, target_size))


            if cropped_frame is not None:
                out.write(cropped_frame)
            frame_count += 1

    cap.release()
    out.release()
    cv2.destroyAllWindows()
    print(f"Processed video saved to {output_video_path}")

#Usage:
crop_and_center_face('videos/20250429_115126.mp4', 'videos/xest1.mp4', target_size=512, target_fps=25)