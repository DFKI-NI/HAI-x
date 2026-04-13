from math import degrees, sqrt

import networkx as nx
import numpy as np
from shapely.geometry import Point, LineString


def build_visibility_graph(polygon, terminals):
    G = nx.Graph()
    vertices = list(polygon.exterior.coords[:-1])
    vertices = [Point(v) for v in vertices] + [Point(t.x, t.y) for t in terminals]

    for i, p1 in enumerate(vertices):
        for j, p2 in enumerate(vertices):
            if i >= j:
                continue
            edge = LineString([p1, p2])
            if polygon.buffer(0).covers(edge):
                G.add_edge(
                    (round(p1.x, 6), round(p1.y, 6)),
                    (round(p2.x, 6), round(p2.y, 6)),
                    weight=edge.length
                )
    return G


def shortest_path_length(polygon, a, b, extra_terminals=[]):
    all_terminals = [a, b] + extra_terminals
    G = build_visibility_graph(polygon, all_terminals)
    a_key = (round(a.x, 6), round(a.y, 6))
    b_key = (round(b.x, 6), round(b.y, 6))

    try:
        length = nx.shortest_path_length(G, a_key, b_key, weight="weight")
        path = nx.shortest_path(G, a_key, b_key, weight="weight")
        # Convert path coordinates back to Points
        path_points = [Point(p) for p in path]
        return length, path_points
    except nx.NetworkXNoPath:
        print(f"No path found between {a_key} and {b_key}")
        return float("inf"), None
    except nx.NodeNotFound as e:
        print(f"Node not found: {e}")
        return float("inf"), None


def analyze_linestring(linestring: LineString) -> dict:
    coords = list(linestring.coords)
    if len(coords) < 2:
        return {
            'total_length': 0.0,
            'num_turns': 0,
            'turns_range': (0, 0),
            'turns_average': 0,
            'mode': 'nearest_point'
        }

    total_length = linestring.length
    segment_lengths = []
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i + 1]
        length = sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        segment_lengths.append(length)

    angles = []
    for i in range(len(coords) - 2):
        p1 = np.array(coords[i])
        p2 = np.array(coords[i + 1])
        p3 = np.array(coords[i + 2])
        v1 = p1 - p2
        v2 = p3 - p2
        dot_product = np.dot(v1, v2)
        mag_v1 = np.linalg.norm(v1)
        mag_v2 = np.linalg.norm(v2)
        if mag_v1 > 0 and mag_v2 > 0:
            cos_angle = dot_product / (mag_v1 * mag_v2)
            cos_angle = max(min(cos_angle, 1.0), -1.0)
            angle_rad = np.arccos(cos_angle)
            angle_deg = degrees(angle_rad)
            angles.append(angle_deg)

    if angles:
        min_angle = min(angles)
        max_angle = max(angles)
        avg_angle = sum(angles) / len(angles)
    else:
        min_angle = max_angle = avg_angle = 0.0

    return {
        'path_length': round(total_length, 2),
        'num_segments': len(segment_lengths),
        'num_turns': len([1 for angle in angles if angle > 0.0]),
        'turns_range': (round(min_angle, 2), round(max_angle, 2)),
        'average_turn': round(avg_angle, 2),
        'mode': 'nearest_point',
    }


def order_points_nearest(points: list[Point]) -> list[Point]:
    if not points:
        return []
    ordered = [points[0]]
    remaining = points[1:]
    while remaining:
        last = ordered[-1]
        dists = [last.distance(p) for p in remaining]
        idx = int(np.argmin(dists))
        ordered.append(remaining.pop(idx))
    return ordered
