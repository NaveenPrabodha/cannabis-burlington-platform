from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.config import get_settings
from app.database import engine
from app.routers import deals, featured, meta, pipeline, products, search, stores

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title="Cannabis Burlington — Market API",
    description=(
        "Public API powering the Burlington Cannabis Price Comparison & Store Discovery "
        "platform. Data sources: HiBuddy.ca (prices, stores), Ontario Cannabis Store "
        "(product catalog, new arrivals), AGCO (licence verification)."
    ),
    version=settings.app_version,
    contact={"name": "Naveen Prabodha"},
    openapi_tags=[
        {"name": "Meta", "description": "Health, categories, brands"},
        {"name": "Stores", "description": "Burlington & 35 km radius cannabis retailers"},
        {"name": "Products", "description": "OCS product catalog with market prices"},
        {"name": "Deals", "description": "Active promotions across stores"},
        {"name": "Search", "description": "Unified search across products + stores"},
        {"name": "Featured", "description": "Homepage curated content"},
        {"name": "Pipeline", "description": "Data-pipeline observability (run history + freshness)"},
    ],
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"detail": "Invalid request", "code": "VALIDATION_ERROR", "errors": exc.errors()},
    )


@app.exception_handler(SQLAlchemyError)
async def db_error_handler(request: Request, exc: SQLAlchemyError):
    return JSONResponse(
        status_code=500,
        content={"detail": "Database error", "code": "DB_ERROR"},
    )


app.include_router(meta.router)
app.include_router(stores.router)
app.include_router(products.router)
app.include_router(deals.router)
app.include_router(search.router)
app.include_router(featured.router)
app.include_router(pipeline.router)


@app.get("/", include_in_schema=False)
async def root():
    return {
        "name": app.title,
        "version": app.version,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }
