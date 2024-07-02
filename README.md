# RDFAgents
Python implementation of distributed knowledge synchronization - based on agent systems and RDF graphs.

It strongly relies on [SPADE](https://spade-mas.readthedocs.io/en/latest/readme.html) in version `3.2.3` with Python `3.9`.

This project is inspired by an algorithm described in:\
Berger, C., Doherty, P., Rudol, P. et al. RGS: RDF graph synchronization for collaborative robotics. Auton Agent Multi-Agent Syst 37, 47 (2023). https://doi.org/10.1007/s10458-023-09629-2

## Docker guide
Using the provided Dockerfile, the project can be built into a docker image by running the following command:
```bash
docker build --tag rdfagents .
```
and then run:
```bash
docker run -d --name rdfagents -e ADDRESS=username@domain -e PASSWORD=password -p 10000:10000 rdfagents
```
where `username@domain` and `password` are the credentials for the XMPP server.

However, we recommend setting up local XMPP server, which eliminates any external limitations.

### Local XMPP server
An example implementation of a dockerized local XMPP server is [ejabberd](https://github.com/processone/docker-ejabberd/tree/master/ecs).

As it states in documentation, it can be run with:
```bash
docker run --name ejabberd -d -p 5222:5222 ejabberd/ecs
```
Then the initial user needs to be registered:
```bash
docker exec -it ejabberd bin/ejabberdctl register admin localhost password
```
However, due to limitation XMPP protocol and Spade's XMPP client implementation (which we failed to solve), the user must use `localhost` as the domain to connect to local ejabberd.

Because of that, we can't use docker network to connect the two containers, and we are left with `--network host` for RDFAgents:
```bash
docker run -d --name rdfagents --network host -e ADDRESS=admin@localhost -e PASSWORD=password -p 10000:10000 rdfagents
```
This is very limiting as generally `--network host` doesn't work on Windows and MacOS.
There may be some workaround port forwarding to WSL network.
On Windows, it may be possible to use `netsh` for that, but again, we failed to make it work.

That is why, we decided to create a joint container for both ejabberd and RDFAgents.

### Joint container
This approach is against good practices, as Docker containers are single-purpose and should isolate services.
However, it works out of the box on most systems.

We provide `ejabberd.Dockerfile`, which combines ejabberd XMPP server and RDFAgents app into a single container.
It can be built with:
```bash
docker build --tag rdfagentsxmpp -f ejabberd.Dockerfile .
```
and then run:
```bash
docker run -d --name rdfagentsxmpp -p 10000:10000 rdfagentsxmpp
```

## Usage
In all cases, the app should be available at `http://localhost:10000/gui`.

The logs are stored in `{app_dir}/logs` directory.
