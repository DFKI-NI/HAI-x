# HAI-x Interface



## Getting started
The easiest way to start the interface and its services is docker. Before the docker compose some env variables are needed:

```
export sh_instance_id=2910562c-acbe-4eac-acf8-b5db98fe1c56
export sh_client_secret=MAVj8DSjSwqihwHvxPNTqKLpoWRvkk5U
export sh_client_id=sh-9af77968-b046-4238-a15c-9fa57c854a47
```

Next, docker compose will start everything:
```
docker compose up
```

The interface can also manually be started with 
```
flask --app main.py run --host=0.0.0.0
```

### Funding
The project HAI-x was funded by the BMBF und the founding number 01IW23003.
