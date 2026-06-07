"""Route package — imports from routes.py (single-file) for now.

This package exists so we can incrementally split routes.py into
smaller files. Currently all routes are still in the parent routes.py
and re-exported here.
"""
from app.api.routes_combined import router

__all__ = ["router"]
