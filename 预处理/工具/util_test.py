#####################coding=utf-8#########################################################
####################### tfrecords制作工具类 ################################################
####################### created by tengxing on 2017.3 ####################################
####################### github：github.com/tengxing ######################################
###########################################################################################

import tensorflow as tf
import numpy as np
from PIL import Image
import cv2
import os
from datetime import datetime
import sys
reload(sys)
sys.setdefaultencoding('utf8')

cwd = os.getcwd()

#参数设置
#############################################################################################
train_dir = {'test','test1'} #训练图片文件夹
filename='train.tfrecords'    #生成train.tfrecords
output_directory='tmp' #输出文件夹
resize_height=28 #存储图片高度
resize_width=28 #存储图片宽度
###############################################################################################


def _int64_feature(value):
    return tf.train.Feature(int64_list=tf.train.Int64List(value=[value]))


def _bytes_feature(value):
    return tf.train.Feature(bytes_list=tf.train.BytesList(value=[value]))


def load_file(examples_list_file):
    lines = np.genfromtxt(examples_list_file, delimiter=" ", dtype=[('col1', 'S120'), ('col2', 'i8')])
    examples = []
    labels = []
    for example, label in lines:
        examples.append(example)
        labels.append(label)
    return np.asarray(examples), np.asarray(labels), len(lines)


def extract_image(filename,  resize_height, resize_width):
    image = cv2.imread(filename)
    image = cv2.resize(image, (resize_height, resize_width))
    b,g,r = cv2.split(image)
    rgb_image = cv2.merge([r,g,b])
    return rgb_image


def transform2tfrecord(train_dir, file_name, output_directory, resize_height, resize_width):
    if not os.path.exists(output_directory) or os.path.isfile(output_directory):
        os.makedirs(output_directory)
    for index, name in enumerate(train_dir):
        class_path = cwd + "/" + name + "/"
        filename = output_directory+"/"+file_name+('-%.5d' % (index))
        writer = tf.python_io.TFRecordWriter(filename)
        for image_name in os.listdir(class_path):
            image_path = class_path + image_name
            #image = Image.open(image_path)
            #image = image.resize((resize_height, resize_width))
            print index
            image = cv2.imread(image_path)
            image = cv2.resize(image, (resize_height, resize_width))
            b, g, r = cv2.split(image)
            image = cv2.merge([r, g, b])
            image_raw = image.tobytes()  # 将图片转化为原生bytes
            example = tf.train.Example(
                features=tf.train.Features(feature={
                    'image_raw': _bytes_feature(image_raw),
                    'height': _int64_feature(image.shape[0]),
                    'width': _int64_feature(image.shape[1]),
                    'depth': _int64_feature(image.shape[2]),
                    'label': _int64_feature(index)
                })
            )
            writer.write(example.SerializeToString())
        writer.close()


def read_tfrecord(file_dir, filename):

    # 文件夹下所有文件
    wildfiles = file_dir+"/"+filename+"*"
    # 获取文件列表
    files = tf.train.match_filenames_once(wildfiles)

    # 输入文件队列
    filename_queue = tf.train.string_input_producer(files, shuffle=False)

    reader = tf.TFRecordReader()
    _, serialized_example = reader.read(filename_queue)
    features = tf.parse_single_example(
        serialized_example,
        features={
          'image_raw': tf.FixedLenFeature([], tf.string),
          'width': tf.FixedLenFeature([], tf.int64),
          'height': tf.FixedLenFeature([], tf.int64),
          'depth': tf.FixedLenFeature([], tf.int64),
          'label': tf.FixedLenFeature([], tf.int64)
        }
    )

    encoded_image = tf.decode_raw(features['image_raw'], tf.uint8)
    #encoded_image.set_shape([features['height'], features['width'], features['depth']])
    # image
    encoded_image = tf.reshape(encoded_image, [resize_height*resize_width*3])
    # normalize
    image = tf.cast(encoded_image, tf.float32) * (1. / 255) - 0.5
    # label
    label = tf.cast(features['label'], tf.int32)
    return image, label

