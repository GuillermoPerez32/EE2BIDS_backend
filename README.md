# EE2BIDS_backend

## Install

### Linux

```bash
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Run App

```bash
uvicorn main:app --port 7301
```

## TODO

- [x] Fix calls to sio.emit() methods so that they emit the update to a single user
- [x] Convert the application to asgi so that it accepts more than one connection at the same time
- [x] Fix loris library so it can accept more than one connection
- [ ] Change eventlet to asyncio for better performance
