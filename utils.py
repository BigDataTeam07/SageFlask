import os

import numpy as np
import tensorflow as tf
from absl import flags

flags.FLAGS.mark_as_parsed()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VOCAB_FILE = os.path.join(BASE_DIR, "static", "vocab.txt")
SAVED_MODEL_DIR = os.path.join(BASE_DIR, "static", "exported_model")
EMOTION_FILE = os.path.join(BASE_DIR, "static", "emotions.txt")
MAX_SEQ_LENGTH = 50
THRESHOLD = 0.35
TOP_K = 2


def convert_sentence_to_features(sentence, tokenizer, max_seq_length):
    tokens = tokenizer.tokenize(sentence)
    if len(tokens) > max_seq_length - 2:
        tokens = tokens[:max_seq_length - 2]
    tokens = ["[CLS]"] + tokens + ["[SEP]"]

    input_ids = tokenizer.convert_tokens_to_ids(tokens)
    input_mask = [1] * len(input_ids)
    segment_ids = [0] * len(tokens)

    while len(input_ids) < max_seq_length:
        input_ids.append(0)
        input_mask.append(0)
        segment_ids.append(0)

    return {
        "input_ids": np.array([input_ids], dtype=np.int64),
        "input_mask": np.array([input_mask], dtype=np.int64),
        "segment_ids": np.array([segment_ids], dtype=np.int64)
    }


def create_example(input_ids, input_mask, segment_ids, num_labels):
    features = {
        "input_ids": tf.train.Feature(int64_list=tf.train.Int64List(value=input_ids)),
        "input_mask": tf.train.Feature(int64_list=tf.train.Int64List(value=input_mask)),
        "segment_ids": tf.train.Feature(int64_list=tf.train.Int64List(value=segment_ids)),
        "label_ids": tf.train.Feature(int64_list=tf.train.Int64List(value=[0] * num_labels))
    }
    example = tf.train.Example(features=tf.train.Features(feature=features))
    return example.SerializeToString()


def load_emotions(emotion_file):
    with open(emotion_file, "r", encoding="utf-8") as f:
        emotions = [line.strip() for line in f if line.strip()]
    return emotions
