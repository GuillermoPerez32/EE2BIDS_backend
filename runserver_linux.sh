fuser -k 7301/tcp
uvicorn main:app --port 7301
