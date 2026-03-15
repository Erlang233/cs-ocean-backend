from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.graph import router as graph_router
from routers.nodes import router as nodes_router
from routers.scan import router as scan_router
from routers.proposals import router as proposals_router

app = FastAPI(
    title="CS Ocean Learning Graph API",
    description="Backend API for the CS self-learning ocean graph",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://erlang233.github.io",
        "http://localhost:5173",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(graph_router)
app.include_router(nodes_router)
app.include_router(scan_router)
app.include_router(proposals_router)


@app.get("/health")
def health_check():
    return {"status": "ok", "message": "CS Ocean API is running"}
