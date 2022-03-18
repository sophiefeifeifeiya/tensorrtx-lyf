"""
An example that uses TensorRT's Python api to make inferences.
"""
# -*- coding: utf-8 -*-
import argparse
import ctypes
import os
import shutil
import random
import sys
import threading
import time
import cv2
import numpy as np
import pycuda.autoinit
import pycuda.driver as cuda
import tensorrt as trt
from threading import Thread


CONF_THRESH = 0.5
IOU_THRESHOLD = 0.4




def _argparse():
    parser = argparse.ArgumentParser(description="This is description!")
    parser.add_argument('--ip', action='store', required=True, dest='ip', help='ip')
    return parser.parse_args()


def import_the_engine(engine_file_path):
    ctx = cuda.Device(0).make_context()
    stream = cuda.Stream()
    TRT_LOGGER = trt.Logger(trt.Logger.INFO)
    runtime = trt.Runtime(TRT_LOGGER)

    # Deserialize the engine from file
    with open(engine_file_path, "rb") as f:
        engine = runtime.deserialize_cuda_engine(f.read())
    context = engine.create_execution_context()

    host_inputs = []
    cuda_inputs = []
    host_outputs = []
    cuda_outputs = []
    bindings = []
    for binding in engine:
        print('binding:', binding, engine.get_binding_shape(binding))
        size = trt.volume(engine.get_binding_shape(binding)) * engine.max_batch_size
        dtype = trt.nptype(engine.get_binding_dtype(binding))
        # Allocate host and device buffers
        host_mem = cuda.pagelocked_empty(size, dtype)
        cuda_mem = cuda.mem_alloc(host_mem.nbytes)
        # Append the device buffer to device bindings.
        bindings.append(int(cuda_mem))
        # Append to the appropriate list.
        if engine.binding_is_input(binding):
            input_w = engine.get_binding_shape(binding)[-1]
            input_h = engine.get_binding_shape(binding)[-2]
            host_inputs.append(host_mem)
            cuda_inputs.append(cuda_mem)
        else:
            host_outputs.append(host_mem)
            cuda_outputs.append(cuda_mem)
    return engine.max_batch_size


def get_img_path_batches(batch_size, img_dir):
    ret = []
    batch = []
    for root, dirs, files in os.walk(img_dir):
        for name in files:
            if len(batch) == batch_size:
                ret.append(batch)
                batch = []
            batch.append(os.path.join(root, name))
    if len(batch) > 0:
        ret.append(batch)
    return ret

def export_label_location():

    # Make self the active context, pushing it on top of the context stack.
    self.ctx.push()
    # Restore
    stream = self.stream
    context = self.context
    engine = self.engine
    host_inputs = self.host_inputs
    cuda_inputs = self.cuda_inputs
    host_outputs = self.host_outputs
    cuda_outputs = self.cuda_outputs
    bindings = self.bindings
    # Do image preprocess
    # batch_image_raw = []
    batch_origin_h = []
    batch_origin_w = []
    batch_input_image = np.empty(shape=[self.batch_size, 3, self.input_h, self.input_w])
    for i, image_raw in enumerate(raw_image_generator):
        input_image, image_raw, origin_h, origin_w = self.preprocess_image(image_raw)
        # batch_image_raw.append(image_raw)
        batch_origin_h.append(origin_h)
        batch_origin_w.append(origin_w)
        np.copyto(batch_input_image[i], input_image)
    batch_input_image = np.ascontiguousarray(batch_input_image)

    # Copy input image to host buffer
    np.copyto(host_inputs[0], batch_input_image.ravel())
    # start = time.time()
    # Transfer input data  to the GPU.
    cuda.memcpy_htod_async(cuda_inputs[0], host_inputs[0], stream)
    # Run inference.
    context.execute_async(batch_size=self.batch_size, bindings=bindings, stream_handle=stream.handle)
    # Transfer predictions back from the GPU.
    cuda.memcpy_dtoh_async(host_outputs[0], cuda_outputs[0], stream)
    # Synchronize the stream
    stream.synchronize()
    # end = time.time()
    # Remove any context from the top of the context stack, deactivating it.
    self.ctx.pop()
    # Here we use the first row of output in that batch_size = 1
    output = host_outputs[0]
    # Do postprocess

    if image_path_batch:
        filename = "{}.txt".format(os.path.basename(image_path_batch[0]).split(".")[0])
        fo = open(os.path.join('output', filename), "a")
        for i in range(self.batch_size):
            result_boxes, result_scores, result_classid = self.post_process(
                output[i * 6001: (i + 1) * 6001], batch_origin_h[i], batch_origin_w[i]
            )
            # write .txt for label and locations

            for j in range(len(result_boxes)):
                box = result_boxes[j]
                fo.write("{}\t{} {} {} {}\n".format(categories[int(result_classid[j])], box[0], box[1], box[2], box[3]))

if __name__ == '__main__':
    # load custom plugin and engine
    PLUGIN_LIBRARY = "build/libmyplugins.so"
    engine_file_path = "build/yolov5s.engine"

    if len(sys.argv) > 1:
        engine_file_path = sys.argv[1]
    if len(sys.argv) > 2:
        PLUGIN_LIBRARY = sys.argv[2]

    ctypes.CDLL(PLUGIN_LIBRARY)

    # load coco labels

    categories = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
                  "traffic light",
                  "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow",
                  "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase",
                  "frisbee",
                  "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
                  "surfboard",
                  "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple",
                  "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
                  "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard",
                  "cell phone",
                  "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors",
                  "teddy bear",
                  "hair drier", "toothbrush"]

    if os.path.exists('output/'):
        shutil.rmtree('output/')

    os.makedirs('output/')

    # a YoLov5TRT instance
    batch_size=import_the_engine(engine_file_path)
    try:
        print('batch size is', batch_size)

        image_dir = "samples/"
        image_path_batches = get_img_path_batches(batch_size, image_dir)

        for batch in image_path_batches:
            # create a new thread to do inference
            try:
                thread1 = Thread(target=export_label_location, args=(yolov5_wrapper, batch))
                thread1.start()
                thread1.join()
            except:
                print ("Error: unable to start thread")
            thread1.start()
            thread1.join()
    finally:
        # destroy the instance
        thread1.exit


