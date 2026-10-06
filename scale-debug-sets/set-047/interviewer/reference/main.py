import json

from paycycle.statement import build_statement

if __name__ == "__main__":
    print(json.dumps(build_statement(), indent=2))
