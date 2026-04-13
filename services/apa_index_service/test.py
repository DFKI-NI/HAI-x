from main import _get_satellite_data, APARequest

# Global constants
PROFILE_NAME = "cmanss"
DATA_DIR = './images/maschsee/'

if __name__ == '__main__':
    from pydantic import BaseModel
    import json

    client_id = input("Client ID: ")
    client_secret = input("Client Secret: ")
    instance_id = input("Instance ID: ")

    req = {
        #"day": "2024-08-06",
        "day": "2025-08-11",
        "resolution_in_m": 10,
        "max_cloud_coverage": 0.1,
        "lake_query": "Maschsee,Hannover,Germany",
        "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
        "client_id": client_id,
        "client_secret": client_secret,
        "instance_id": instance_id,
        "geojson_file": True
    }

    req = APARequest(**req)

    # Handle single day case
    if req.day is not None:
        day = req.day
        start_time = day + "T00:0:01"
        end_time = day + "T23:59:59"
    else:
        start_time = req.start
        end_time = req.stop

    resolution_in_m = req.resolution_in_m
    max_cloud_coverage = req.max_cloud_coverage
    lake_query = req.lake_query
    copernicus_data_service = req.copernicus_data_service

    time_frame = (start_time, end_time)

    data = _get_satellite_data(
        lake_query,
        time_frame,
        copernicus_data_service,
        resolution_in_m,
        max_cloud_coverage,
        client_id,
        client_secret,
        instance_id
    )
    print(data)

    for k, v in data.items():
        for kk, vv in v.items():
            data[k][kk] = vv.tolist()
    print(data.keys())

    # Persist raw response as JSON for inspection
    out_json_path = f'./Maschsee_{req.day}.json'
    with open(out_json_path, 'w') as f:
        json.dump(data, f)

    # Generate GeoJSON file(s) from the retrieved data
    # Note: build_geojson_files accepts array-like (lists) and converts them to numpy arrays internally
    from src.utils import build_geojson_files

    try:
        # with open(out_json_path, 'r') as f:
        #     data_for_geo = json.load(f)
        filename = build_geojson_files(data, lake_query=lake_query, output_dir=".")
        print(f"GeoJSON file(s) created: {filename}")
    except Exception as e:
        print(f"Failed to create GeoJSON: {e}")
        
    
