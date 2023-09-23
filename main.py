from fastapi import FastAPI
from google_maps_scraper import GoogleMapsScraper
from dotenv import load_dotenv
import os
load_dotenv()

app = FastAPI()


@app.get("/")
async def get_google_maps_places(query: str):
    scraper = GoogleMapsScraper(os.getenv("GOOGLE_PLACES_API_KEY"))
    return scraper.get_full_places(query)
