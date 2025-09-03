# CVRP with VRPy

## Getting started

Build the docker image with 
```
docker build -t pathplanningvrpy .
```

Start the docker container with
```
docker run -d -p 8002:8002 pathplanningvrpy
```

You can get a path by sending a dictionary to /routePos/. The data should look like the example:
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
