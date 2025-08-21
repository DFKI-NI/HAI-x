import json
import geopy.distance
import networkx
import plotly.graph_objects as go
from vrpy import VehicleRoutingProblem
import numpy as np
import geopy.distance
from networkx import Graph, DiGraph, shortest_path
import pandas as pd
from utils import variables as var, route_util as util


def pathplanning(coords, volumen):
    G = DiGraph()

    coords = coords[0]
    for x in range(len(coords)):
        for y in range(len(coords)):
            # distance_m[x, y] = geopy.distance.geodesic(coords[x], coords[y]).km

            if x != y:
                if x == 0:
                    G.add_edge("Source", y, cost=geopy.distance.geodesic(coords[x], coords[y]).km)
                elif y == 0:
                    G.add_edge(x, "Sink", cost=geopy.distance.geodesic(coords[x], coords[y]).km)
                else:
                    G.add_edge(x, y, cost=geopy.distance.geodesic(coords[x], coords[y]).km)

    print(G.nodes)
    volumen = volumen[0]
    for i in range(len(volumen) - 1):
        print(i)
        print(volumen[i])
        G.nodes[i+1]["demand"] = int(volumen[i])


    prob = VehicleRoutingProblem(G, load_capacity=15)
    prob.solve()

    print(prob.best_value)
    print(prob.best_routes)
    print(prob.best_routes_load)

    print(prob.best_routes[1][1:len(prob.best_routes[1]) - 1])
    test = coords[prob.best_routes[1][1:len(prob.best_routes[1])-1]]
    test = np.append([coords[0]], test, axis=0)
    test = np.append(test, [coords[0]], axis=0)

    fig = go.Figure(go.Scattermapbox(
            lat=test[:, 0],
            lon=test[:, 1],
            mode='markers+lines'
        ))

    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(mapbox = {
        'center': {'lat': 52.35308906463923, 'lon': 9.745069376309802},
        'zoom': 12}
        )

    fig.show()

# coords_array = np.array([[52.35318135200406, 9.74107460029927],
#         [52.36198399380396, 9.737311890891082],
#         [52.352820788941656, 9.744370399199804],
#         [52.34419835503276, 9.753213602726817],
#         [52.35097691156773, 9.745726538652708]])

# volumen_array = np.array([5, 4, 4, 2])

# pathplanning(coords_array, volumen_array)

def isDrin(area: np.array):
    area = np.array(area)
    graphpoint = np.array([[52.35318588, 9.74102266],
            [52.3433373, 9.75001182],
            [52.34495794, 9.74651078],
            [52.34514278, 9.75307888],
            [52.34600789, 9.75132736],
            [52.34703233, 9.74786158],
            [52.34747625, 9.74471999],
            [52.34928603, 9.7491659],
            [52.34984771, 9.74601405],
            [52.35103883, 9.74611005],
            [52.35230372, 9.74370322],
            [52.35301918, 9.74618459],
            [52.35625129, 9.74283061],
            [52.35707066, 9.74014742],
            [52.36100797, 9.73604811],
            [52.36207759, 9.73843317]])

    lat = area[:, 0]
    lon = area[:, 1]

    for i, gp in enumerate(graphpoint):
        if np.sort(lat)[0] <= gp[0] <= np.sort(lat)[len(lat) - 1]:
            if np.sort(lon)[0] <= gp[1] <= np.sort(lon)[len(lon) - 1]:
                index = i

    return index

