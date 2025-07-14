import json


def load_json_data(json_path):
    with open(json_path) as json_file:
        data = json.load(json_file)

        return data