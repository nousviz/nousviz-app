"""B216 (v0.9.10.3): no models for /api/widget-runtime/*.

Both handlers in routes/widget_runtime.py serve raw JavaScript via
`Response(media_type='application/javascript')` — they're file servers,
not JSON endpoints. response_model would force JSON serialization and
break the shim contract. Intentionally left without response_model;
operators reading /docs/api see "JavaScript response" instead of
"no schema declared" because of the explicit response_class on the
route (see routes/widget_runtime.py).
"""