def pathplaning2(areasOfInterest: np.array, Amount: np.array):
    aoi_dict = {
        1: {'amount': 8, 'cords': [[52.362557910099596, 9.738487551966356], [52.36234859447236, 9.737451089478453],
                                   [52.361496370609714, 9.737989723527287], [52.361665819938416, 9.739091474990806]]
            },
        2: {'amount': 9, 'cords': [[52.34614877808775, 9.745042138406237], [52.34439303461969, 9.747285727910029],
                                   [52.345808962213, 9.748657840499126]]
            },
        3: {'amount': 5, 'cords': [[52.3501245, 9.7485848], [52.3491809, 9.7481926], [52.3478698, 9.7490756],
                                   [52.3481845, 9.7502284]]
            }
    }

    aoi_pp = np.zeros([len(aoi_dict), 2])
    idx = 0
    for x in range(len(areasOfInterest)):
        aoi_pp[x, 0] = isDrin(areasOfInterest[x])
        aoi_pp[x, 1] = Amount[x]


    areasOfInterest = aoi_pp.astype(int)
    # areasOfInterest = np.array([[1, 8], [2, 5], [3, 8], [4, 8], [14, 5], [15, 6]])
    vessel_capacity = 15

    cords = [[52.35318588, 9.74102266],  # 0
             [52.3433373, 9.75001182],  # 1
             [52.34495794, 9.74651078],  # 2
             [52.34514278, 9.75307888],  # 3
             [52.34600789, 9.75132736],  # 4
             [52.34703233, 9.74786158],  # 5
             [52.34747625, 9.74471999],  # 6
             [52.34928603, 9.7491659],  # 7
             [52.34984771, 9.74601405],  # 8
             [52.35103883, 9.74611005],  # 9
             [52.35230372, 9.74370322],  # 10
             [52.35301918, 9.74618459],  # 11
             [52.35625129, 9.74283061],  # 12
             [52.35707066, 9.74014742],  # 13
             [52.36100797, 9.73604811],  # 14
             [52.36207759, 9.73843317]]  # 15

    adjazenz = [[0, 10],
                [10, 9],
                [9, 8],
                [8, 6],
                [6, 2],
                [2, 1],
                [1, 3],
                [3, 4],
                [4, 7],
                [7, 11],
                [11, 12],
                [12, 15],
                [15, 14],
                [14, 13],
                [13, 0],
                [5, 8],
                [5, 6],
                [5, 2],
                [5, 1],
                [5, 4],
                [9, 7],
                [13, 15],
                [0, 12],
                [0, 11],
                [5, 7]]

    G = Graph()

    for ad in adjazenz:
        G.add_edge(ad[0], ad[1], cost=geopy.distance.geodesic(cords[ad[0]], cords[ad[1]]).km)

    for point in range(len(cords)):
        G.nodes[point]['cords'] = cords[point]

    G_aoi = DiGraph()

    for area_a in areasOfInterest:
        G_aoi.add_edge("Source", int(area_a[0]), cost=networkx.path_weight(G, shortest_path(G, 0, area_a[0],
                                                                                            weight='cost'),
                                                                           'cost'))
        G_aoi.add_edge(area_a[0], "Sink", cost=networkx.path_weight(G, shortest_path(G, 0, area_a[0], weight='cost'),
                                                                    'cost'))
        G_aoi.nodes[area_a[0]]['demand'] = int(area_a[1])

        for area_b in areasOfInterest:
            G_aoi.add_edge(int(area_a[0]), int(area_b[0]), cost=networkx.path_weight(G, shortest_path(G, area_a[0],
                                                                                                      area_b[0],
                                                                                                      weight='cost'),
                                                                                     'cost'))

    prob = VehicleRoutingProblem(G_aoi, load_capacity=vessel_capacity)
    prob.solve()

    routen = []
    for x in prob.best_routes:
        prob.best_routes[x][0] = 0
        prob.best_routes[x][len(prob.best_routes[x]) - 1] = 0
        routen.append(prob.best_routes[x])

    compl_routes = []
    for route in routen:
        routebuild = []
        for i in range(len(route) - 1):
            routebuild = np.append(routebuild, np.array(shortest_path(G, route[i], route[i + 1], weight='cost')))

        compl_routes.append(routebuild)

    cords_np = np.array(cords)
    fertigen_cords = {}
    route_number = 0
    for draw_route in compl_routes:
        route_number += 1
        draw_route = draw_route.astype(int)
        fertigen_cords[route_number] = cords_np[draw_route]

    draw_map(fertigen_cords, aoi_pp)

