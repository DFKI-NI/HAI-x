import json
import os

from shapely.geometry import Point

from src.connectors import ClustersConnectors


def run_test(start, end, mode, clusters, output_file, row_spacing, delete=True):
    input_type = "file" if isinstance(clusters, str) else "dict"
    print(f"Testing mode: {mode}, input_type: {input_type}")

    connector_builder = ClustersConnectors(start, end, row_spacing, mode)

    if input_type == "dict":
        with open(input_file, 'r') as f:
            input_data = json.load(f)
    else:
        input_data = input_file

    try:
        connector_builder.load_data(input_data)
        result = connector_builder.generate_Connectors(output_file)
        print(f"Successfully generated connectors for {mode}")
    except Exception as e:
        print(f"Failed testing {mode}: {e}")
        raise e
    finally:
        if os.path.exists(output_file) and delete:
            os.remove(output_file)


if __name__ == "__main__":
    max_capacity = 100000
    harvester_width = 20
    date = "2025-12-26"
    lake_name = "maschsee"
    start = Point(9.741273233, 52.353144617)
    end = Point(9.741244433, 52.35319485)
    mode = "serpentine"
    row_spacing = 1.0
    input_file = "./test_data/Maschsee_Clustered_Cap100000_20m_2025-12-26.geojson"
    output_file = f"{lake_name}_path1_{mode}_Cap{max_capacity}_{harvester_width}m_{date}.geojson"
    delete = False

    modes = ["unidirectional", "serpentine", "nearest_point"]

    for mode in modes:
        run_test(start, end, mode, input_file, output_file, row_spacing)
    
    # Test with dict input
    with open(input_file, 'r') as f:
        cluster_dict = json.load(f)
    for mode in modes:
        run_test(start, end, mode, cluster_dict, output_file, row_spacing, delete)

    print("All tests passed!")
