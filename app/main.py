from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.cohorts import router as cohorts_router

from app.routers.analysis import router as analysis_router
from app.routers.hf_merge import router as hf_router

app = FastAPI(
    title="GeoAstro Stat API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://geoastro-stat-mhwild7l9-manuel-dcs-projects.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analysis_router)
app.include_router(hf_router)
app.include_router(cohorts_router)

@app.get("/")
def root():
    return {"message": "GeoAstro Stat API running"}