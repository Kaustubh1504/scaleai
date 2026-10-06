import json

from chatpack.builder import build_dataset

if __name__ == "__main__":
    print(json.dumps(build_dataset(), indent=2))
