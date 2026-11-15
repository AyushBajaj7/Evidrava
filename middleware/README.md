# Evidrava Middleware

The local middleware is the browser-facing boundary. It forwards only the documented API routes to the local backend, limits JSON request size, permits only the configured frontend origin, handles CORS preflight, and adds a request ID. It accepts only `127.0.0.1` bindings and endpoints, so browser-uploaded workbooks cannot be sent to another machine. The workbook-check route alone receives the larger 32 MB bounded request limit needed for an encoded 20 MB `.xlsx` plus optional local inputs; all other POST routes retain the smaller limit.

Run it after the backend:

```powershell
.\.venv-pilot\Scripts\python.exe -m middleware --host 127.0.0.1 --port 8001 --backend-url http://127.0.0.1:8002 --frontend-origin http://127.0.0.1:5173
```

It is a local development boundary, not an internet-facing production gateway.
