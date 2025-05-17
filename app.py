import base64
import json

import boto3
import numpy as np
from flask import Flask, request, jsonify

from bert import tokenization
from utils import convert_sentence_to_features, create_example, load_emotions, VOCAB_FILE, EMOTION_FILE, \
    MAX_SEQ_LENGTH, THRESHOLD, TOP_K

app = Flask(__name__)
runtime = boto3.client("sagemaker-runtime", region_name="ap-southeast-1")

# preload tokenizer and labels
tokenizer = tokenization.FullTokenizer(vocab_file=VOCAB_FILE, do_lower_case=False)
emotions = load_emotions(EMOTION_FILE)
num_labels = len(emotions)


@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    sentence = data.get("text", "")
    feats = convert_sentence_to_features(sentence, tokenizer, MAX_SEQ_LENGTH)
    ex = create_example(
        feats["input_ids"][0].tolist(),
        feats["input_mask"][0].tolist(),
        feats["segment_ids"][0].tolist(),
        num_labels
    )
    b64 = base64.b64encode(ex).decode("utf-8")
    payload = {"instances": [{"b64": b64}]}
    resp = runtime.invoke_endpoint(
        EndpointName="emotion-predict-endpoint",
        ContentType="application/json",
        Body=json.dumps(payload)
    )
    result = json.loads(resp["Body"].read())
    probs = np.array(result["predictions"][0])
    output = {emotions[i]: float(probs[i]) for i in range(len(emotions))}
    filtered = {k: v for k, v in output.items() if v >= THRESHOLD}
    sorted_top = dict(sorted(filtered.items(), key=lambda item: item[1], reverse=True)[:TOP_K])
    return jsonify(sorted_top)


@app.route("/", methods=["GET"])
def health():
    return "OK", 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
