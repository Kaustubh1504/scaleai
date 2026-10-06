import json

from quotecache.reports import build_report

if __name__ == "__main__":
    print(json.dumps(build_report(), indent=2))
