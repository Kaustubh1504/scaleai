import json

from podium.board import build_board

if __name__ == "__main__":
    print(json.dumps(build_board(), indent=2))
