# Evidrava Frontend

The frontend is a dependency-free browser console that runs only on `127.0.0.1`. It connects only to the local middleware and does not access project files directly.

Run it after the backend and middleware:

```powershell
.\.venv-pilot\Scripts\python.exe -m frontend --host 127.0.0.1 --port 5173 --api-base http://127.0.0.1:8001
```

Open `http://127.0.0.1:5173`. The console can temporarily check a selected workbook copy, validate pasted candidate-frame text, and return a frozen-protocol selection manifest. It never changes the workbook or issues a research decision.