def disp_tfrecords(file_dir, filename):
    # 文件夹下所有文件
    wildfiles = file_dir + "/" + filename + "*"
    # 获取文件列表
    files = tf.train.match_filenames_once(wildfiles)

    # 输入文件队列
    filename_queue = tf.train.string_input_producer(files, shuffle=False)

    reader = tf.TFRecordReader()
    _, serialized_example = reader.read(filename_queue)
    features = tf.parse_single_example(
        serialized_example,
        features={
            'image_raw': tf.FixedLenFeature([], tf.string),
            'height': tf.FixedLenFeature([], tf.int64),
            'width': tf.FixedLenFeature([], tf.int64),
            'depth': tf.FixedLenFeature([], tf.int64),
            'label': tf.FixedLenFeature([], tf.int64)
        }
    )
    image = tf.decode_raw(features['image_raw'], tf.uint8)
    # print(repr(image))
    height = features['height']
    width = features['width']
    depth = features['depth']
    label = tf.cast(features['label'], tf.int32)
    init_op = tf.initialize_all_variables()
    resultImg = []
    resultLabel = []
    with tf.Session() as sess:
        sess.run(init_op)
        coord = tf.train.Coordinator()
        threads = tf.train.start_queue_runners(sess=sess, coord=coord)
        for i in range(21):
            image_eval = image.eval()
            #print image_eval
            resultLabel.append(label.eval())
            image_eval_reshape = image_eval.reshape([height.eval(), width.eval(), depth.eval()])
            #print image_eval_reshape
            resultImg.append(image_eval_reshape)
            pilimg = Image.fromarray(np.asarray(image_eval_reshape))
            pilimg.show()
        coord.request_stop()
        coord.join(threads)
        sess.close()
    return resultImg, resultLabel

def add_evaluation_step(result_tensor, ground_truth_tensor):
  """Inserts the operations we need to evaluate the accuracy of our results.

  Args:
    result_tensor: The new final node that produces results.
    ground_truth_tensor: The node we feed ground truth data
    into.

  Returns:
    Tuple of (evaluation step, prediction).
  """
  with tf.name_scope('accuracy'):
    with tf.name_scope('correct_prediction'):
      prediction = tf.argmax(result_tensor, 1)
      correct_prediction = tf.equal(
          prediction, tf.argmax(ground_truth_tensor, 1))
    with tf.name_scope('accuracy'):
      evaluation_step = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
  tf.summary.scalar('accuracy', evaluation_step)
  return evaluation_step, prediction


#img, label = disp_tfrecords(output_directory, filename)

transform2tfrecord(train_dir, filename, output_directory, resize_height, resize_width)
img, label = read_tfrecord(output_directory, filename) #读取函数


# Create the model
image_input_ph = tf.placeholder(tf.float32, [None, 2352])
label_input_ph = tf.placeholder(tf.float32, [None, 2])

layer_weights = tf.Variable(tf.truncated_normal([2352, 2], stddev=0.001), name='final_weights')
layer_biases = tf.Variable(tf.zeros([2]), name='final_biases')

logits = tf.matmul(image_input_ph, layer_weights) + layer_biases

final_tensor = tf.nn.softmax(logits, name="final_result")

with tf.name_scope('cross_entropy'):
    cross_entropy = tf.nn.softmax_cross_entropy_with_logits(
        logits=logits, labels=label_input_ph)
    with tf.name_scope('total'):
        cross_entropy_mean = tf.reduce_mean(cross_entropy)

with tf.name_scope('train'):
    train_step = tf.train.GradientDescentOptimizer(0.001).minimize(
        cross_entropy_mean)

# Merge all the summaries and write them out to /tmp/retrain_logs (by default)
merged = tf.summary.merge_all()


# Create the operations we need to evaluate the accuracy of our new layer.
evaluation_step, prediction = add_evaluation_step(final_tensor, label_input_ph)


# 使用shuffle_batch可以随机打乱输入 next_batch挨着往下取
# shuffle_batch才能实现[img,label]的同步,也即特征和label的同步,不然可能输入的特征和label不匹配
# 比如只有这样使用,才能使img和label一一对应,每次提取一个image和对应的label
# shuffle_batch返回的值就是RandomShuffleQueue.dequeue_many()的结果
# Shuffle_batch构建了一个RandomShuffleQueue，并不断地把单个的[img,label],送入队列中
img_batch, label_batch = tf.train.shuffle_batch([img, label],
                                                batch_size=100, capacity=1300,
                                                min_after_dequeue=1000)

# 初始化所有的op
init = tf.global_variables_initializer()

with tf.Session() as sess:
    sess.run(init)
    train_writer = tf.summary.FileWriter('tmp/',
                                         sess.graph)
    # 启动队列
    threads = tf.train.start_queue_runners(sess=sess)
    for i in range(200):
        val, l = sess.run([img_batch, label_batch])
        # l = to_categorical(l, 12)
        #print(val.shape, l)
        labels = []
        for index in l:
            a = np.zeros(2, dtype=np.int32)
            a[index] = 1.0
            labels.append(a)
        #print val.shape,labels
        train_summary, _ = sess.run([merged, train_step],feed_dict={
        image_input_ph: val,
        label_input_ph: labels})
        if (i % 10) == 0:
            train_accuracy, cross_entropy_value = sess.run(
                [evaluation_step, cross_entropy],
                feed_dict={image_input_ph: val,
                           label_input_ph: labels})
            print('%s: Step %d: Train accuracy = %.1f%%' % (datetime.now(), i,
                                                            train_accuracy * 100))
            #print('%s: Step %d: Cross entropy = %f' % (datetime.now(), i,
             #                                          cross_entropy_value))

