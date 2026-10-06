import json

from evalscore.reports import build_report

if __name__ == "__main__":
    report = build_report()
    print(json.dumps({"models": report["models"], "leaderboard": report["leaderboard"]}, indent=2))
