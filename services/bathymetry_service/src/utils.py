import os

import matplotlib.pyplot as plt
import osmnx as ox


def _clean_column_names(gdf):
    columns = gdf.columns
    new_columns = [col.replace(":", "_").replace("-", "_") for col in columns]
    gdf.columns = new_columns
    # for col in columns:
    #     # Replace special characters and truncate to 10 characters
    #     col_clean = col.replace(":", "_").replace("-", "_")
    #     cleaned.append(col_clean[:10])
    return gdf


def get_lake_shp(lake_query: str) -> str:
    """
    Retrieve lake boundaries from OpenStreetMap and save as a shapefile.

    Args:
        lake_query: A string containing the lake name and location (e.g., "Maschsee, Hannover, Germany")

    Returns:
        str: Path to the created shapefile, or None if the lake could not be found

    Raises:
        Various exceptions related to file operations are caught and logged
    """
    try:
        lake_gdf = ox.features_from_place(lake_query, tags={"natural": "water"})
        if lake_gdf.empty:
            lake_gdf = ox.features_from_address(lake_query.split(",")[0],
                                                tags={"natural": "water"})
    except Exception as e:
        print(f"OSM Error for {lake_query}: {e}")
        return None

    if not (lake_gdf is None):
        result = {"name": lake_query.split(",")[0], "found": True, "gdf": lake_gdf}
    else:
        return None

    folder_name = f"{result['name']}"
    if not os.path.exists(folder_name):
        try:
            os.makedirs(folder_name)
        except FileExistsError:
            print(f"One or more directories in '{folder_name}' already exist.")
        except PermissionError:
            print(f"Permission denied: Unable to create '{folder_name}'.")
        except Exception as e:
            print(f"An error occurred: {e}")
    file_name = f"{folder_name}/{result['name']}_boundaries.shp"
    result['gdf'] = _clean_column_names(result['gdf'])
    result['gdf'].to_file(file_name)

    return file_name


def create_depth_visualization(estimated_depth, depth1, depth2, dist1, dist2,
                               current_coord, coord1, coord2, point_id, output_dir):
    """
    Create a single visualization showing spatial distribution with depth information
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # Points data
    points = [current_coord, coord1, coord2]
    depths = [estimated_depth, depth1, depth2]
    distances = [0, dist1, dist2]
    labels = ['Current Point', 'Nearest Point 1', 'Nearest Point 2']
    colors = ['blue', 'green', 'orange']
    markers = ['o', 's', '^']  # Different markers for each point
    sizes = [200, 150, 150]  # Different sizes for emphasis

    # Extract coordinates
    lons = [point[1] for point in points]  # longitude
    lats = [point[0] for point in points]  # latitude

    # Create normalized coordinates for better visualization
    lon_range = max(lons) - min(lons)
    lat_range = max(lats) - min(lats)
    scale = max(lon_range, lat_range, 0.0001)  # avoid division by zero

    # Normalize coordinates
    norm_lons = [(lon - min(lons)) / scale for lon in lons]
    norm_lats = [(lat - min(lats)) / scale for lat in lats]

    # Plot points with size proportional to depth
    for i, (x, y, depth, color, marker, size) in enumerate(zip(norm_lons, norm_lats, depths, colors, markers, sizes)):
        ax.scatter(x, y, s=size, c=color, marker=marker, alpha=1.0, edgecolors='black', linewidth=1)

        # Add depth text inside or near the point
        ax.text(x, y, f'{depth:.1f}m',
                ha='right', va='bottom',
                fontsize=10, fontweight='bold',
                bbox=dict(boxstyle="round,pad=0.3", facecolor='white', alpha=0.5))

    # Draw distance lines with labels
    for i in range(1, 3):  # Draw lines to nearest points
        ax.plot([norm_lons[0], norm_lons[i]], [norm_lats[0], norm_lats[i]],
                'gray', linestyle='--', alpha=0.7, linewidth=1.5)

        # Add distance label at midpoint
        mid_x = (norm_lons[0] + norm_lons[i]) / 2
        mid_y = (norm_lats[0] + norm_lats[i]) / 2
        ax.text(mid_x, mid_y, f'{distances[i]:.0f}m',
                ha='center', va='center',
                bbox=dict(boxstyle="round,pad=0.2", facecolor='lightgray', alpha=0.8),
                fontsize=9)

    # Add point labels
    # for i, (x, y, label) in enumerate(zip(norm_lons, norm_lats, labels)):
    #    offset_x = 0.1
    #    offset_y = 0.1
    #    ax.annotate(label, xy=(x, y), xytext=(x + offset_x, y + offset_y),
    #                arrowprops=dict(arrowstyle='->', color='black', alpha=0.6),
    #                bbox=dict(boxstyle="round,pad=0.3", facecolor='lightyellow', alpha=0.8),
    #                fontsize=9)

    # Add information box
    info_text = f"Current Point Depth: {estimated_depth:.2f}m\n"
    info_text += f"Nearest Point 1: {depth1:.2f}m ({dist1:.0f}m away)\n"
    info_text += f"Nearest Point 2: {depth2:.2f}m ({dist2:.0f}m away)\n"
    info_text += f"Average of Nearby: {(depth1 + depth2) / 2:.2f}m\n"
    info_text += f"Depth Difference: {abs(estimated_depth - (depth1 + depth2) / 2):.2f}m"

    ax.text(0.02, 0.98, info_text, transform=ax.transAxes,
            verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.9),
            fontsize=10, fontweight='bold')

    # Set title and labels
    ax.set_title('Spatial Distribution with Depth Information\n(Coordinates Normalized for Visualization)',
                 fontsize=12, fontweight='bold', pad=20)
    ax.set_xlabel('Longitude (Normalized)')
    ax.set_ylabel('Latitude (Normalized)')

    # Remove axis ticks since coordinates are normalized
    ax.set_xticks([])
    ax.set_yticks([])

    # Add grid
    ax.grid(True, alpha=0.3, linestyle='--')

    # Add legend
    legend_elements = [
        plt.Line2D([0], [0], marker='o', color='w', markerfacecolor='blue', markersize=10, label='Current Point'),
        plt.Line2D([0], [0], marker='s', color='w', markerfacecolor='green', markersize=10, label='Nearest Point 1'),
        plt.Line2D([0], [0], marker='^', color='w', markerfacecolor='orange', markersize=10, label='Nearest Point 2')
    ]
    ax.legend(handles=legend_elements, loc='lower right')

    plt.tight_layout()

    # Save image
    img_filename = f"{point_id}.png"
    img_path = os.path.join(output_dir, img_filename)
    plt.savefig(img_path, dpi=80, bbox_inches='tight')
    plt.close(fig)

    return img_filename
