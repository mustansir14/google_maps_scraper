import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from google_maps_scraper import GoogleMapsScraper

load_dotenv()

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"])


@app.get("/")
async def get_google_maps_places(query: str):
    scraper = GoogleMapsScraper(os.getenv("GOOGLE_PLACES_API_KEY"))
    return scraper.get_full_places(query)
