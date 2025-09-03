# HAI-x Interface



## Getting started
The easiest way to start the interface and its services is docker. Before the docker compose some env variables are needed:

```
export sh_instance_id=<value>
export sh_client_secret=<value>
export sh_client_id=<value>
```

Next, docker compose will start everything:
```
docker compose up
```

The interface can also manually be started with 
```
flask --app main.py run --host=0.0.0.0
```

## VRPy API
The service that uses VRPy to create paths which include all areas of interest of one day can be reached under the port 10002 with a POST request and the following data.

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

### Funding
The project HAI-x was funded by the BMBF und the founding number 01IW23003.
