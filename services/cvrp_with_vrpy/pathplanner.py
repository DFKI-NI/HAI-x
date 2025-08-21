import networkx
import pandas as pd
import plotly.graph_objects as go
from vrpy import VehicleRoutingProblem
import numpy as np
import geopy.distance
from networkx import Graph, DiGraph, shortest_path
import plotly.express as px
from matplotlib import path


def planning(aoi_dict: dict, vc: int, duration: int):
    vessel_capacity = vc

    areasOfInterest_cords = np.zeros((len(aoi_dict), 3))
    i = 0

    for cords in aoi_dict:
        punkt = np.array(aoi_dict[cords]["cords"])

        x_mitte = punkt[:, 0].mean()
        y_mitte = punkt[:, 1].mean()

        areasOfInterest_cords[i] = np.array([x_mitte, y_mitte, aoi_dict[cords]["amount"]])
        i += 1

    newcords = np.array([
        [52.35319481421753, 9.741068524961092],
        [52.35375288163785, 9.740944334909406],
        [52.354923174878856, 9.740252419024957],
        [52.35601216990911, 9.739320993798955],
        [52.35770249713955, 9.73872665573478],
        [52.35836344085968, 9.737954903401128],
        [52.35889435569331, 9.736517847317502],
        [52.36144590835293, 9.735187239829951],
        [52.36171134804204, 9.736136406481053],
        [52.361995365501336, 9.736120380558818],
        [52.362518252958246, 9.738393785869484],
        [52.36161367655934, 9.738981599734384],
        [52.361648185835286, 9.739504317188478],
        [52.35759845926092, 9.74253466887106],
        [52.357365499776016, 9.742647688861135],
        [52.356373251178255, 9.743438828791655],
        [52.35634736613406, 9.74374963376436],
        [52.3545181179009, 9.745400648693204],
        [52.35403574132127, 9.745047440643674],
        [52.353261022403466, 9.745862423368775],
        [52.353261022403466, 9.746562423368775],
        [52.34839859450956, 9.750271272453712],
        [52.34784003843393, 9.750271272453712],
        [52.34746106110065, 9.751774190015617],
        [52.344011148585295, 9.75426737232507],
        [52.343327511541844, 9.75284234353687],
        [52.34381817005903, 9.752458161034456],
        [52.34378073857038, 9.752279317457125],
        [52.34327490452804, 9.752728082341761],
        [52.342990805740264, 9.751518957467772],
        [52.34315049255071, 9.749434006792855],
        [52.34361358175123, 9.74762061432649],
        [52.34448144012328, 9.745931067726529],
        [52.345667770995355, 9.744848294726213],
        [52.34648725566052, 9.744591105398646],
        [52.34830194094891, 9.744971640283941],
        [52.34957533218151, 9.746027255531429],
        [52.35094080033972, 9.74564581475346],
        [52.35184567068127, 9.744430526592005]
    ])

    maschsee = path.Path(newcords)
    areasOfInterest = []

    G = Graph()

    for nummer in range(len(newcords) - 1):
        distance = geopy.distance.geodesic(newcords[nummer], newcords[nummer + 1]).km
        G.add_edge(nummer, nummer + 1, cost=distance)

    distance = geopy.distance.geodesic(newcords[len(newcords) - 1], newcords[0]).km
    G.add_edge(len(newcords)- 1, 0, cost=distance)

    new_graph_cords = []

    for aoi in areasOfInterest_cords:
        new_id = len(G.nodes)
        contains_any = False
        for cord_i in range(len(newcords)):
            contains = True
            lats = np.linspace(newcords[cord_i, 0], aoi[0], num=10)
            lons = np.linspace(newcords[cord_i, 1], aoi[1], num=10)
            for i in range(len(lats)):
                if not maschsee.contains_point([lats[i], lons[i]]):
                    contains = False

            if contains:
                contains_any = True
                new_graph_cords.append(cord_i)
                distance = geopy.distance.geodesic(newcords[cord_i], aoi[:2]).km
                G.add_edge(cord_i, new_id, cost=distance)


        if contains_any:
            areasOfInterest.append([new_id, float(aoi[2])])
            newcords = np.append(newcords, [aoi[:2]], axis=0)


    G_aoi = DiGraph()


    for area_a in areasOfInterest:
        G_aoi.add_edge("Source", int(area_a[0]), cost=networkx.path_weight(G, shortest_path(G, 0, area_a[0],
                                                                                            weight='cost'),
                                                                       'cost'), time=networkx.path_weight(G, shortest_path(G, 0, area_a[0], weight='cost'), 'cost') * 20)
        G_aoi.add_edge(area_a[0], "Sink", cost=networkx.path_weight(G, shortest_path(G, 0, area_a[0], weight='cost'),
                                                                    'cost'), time=networkx.path_weight(G, shortest_path(G, 0, area_a[0], weight='cost'), 'cost') * 20)
        G_aoi.nodes[area_a[0]]['demand'] = int(area_a[1])
        G_aoi.nodes[area_a[0]]['time'] = int(20)

        for area_b in areasOfInterest:
            G_aoi.add_edge(int(area_a[0]), int(area_b[0]), cost=networkx.path_weight(G, shortest_path(G, area_a[0],
                                                                                                      area_b[0],
                                                                                                      weight='cost'),
                                                                                     'cost'), time=networkx.path_weight(G, shortest_path(G, area_a[0], area_b[0], weight='cost'), 'cost') * 20)

    prob = VehicleRoutingProblem(G_aoi, load_capacity=vessel_capacity)
    prob.duration = duration
    prob.solve(time_limit=60)

    # print(networkx.path_weight(G_aoi, prob.best_routes[1], weight='time'))
    # print(networkx.path_weight(G_aoi, prob.best_routes[2], weight='time'))

    routen = []
    for x in prob.best_routes:
        prob.best_routes[x][0] = 0
        prob.best_routes[x][len(prob.best_routes[x]) - 1] = 0
        routen.append(prob.best_routes[x])

    compl_routes = []
    for route in routen:
        routebuild = []
        for i in range(len(route) - 1):
            routebuild = np.append(routebuild, np.array(shortest_path(G, route[i], route[i+1], weight='cost')))

        compl_routes.append(routebuild)

    cords_np = np.array(newcords)
    fertigen_cords = {}
    route_number = 0
    for draw_route in compl_routes:
        route_number += 1
        draw_route = draw_route.astype(int)

        fertigen_cords[route_number] = cords_np[draw_route].tolist()

    return fertigen_cords


def draw_map(cords_to_draw: np.array, aoi_dict: dict):
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

    fig.show()


