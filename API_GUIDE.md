# AI-Book Application API Guide

## 📌 App Overview
This application is a FastAPI-based backend titled **"PDF to JSON with OpenAI"**. It focuses on helping students and users manage textbooks and reading materials by:
1. **Syllabus & PDF Processing:** Parsing university syllabus PDFs to automatically extract book requirements, reading schedules, and providing textbook rental timing recommendations.
2. **Provider & Pricing Aggregation:** Searching across numerous book providers (Open Library, Google Books, eCampus, WorldCat, Internet Archive, HathiTrust, etc.) to fetch details, check availability, and find the lowest-cost or most accessible option.
3. **AI Study Assistant:** Using OpenAI to generate personalized study plans and textbook access strategies based on user context.

---

## 🚀 Quick Start
To run this application, ensure you have set up your `.env` file since several endpoints heavily rely on external APIs (specifically OpenAI).

**Required Environment Variables (`.env`)**:
- `OPENAI_API_KEY` (MUST be provided to start the app)
- Optional provider keys: `GOOGLE_BOOKS_API_KEY`, `WORLDCAT_API_KEY`, `OPENALEX_API_KEY`, `PRIMO_API_KEY`, etc.

**Run the Server**:
```bash
uvicorn app:app --reload --port 8000
```
Interactive API documentation will then be available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 📡 Endpoints Overview

### 1. Document & AI Analysis
These endpoints handle file uploads and utilize OpenAI to extract actionable insights.

- **`POST /parse-pdf`**
  - **What it does:** Upload a PDF (like a syllabus), extracts text, sends it to OpenAI, and returns a structured JSON array of books.
  - **Input:** `multipart/form-data` with a `file` field.
  
- **`POST /analyze-syllabus`**
  - **What it does:** Similar to `/parse-pdf` but goes further. It extracts both books and schedule information, returning rental timing recommendations per book (e.g., when to rent a book based on the syllabus timeline).
  - **Input:** `multipart/form-data` with a `file` field.

- **`POST /chat-study-plan`**
  - **What it does:** Generates a personalized study and textbook access strategy from the previously analyzed syllabus data and user context.
  - **Input:** JSON payload (context, scheduling details).

### 2. Book Lookup & Searching
These endpoints allow you to search for books by title across various literature and commercial databases.

- **`GET /book`**
  - **What it does:** Searches for books by name using the OpenAlex API. Returns a localized list of works with their IDs, authors, and DOIs.
  - **Params:** `title` (required), `per_page` (optional).

- **`GET /search_books`**
  - **What it does:** Searches for books by name using the Open Library Search API.
  - **Params:** `q` (search query), `limit`, `fields`, `lang`, `sort`.

- **`GET /search_ecampus`**
  - **What it does:** Searches for a book by title, grabs its ISBN from Open Library, and directly fetches its pricing from eCampus.

### 3. Pricing, Aggregation & Compare
These endpoints are designed to save money and find where a book is physically or digitally available.

- **`GET /pricing/{isbn}`**
  - **What it does:** Retrieves direct eCampus pricing (New, Used, Rental) for a specific ISBN.

- **`GET /pricing_openlibrary/{isbn}`**
  - **What it does:** Retrieves Open Library availability information (whether a digital copy can be borrowed) for a given ISBN.

- **`GET /compare_book_providers`**
  - **What it does:** The ultimate aggregation endpoint. It searches multiple provider APIs in parallel, attaches source metadata to the first candidate from each provider, fetches their specific details, and returns the lowest-cost / best provider logic.

### 4. System & Documentation
- **`GET /`** - Root status endpoint.
- **`GET /docs`** - Interactive Swagger UI.
- **`GET /openapi.json`** - OpenAPI raw JSON schema.
