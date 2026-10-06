from routedesk.reports import build_report, export_json

if __name__ == "__main__":
    print(export_json(build_report()))
