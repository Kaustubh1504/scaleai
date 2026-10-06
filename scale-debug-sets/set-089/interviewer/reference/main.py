import json

from evalboard.report import build_leaderboard

if __name__ == "__main__":
    print(json.dumps(build_leaderboard(), indent=2))
