from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import pairwise_distances_argmin
from scipy.spatial import ConvexHull
import numpy as np
import rasterio
import cv2

def _cluster_based_on_plant_intensity(path_to_tiff, categories, attempts=10):
    """
    Cluster pixels in a TIFF image based on plant intensity.

    Args:
        path_to_tiff (str): Path to the TIFF image file
        categories (list): List of category names for clustering
        attempts (int, optional): Number of attempts for k-means clustering. Defaults to 10.

    Returns:
        tuple: (ret, label, center) where:
            - ret: Compactness measure
            - label: Labels for each pixel
            - center: Cluster centers

    Note:
        This function uses only the green channel for clustering as it's most 
        relevant for plant intensity detection.
    """
    image = rasterio.open(path_to_tiff)
    img = np.moveaxis(image.read(), 0, 2)

    # cluster according to intensity
    vectorized_img = img.reshape((-1, 3))[..., 1]  # only take green channel
    vectorized_img = np.float32(vectorized_img)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    K = len(categories) # 5  # [none, low, medium, high, vegetation]
    ret, label, center = cv2.kmeans(vectorized_img, K, None, criteria, attempts, cv2.KMEANS_PP_CENTERS)
    #center = np.uint8(center)
    #res = center[label.flatten()]
    #result_image = res.reshape((img.shape[:2]))

    return ret, label, center

def _sort_centers_according_to_category(center, categories):
    """
    Sort cluster centers according to categories.

    Args:
        center (numpy.ndarray): Cluster centers
        categories (list): List of category names

    Returns:
        tuple: (sorted_centers, sorted_center_args) where:
            - sorted_centers: Dictionary mapping categories to center values
            - sorted_center_args: Dictionary mapping categories to center indices
    """
    sorted_center_args = {k: v for k, v, in zip(categories, center.flatten().argsort())}
    sorted_centers = {k: v[0] for k, v in zip(categories, center[list(sorted_center_args.values())])}
    return sorted_centers, sorted_center_args

def _get_lat_lon_from_tiff(path_to_tiff):
    """
    Extract latitude and longitude coordinates from a TIFF image.

    Args:
        path_to_tiff (str): Path to the TIFF image file

    Returns:
        numpy.ndarray: Array of GPS coordinates (longitude, latitude) for each pixel
    """
    image = rasterio.open(path_to_tiff)
    band1 = image.read(1)
    height, width = band1.shape
    cols, rows = np.meshgrid(np.arange(width), np.arange(height))
    xs, ys = rasterio.transform.xy(image.transform, rows, cols)
    lons = np.array(xs)
    lats = np.array(ys)

    gps = np.array(list(zip(lons.ravel(), lats.ravel())))
    return gps

def _convert_intensity_clusters_to_position_clusters(gnss, label, sorted_center_args):
    """
    Convert intensity clusters to position clusters.

    Args:
        gnss (numpy.ndarray): Array of GPS coordinates
        label (numpy.ndarray): Labels for each pixel
        sorted_center_args (dict): Dictionary mapping categories to center indices

    Returns:
        dict: Dictionary mapping categories to positions
    """
    positions_per_category = dict()
    for k, v in sorted_center_args.items():
        positions_per_category[k] = gnss[np.argwhere(v == label)[:, 0]]

    return positions_per_category

def _cluster_regions(positions, n_clusters, random_state=0):
    """
    Cluster positions into regions using K-means.

    Args:
        positions (numpy.ndarray): Array of positions to cluster
        n_clusters (int): Number of clusters to create
        random_state (int, optional): Random state for reproducibility. Defaults to 0.

    Returns:
        tuple: (k_means_cluster_centers, k_means_labels) where:
            - k_means_cluster_centers: Centers of the clusters
            - k_means_labels: Labels for each position
    """
    kmeans = KMeans(n_clusters=n_clusters, random_state=random_state).fit(positions)
    k_means_cluster_centers = kmeans.cluster_centers_
    k_means_labels = pairwise_distances_argmin(positions, k_means_cluster_centers)

    return k_means_cluster_centers, k_means_labels

