import json

from turnsmith.export import build_dataset

if __name__ == "__main__":
    print(json.dumps(build_dataset(), indent=2))
