# HAI-x Interface



## Getting started
The easiest way to start the interface and its services is docker. Before the docker compose some env variables are needed:

```
export sh_instance_id=<value>
export sh_client_secret=<value>
export sh_client_id=<value>
```

These values can be obtained at the Sentinel Hub (https://www.sentinel-hub.com/). You need an account and a plan (Exploration plan or free trial is enough for Process API and OGC API). Before using it, you must authenticate using your credentials (client ID and secret).

- On the Sentinel Hub website, login with your credentials
- Go to your account settings
- Under OAuth clients, click on 'create new'
- Enter a client name and create it
- Note the client ID and client secret for later use

Next, docker compose will start everything:
```
docker compose up
```

The interface can also manually be started with 
```
flask --app main.py run --host=0.0.0.0
```

## VRPy API
The service that uses VRPy to create paths which include all areas of interest of one day can be reached under the port <b>10002</b> and the path <b>/routePos</b> with a POST request and the following data.

```
{
    'vc':15, 
    'duration':80, 
    'aois':
    {
        1: 
        {
            'amount': 8, 
            'cords': [[52.362557910099596, 9.738487551966356], [52.36234859447236, 9.737451089478453],[52.361496370609714, 9.737989723527287], [52.361665819938416, 9.739091474990806]]
        },
        2: 
        {
            'amount': 9, 
            'cords': [[52.34614877808775, 9.745042138406237], [52.34439303461969, 9.747285727910029],[52.345808962213, 9.748657840499126]]
        } 
    }
}
```
A more detailed description of this service api can be found under <b>services/cvrp_with_vrpy</b>.

## Creating AoIs with APA
The AoIs from APA service uses the port <b>10003</b> and the route is <b>/api/get_aois</b>. The POST request should send data like

```
{
  "start": "2025-01-01",
  "stop": "2025-01-31",
  "day": null,
  "resolution_in_m": 10,
  "max_cloud_coverage": 0.5,
  "lake_query": "Maschsee, Hannover, Germany",
  "copernicus_data_service": "ALL-BANDS-TRUE-COLOR",
  "n_areas": 20
}
```

A more detailed description of this service API can be found under <b>services/estimate-weeding-areas-from-apa</b>.

### Funding
The project HAI-x was funded by the BMBF und the founding number 01IW23003.
