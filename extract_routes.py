import os
os.environ["OPENAI_API_KEY"] = "fake_key_for_testing"

from app import app
import json

routes = []
for r in getattr(app, 'routes', []):
    if hasattr(r, 'methods'):
        doc = getattr(r.endpoint, '__doc__', None)
        routes.append({
            "path": r.path,
            "methods": list(r.methods),
            "name": r.name,
            "docstring": doc.strip() if doc else "(No docstring)",
        })

with open('routes.json', 'w', encoding='utf-8') as f:
    json.dump(routes, f, indent=2)
