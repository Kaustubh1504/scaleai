import json

from batchsched.report import build_schedule

if __name__ == "__main__":
    print(json.dumps(build_schedule(), indent=2))
