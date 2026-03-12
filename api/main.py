from fastapi import FastAPI

from api.routers import health


app = FastAPI(title="JMIE API", version="0.1.0")

# include the health check router; more routes will be added in later sprints
app.include_router(health.router)
