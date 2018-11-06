# Stupid python path shit.
# Instead just add darknet.py to somewhere in your python path
# OK actually that might not be a great idea, idk, work in progress
# Use at your own risk. or don't, i don't care
import sys
import os
import argparse
import sqlite3 as db


parser = argparse.ArgumentParser(description='Input path to darknet')
parser.add_argument('DATA_PATH', type=str, nargs=1,
                    help='Set path to data folder, containg datasets')
parser.add_argument('DARKNET_PATH', type=str, nargs=1,
                    help='Path to darknet folder')
args = parser.parse_args()
DATA_PATH = args.DATA_PATH[0]
DARKNET_PATH = args.DARKNET_PATH[0]

sys.path.append(os.path.join(DARKNET_PATH, 'python/'))
import darknet as dn


dn.set_gpu(0)
net = dn.load_net(os.path.join(DARKNET_PATH, "cfg/yolo-obj_test.cfg"), os.path.join(DARKNET_PATH,
                                                                                    "backup/yolo-obj_test_6000.weights"), 0)
meta_data_net = dn.load_meta(os.path.join(DARKNET_PATH, "data/obj.data"))


test_images_list_file = open(os.path.join(DATA_PATH, 'tmp', "test.txt"), "r")
image_filepaths = test_images_list_file.readlines()


class Box(object):
    """docstring for Box"""

    def __init__(self, class_name, xmin, xmax, ymin, ymax, confidence=None):
        self.class_name = class_name
        self.xmin = xmin
        self.xmax = xmax
        self.ymin = ymin
        self.ymax = ymax
        self.confidence = confidence


def initialize_database():
    conn = db.connect('detections.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE detections
                         (image_name text, xmin integer, xmax integer, ymin integer, ymax integer, class_name text, confidence real)''')
    return conn


def add_to_db(conn, image_name, xmin, xmax, ymin, ymax, class_name, confidence):
    c = conn.cursor()
    c.execute("INSERT INTO detections (image_name, xmin, xmax, ymin, ymax, class_name, confidence) VALUES (?, ?, ?, ?, ?, ?, ?)"), (
        image_name, xmin, xmax, ymin, ymax, class_name, confidence)


def convert_yolo_format(x_center, y_center, width, height):
    x_min = float(x_center) - float(width) / 2
    x_max = float(x_center) + float(width) / 2
    y_min = float(y_center) - float(height) / 2
    y_max = float(y_center) + float(height) / 2
    return [x_min, x_max, y_min, y_max]


def get_detected_boxes(yolo_output):
    boxes = []
    for detection in yolo_output:
        coordinates = convert_yolo_format(
            detection[2][0], detection[2][1], detection[2][2], detection[2][3])
        boxes.append(Box(detection[0], coordinates[0],
                         coordinates[1], coordinates[2], coordinates[3], confidence=detection[1]))
    return boxes


def get_yolo_detections(image_name, net, meta_data_net, thresh=0.5):
    detections = dn.detect(net, meta_data_net, os.path.join(
        DARKNET_PATH, image_name.strip()), thresh=thresh)
    print(detections)
    return get_detected_boxes(detections)


def write_detections_to_db(image_filepaths, thresh=0.5):
    conn = initialize_database()
    for image in image_filepaths:
        boxes = get_yolo_detections(image, net, meta_data_net, thresh)
        for box in boxes:
            add_to_db(conn, image, box.xmin, box.xmax, box.ymin,
                      box.ymax, box.class_name, box.confidence)
    conn.commit()
    conn.close()


write_detections_to_db(image_filepaths, thresh=0.05)
