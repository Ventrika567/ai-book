import os

from dotenv import load_dotenv

load_dotenv()

# ---------- LLM ----------
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o")
EXTRACT_SYLLABUS_MODEL = os.getenv("EXTRACT_SYLLABUS_MODEL", "gpt-4o-mini")

# ---------- Provider URLs ----------
OPEN_LIBRARY_SEARCH_URL = "https://openlibrary.org/search.json"
OPEN_LIBRARY_WORK_URL = "https://openlibrary.org"
OPEN_LIBRARY_BOOK_URL = "https://openlibrary.org/isbn"
GOOGLE_BOOKS_VOLUMES_URL = "https://www.googleapis.com/books/v1/volumes"
INTERNET_ARCHIVE_ADVANCED_SEARCH_URL = "https://archive.org/advancedsearch.php"
HATHITRUST_ISBN_API_URL = "https://catalog.hathitrust.org/api/volumes/brief/isbn"
WORLDCAT_SEARCH_V2_URL = "https://americas.discovery.api.oclc.org/worldcat/search/v2/bibs"
DOAB_SEARCH_URL = "https://directory.doabooks.org/rest/search"
OAPEN_SEARCH_URL = "https://library.oapen.org/rest/search"
OPENALEX_BASE_URL = "https://api.openalex.org/works"
ECAMPUS_URL = "https://api.ecampus.com/service.asmx"
ECAMPUS_SOAP_ACTION = "http://www.etextbooksnow.com/GetTextbookXInfo"

# ---------- Provider API Keys ----------
GOOGLE_BOOKS_API_KEY = os.getenv("GOOGLE_BOOKS_API_KEY", "")
WORLDCAT_API_KEY = os.getenv("WORLDCAT_API_KEY", "")
PRIMO_API_KEY = os.getenv("PRIMO_API_KEY", "")
PRIMO_BASE_URL = os.getenv("PRIMO_BASE_URL", "")
PRIMO_VIEW = os.getenv("PRIMO_VIEW", "")
EDS_PROFILE = os.getenv("EDS_PROFILE", "")
EDS_API_TOKEN = os.getenv("EDS_API_TOKEN", "")
EDS_BASE_URL = os.getenv("EDS_BASE_URL", "https://eds-api.ebscohost.com/edsapi/publication/search")
OPENALEX_API_KEY = os.getenv("OPENALEX_API_KEY")
