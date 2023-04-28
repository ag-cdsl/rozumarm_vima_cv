import cv2
import numpy as np
from aruco import draw_aruco
from calibrate_table import calibrate_table
from camera_utils import stream, StreamCallbacks
from segmentation import segment_scene_colorful
from detection import detect_boxes_aruco
from aruco_detection_configs import aruco_dict, aruco_detection_params, retry_rejected_params


def show(image):
    cv2.namedWindow('show', cv2.WINDOW_NORMAL)
    cv2.imshow('show', image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def get_color_range(image):
    roi = cv2.selectROI(image, showCrosshair=False)
    cv2.destroyAllWindows()
    x, y, w, h = roi

    sub_image = image[y: y + h, x: x + w]
    min_colors = sub_image.min(axis=(0, 1))
    max_colors = sub_image.max(axis=(0, 1))

    return min_colors, max_colors


def stream_table_frame(camera, view, K, D, aruco_size, save_folder=None):
    def calibrate_and_draw_table_frame(image, key):
        camera2table, _ = calibrate_table(image, view, K, D, aruco_size)
        table_detected = camera2table is not None
        if table_detected != calibrate_and_draw_table_frame.table_detected:
            if table_detected:
                print("Table detected")
            else:
                print("Could not detect table")
            calibrate_and_draw_table_frame.table_detected = table_detected
        if not table_detected:
            return
        rvec, _ = cv2.Rodrigues(camera2table[0:3, 0:3])
        tvec = camera2table[0:3, 3]
        cv2.drawFrameAxes(image, K, D, rvec, tvec, 0.1)
    calibrate_and_draw_table_frame.table_detected = None

    if save_folder is not None:
        save_callback = StreamCallbacks.get_save_by_key_callback(save_folder)
    else:
        save_callback = lambda image, key: None
    stream(camera, [save_callback, calibrate_and_draw_table_frame], "stream table frame")


def stream_segmented_scene(camera, view, save_folder=None):
    def segment_and_show_scene(image, key):
        segmentation, (num_red, num_blue) = segment_scene_colorful(image, view)
        if num_red != segment_and_show_scene.num_red or \
                num_blue != segment_and_show_scene.num_blue:
            print(f"Segmented {num_red} red, {num_blue} blue boxes")
            segment_and_show_scene.num_red = num_red
            segment_and_show_scene.num_blue = num_blue
        np.copyto(image, segmentation)
    segment_and_show_scene.num_red = -1
    segment_and_show_scene.num_blue = -1

    if save_folder is not None:
        save_callback = StreamCallbacks.get_save_by_key_callback(save_folder)
    else:
        save_callback = lambda image, key: None
    stream(camera, [save_callback, segment_and_show_scene], "stream segmented scene")


def stream_aruco_detected_on_boxes(camera, view, K, D, aruco_size, save_folder=None):
    def detect_and_draw_aruco_on_boxes(image, key):
        arucos = detect_boxes_aruco(image, view, K, D, aruco_size)
        if arucos.n != detect_and_draw_aruco_on_boxes.number_of_boxes:
            print(f"Number of boxes: {arucos.n}")
            detect_and_draw_aruco_on_boxes.number_of_boxes = arucos.n
        draw_aruco(image, arucos, False, False, K, D)
    detect_and_draw_aruco_on_boxes.number_of_boxes = -1

    if save_folder is not None:
        save_callback = StreamCallbacks.get_save_by_key_callback(save_folder)
    else:
        save_callback = lambda image, key: None
    stream(camera, [save_callback, detect_and_draw_aruco_on_boxes],
        "stream aruco detected on boxes")
