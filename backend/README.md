# Evidrava Backend

This local, standard-library API exposes safe project status, temporary workbook checking, and in-memory candidate-frame operations. It binds only to `127.0.0.1`, does not accept browser-supplied paths, and never writes to the workbook, screening CSV, source packets or project output folders.

Run it from the project root:

```powershell
.\.venv-pilot\Scripts\python.exe -m backend --host 127.0.0.1 --port 8002
```

The supported routes are `GET /health`, `GET /api/v1/project-status`, `GET /api/v1/templates`, `POST /api/v1/workbook/check`, `POST /api/v1/frame/check`, and `POST /api/v1/sample/draw`. Workbook uploads are strict Base64 bytes, limited to 20 MB after decoding, and are checked only in a temporary directory. Optional session-calendar CSV and selection-manifest JSON are validated with the upload but are not retained. Use the middleware rather than exposing this service to a browser directly.
