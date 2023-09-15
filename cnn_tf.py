import tensorflow as tf
import numpy as np
import pickle, os, cv2
import logging

logging.getLogger('tensorflow').setLevel(logging.INFO)
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

def get_image_size():
    img = cv2.imread('gestures/0/100.jpg', 0)
    return img.shape

def get_num_of_classes():
    return len(os.listdir('gestures/'))

image_x, image_y = get_image_size()

def cnn_model_fn(features, labels, mode):
    input_layer = tf.reshape(features["x"], [-1, image_x, image_y, 1], name="input")

    conv1 = tf.keras.layers.Conv2D(
      filters=16,
      kernel_size=[2, 2],
      padding="same",
      activation=tf.nn.relu,
      name="conv1")(input_layer)
    print("conv1",conv1.shape)
    pool1 = tf.keras.layers.MaxPooling2D(pool_size=[2, 2], strides=2, name="pool1")(conv1)
    print("pool1",pool1.shape)

    conv2 = tf.keras.layers.Conv2D(
      filters=32,
      kernel_size=[5, 5],
      padding="same",
      activation=tf.nn.relu,
      name="conv2")(pool1)
    print("conv2",conv2.shape)
    pool2 = tf.keras.layers.MaxPooling2D(pool_size=[5, 5], strides=5, name="pool2")(conv2)
    print("pool2",pool2.shape)

    conv3 = tf.keras.layers.Conv2D(
      filters=64,
      kernel_size=[5, 5],
      padding="same",
      activation=tf.nn.relu,
      name="conv3")(pool2)
    print("conv3",conv3.shape)

    # Dense Layer
    flat = tf.reshape(conv3, [-1, 5*5*64], name="flat")
    print(flat.shape)
    dense = tf.keras.layers.Dense(units=128, activation=tf.nn.relu, name="dense")(flat)
    print(dense.shape)
    dropout = tf.keras.layers.Dropout(rate=0.2, name="dropout")(dense, training=mode == tf.estimator.ModeKeys.TRAIN)

    # Logits Layer
    num_of_classes = get_num_of_classes()
    logits = tf.keras.layers.Dense(units=num_of_classes, name="logits")(dropout)

    output_class = tf.argmax(input=logits, axis=1, name="output_class")
    output_probab = tf.nn.softmax(logits, name="softmax_tensor")
    predictions = {"classes": tf.argmax(input=logits, axis=1), "probabilities": tf.nn.softmax(logits, name="softmax_tensor")}

    if mode == tf.estimator.ModeKeys.PREDICT:
        return tf.estimator.EstimatorSpec(mode=mode, predictions=predictions)

    # Calculate Loss (for both TRAIN and EVAL modes)
    onehot_labels = tf.one_hot(indices=tf.cast(labels, tf.int32), depth=num_of_classes)
    loss = tf.losses.softmax_cross_entropy(onehot_labels=onehot_labels, logits=logits)

    # Configure the Training Op (for TRAIN mode)
    if mode == tf.estimator.ModeKeys.TRAIN:
        optimizer = tf.optimizers.SGD(learning_rate=1e-2)
        train_op = optimizer.minimize(loss=loss, global_step=tf.compat.v1.train.get_global_step())
        return tf.estimator.EstimatorSpec(mode=mode, loss=loss, train_op=train_op)

    # Add evaluation metrics (for EVAL mode)
    eval_metric_ops = {"accuracy": tf.metrics.accuracy(labels=labels, predictions=predictions["classes"])}
    return tf.estimator.EstimatorSpec(mode=mode, loss=loss, eval_metric_ops=eval_metric_ops)

def main(argv):
    with open("train_images", "rb") as f:
        train_images = np.array(pickle.load(f))
    with open("train_labels", "rb") as f:
        train_labels = np.array(pickle.load(f), dtype=np.int32)

    with open("test_images", "rb") as f:
        test_images = np.array(pickle.load(f))
    with open("test_labels", "rb") as f:
        test_labels = np.array(pickle.load(f), dtype=np.int32)

    classifier = tf.estimator.Estimator(model_fn=cnn_model_fn, model_dir="tmp/cnn_model3")

    tensors_to_log = {"probabilities": "softmax_tensor"}
    logging_hook = tf.estimator.LoggingTensorHook(tensors=tensors_to_log, every_n_iter=50)

    # Define the train_input_fn and eval_input_fn using tf.data.Dataset

def train_input_fn():
    dataset = tf.data.Dataset.from_tensor_slices(({"x": train_images.astype(np.float32) / 255.0}, train_labels))
    dataset = dataset.batch(500).repeat(10).shuffle(buffer_size=10000)
    return dataset

def eval_input_fn():
    dataset = tf.data.Dataset.from_tensor_slices(({"x": test_images.astype(np.float32) / 255.0}, test_labels))
    dataset = dataset.batch(500)
    return dataset



    classifier.train(input_fn=train_input_fn, hooks=[logging_hook])

    test_results = classifier.evaluate(input_fn=eval_input_fn)
    print(test_results)

if __name__ == "__main__":
    main(None)
