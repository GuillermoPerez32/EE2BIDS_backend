# EE2BIDS_backend

## Install

### Linux

```bash
python3.8 -m venv venv
source venv/bin/activate
pip install -r requirements.xt
```

## Run App

```bash
uvicorn eeg2bids:app --port 7301
```

## TODO

- [x] fix calls to sio.emit() methods so that they emit the update to a single user
- [x] convert the application to asgi so that it accepts more than one connection at the same time
- [ ] Fix loris library so it can accept more than one connection
