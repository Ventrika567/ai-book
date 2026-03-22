from typing import Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.step1_extract import router as step1_router
from routes.step2_query import router as step2_router
from routes.step3_select import router as step3_router
from routes.step4_finalize import router as step4_router
from routes.chat import router as chat_router

app = FastAPI(title="SmartRent - Textbook Rental Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:8000",
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register route modules
app.include_router(step1_router)
app.include_router(step2_router)
app.include_router(step3_router)
app.include_router(step4_router)
app.include_router(chat_router)


@app.get("/")
def root() -> Dict[str, str]:
    return {
        "message": "SmartRent API is running. Endpoints: /extract-syllabus, /query-providers, /select-best-provider, /finalize-results, /chat-study-plan"
    }
