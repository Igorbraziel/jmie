from fastapi import FastAPI
import sentry_sdk

from api.routers import health

sentry_sdk.init(
    dsn="https://4bd44d5624114cb4f2c07cbd9a72de5c@o4511055688302592.ingest.us.sentry.io/4511055690661888",
    # Add data like request headers and IP for users,
    # see https://docs.sentry.io/platforms/python/data-management/data-collected/ for more info
    send_default_pii=True,
)

app = FastAPI(title="JMIE API", version="0.1.0")

# include the health check router; more routes will be added in later sprints
app.include_router(health.router)
