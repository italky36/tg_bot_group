#!/usr/bin/env python3
"""Entry point for running the admin panel."""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "admin_panel.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
