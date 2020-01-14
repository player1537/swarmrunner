# SwarmRunner

## Getting Started

```console
$ git clone git@github.com:player1537/swarmrunner.git
$ # in a "server" tmux window
$ python3.7 -m swarmrunner server --port 8000
$ # in a "client" tmux window
$ python3.7 -m swarmrunner client listen 127.0.0.1:8000
$ # in a browser
$ xdg-open http://127.0.0.1:8000
```

* `swarmrunner/server.py`
is the server script
that handles the backend API.

* `swarmrunner/client.py`
is the client script
that handles registering with the backend,
listening for incoming scripts,
and executing them.

* `swarmrunner/static/index.html`
is the default page that gets sent.

* `swarmrunner/static/main.js`
is the default JavaScript that gets executed.

* by default, the server writes to `log-server.txt`
and the client writes to `log-client.txt`.
The `--logfile` parameter changes this.

## API

```
GET /
  main index.html page
```

```
GET /clients/
  list of currently connected clients

{
  "clients": [
    {
      "name": "my_name",
      "env": {
        "key1": "val1",
        "key2": "val2"
      }
    }
  ]
}
```

```
POST /register/:name
  register this client with this name
  body of request is a JSON object of environment variables.
```

```
POST /send/:name
  send data to a client connected with the given name.
  the expectation is that this is a shell (bash) script.
```

```
GET /listen/:name
  listen for incoming data on the given name.
  the expectation is that this is a shell (bash) script.
```