def _create_ranked_list_of_polygons_from_clustered_regions(positions, k_means_cluster_centers, k_means_labels, n_clusters):
    """
    Create a ranked list of polygons from clustered regions.

    Args:
        positions (numpy.ndarray): Array of positions
        k_means_cluster_centers (numpy.ndarray): Centers of the clusters
        k_means_labels (numpy.ndarray): Labels for each position
        n_clusters (int): Number of clusters

    Returns:
        list: List of ConvexHull objects representing areas, sorted by number of members

    Note:
        The function creates convex hulls around each cluster and sorts them by size.
    """
    members_per_cluster = [positions[k_means_labels == k, :].shape[0] for k in range(n_clusters)]
    sorted_list_of_clusters = np.argsort(members_per_cluster)
    list_of_areas = list()
    for k in sorted_list_of_clusters:
        my_members = k_means_labels == k
        member_positions = positions[my_members, :]
        hull = ConvexHull(member_positions)
        list_of_areas.append(hull)

    #[ConvexHull(positions[k_means_labels == k, :]) for k in range(n_clusters) if len(positions[k_means_labels == k, :]) > 2]

    return list_of_areas

def estimate_areas_of_interest(path_to_tiff, relevant_categories, n_areas, categories=['none', 'low', 'medium', 'high', 'vegetation']):
    """
    Estimate areas of interest from a TIFF image based on plant intensity.

    Args:
        path_to_tiff (str): Path to the TIFF image file
        relevant_categories (list): List of categories to consider as relevant
        n_areas (int): Number of areas to identify
        categories (list, optional): List of all possible categories. 
            Defaults to ['none', 'low', 'medium', 'high', 'vegetation'].

    Returns:
        list: List of ConvexHull objects representing areas of interest

    Note:
        This is the main function that orchestrates the entire process of 
        identifying areas of interest based on plant intensity in the image.
    """
    ret, label, center =_cluster_based_on_plant_intensity(path_to_tiff, categories)

    sorted_centers, sorted_center_args = _sort_centers_according_to_category(center, categories)

    gnss = _get_lat_lon_from_tiff(path_to_tiff)
    positions_per_category = _convert_intensity_clusters_to_position_clusters(gnss, label, sorted_center_args)

    filtered_positions = [p for c, p in positions_per_category.items() if c in relevant_categories]
    filtered_positions = np.vstack(filtered_positions)

    k_means_cluster_centers, k_means_labels = _cluster_regions(filtered_positions, n_areas)

    list_of_areas = _create_ranked_list_of_polygons_from_clustered_regions(filtered_positions, k_means_cluster_centers, k_means_labels, n_areas)

    return list_of_areas

# Potential optimizations:
# 1. The function _get_lat_lon_from_tiff could be optimized by using vectorized operations
#    instead of creating meshgrids and converting to lists.
# 2. In _cluster_based_on_plant_intensity, we could consider using more efficient clustering
#    algorithms for large images, or implement downsampling for initial clustering.
# 3. Memory usage could be optimized in _convert_intensity_clusters_to_position_clusters
#    by using more efficient data structures or processing in chunks.
# 4. The ConvexHull calculation in _create_ranked_list_of_polygons_from_clustered_regions
#    could be expensive for large clusters - consider simplifying or approximating for speed.

if __name__ == "__main__":
    # Simple test to demonstrate the functionality
    import matplotlib.pyplot as plt
    import os

    # Test with a sample TIFF file
    # Replace with an actual path to a test TIFF file
    test_tiff_path = "path/to/test/image.tiff"
    test_tiff_path = "/home/cmanss/Schreibtisch/interface/ai/estimate-weeding-areas-from-ndvi/estimate-weeding-areas-from-apa/images/maschsee/cropped/2025-01-08.tiff"

    # Skip test if file doesn't exist
    if os.path.exists(test_tiff_path):
        # Define test parameters
        relevant_cats = ['medium', 'high']
        num_areas = 3

        # Run the main function
        areas = estimate_areas_of_interest(
            test_tiff_path, 
            relevant_cats, 
            num_areas
        )

        # Print results
        print(f"Found {len(areas)} areas of interest")
        for i, area in enumerate(areas):
            print(f"Area {i+1}: {area.volume} square units, {len(area.vertices)} vertices")

        # Optional: Visualize the first area if matplotlib is available
        try:
            plt.figure(figsize=(10, 10))
            for i, area in enumerate(areas):
                hull_points = area.points[area.vertices]
                plt.plot(hull_points[:, 0], hull_points[:, 1], 'o-', label=f"Area {i+1}")
            plt.legend()
            plt.title("Areas of Interest")
            plt.xlabel("Longitude")
            plt.ylabel("Latitude")
            plt.show()
        except Exception as e:
            print(f"Visualization failed: {e}")
    else:
        print(f"Test file {test_tiff_path} not found. Skipping test.")
        print("To run a real test, replace 'test_tiff_path' with an actual TIFF file path.")
