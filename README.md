# Progress HTTP Server

A simple HTTP server with download progress bar and upload function. It's usefull for serving tools inside a directory on a server. It's a better alternative for `python -m http.sever 80`. Directory listing only from server-side.

## Installation

Install using pip:

```bash
pip install .
```

## Usage

### Start server

```bash
armory-http [HTTP-PORT]
```

### Download a file to a client

```bash
curl [SERVER-IP]:[HTTP-PORT]/[FILENAME-ON-SERVER] -o [FILENAME-ON-CLIENT]
```

### Upload a file from a client

```bash
curl -F "file=@[FILENAME-ON-CLIENT]" [SERVER-IP]:[HTTP-PORT]/upload
```

