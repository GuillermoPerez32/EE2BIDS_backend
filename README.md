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

✅ Fix calls to sio.emit() methods so that they emit the update to a single user

✅ Convert the application to asgi so that it accepts more than one connection at the same time

✅ Fix loris library so it can accept more than one connection

✅ Fix [BIDS.py](./libs/BIDS.py) so it can accept more than one connection

🟧 Fix [EDF.py](./libs/EDF.py) so it can accept more than one connection

🟧 Fix [iEEG.py](./libs/iEEG.py) so it can accept more than one connection

🟧 Fix [Modifier.py](./libs/Modifier.py) so it can accept more than one connection

🟧 Change eventlet to asyncio for better performance

🟧 Send compressed file in the tarfile_bids endpoint's response

🟧 Notify errors to the client for a better UX, for example in the connection to loris

❌ The app runs async but many endpoints works locally