def pathplanning3(date, available_hours, volume):
    cords = get_paths(date, available_hours, volume)
    aoi = [[0,5],
           [0,3]]
    fig = util.create_base_map(date)
    fig = draw_map(fig, cords, aoi, date)
    return fig

def draw_map(fig, cords_to_draw, aoi_to_draw, date):
    fig = util.create_base_map(date)

    cords_np = np.array([[52.35318588, 9.74102266],  # 0
             [52.3433373, 9.75001182],  # 1
             [52.34495794, 9.74651078],  # 2
             [52.34514278, 9.75307888],  # 3
             [52.34600789, 9.75132736],  # 4
             [52.34703233, 9.74786158],  # 5
             [52.34747625, 9.74471999],  # 6
             [52.34928603, 9.7491659],  # 7
             [52.34984771, 9.74601405],  # 8
             [52.35103883, 9.74611005],  # 9
             [52.35230372, 9.74370322],  # 10
             [52.35301918, 9.74618459],  # 11
             [52.35625129, 9.74283061],  # 12
             [52.35707066, 9.74014742],  # 13
             [52.36100797, 9.73604811],  # 14
             [52.36207759, 9.73843317]])  # 15

    for idx in range(len(cords_to_draw)):
        fig.add_scattermapbox(
            lat=cords_to_draw[idx][:, 0],
            lon=cords_to_draw[idx][:, 1],
            mode='markers+lines',
            text=idx
        )

    aoi_to_draw = np.append([[0, 0]], aoi_to_draw, axis=0)
    aoi_to_draw = aoi_to_draw.astype(int)

    fig.add_trace(go.Scattermapbox(
            mode = "markers",
            lat = cords_np[aoi_to_draw[:, 0]][:, 0],
            lon = cords_np[aoi_to_draw[:, 0]][:, 1],
            text = aoi_to_draw[:, 1],
            marker={'color': 'blue'}
        ))

    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(mapbox = {
        'center': {'lat': 52.35308906463923, 'lon': 9.745069376309802},
        'zoom': 13}
        )
    fig.update_layout(
        margin=dict(l=0,r=0,b=0,t=0),
        paper_bgcolor='rgba(0,0,0,0)'
    )

    return fig

def draw_map2(cords_to_draw: np.array, aoi_dict: dict):
    areasOfInterest_cords = np.zeros((len(aoi_dict), 3))
    i = 0

    for cords in aoi_dict:
        punkt = np.array(aoi_dict[cords]["cords"])

        x_mitte = punkt[:, 0].mean()
        y_mitte = punkt[:, 1].mean()

        areasOfInterest_cords[i] = np.array([x_mitte, y_mitte, aoi_dict[cords]["amount"]])
        i += 1

    fig = go.Figure(go.Scattermapbox(
            lat=[],
            lon=[],
            mode='markers+lines'
        ))

    for idx in cords_to_draw:
        fig.add_scattermapbox(
            lat=np.array(cords_to_draw[idx])[:, 0],
            lon=np.array(cords_to_draw[idx])[:, 1],
            mode='markers+lines',
            text=idx
        )

    fig.add_trace(go.Scattermapbox(
            mode = "markers",
            lat = areasOfInterest_cords[:, 0],
            lon = areasOfInterest_cords[:, 1],
            text = areasOfInterest_cords[:, 2],
            marker={'color': 'blue'}
        ))


    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(mapbox = {
        'center': {'lat': 52.35308906463923, 'lon': 9.745069376309802},
        'zoom': 12}
        )

    return fig


def get_paths(date, hours, volume):
    return np.array([[
                [52.35318588, 9.74102266],
                [52.3433373, 9.75001182],
                [52.34495794, 9.74651078],
                [52.34514278, 9.75307888]],
            [
                [52.34600789, 9.75132736],  # 4
                [52.34703233, 9.74786158],  # 5
                [52.34747625, 9.74471999],  # 6
                [52.34928603, 9.7491659]
            ]])
