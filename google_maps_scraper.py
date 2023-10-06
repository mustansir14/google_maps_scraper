import concurrent.futures
import logging
import os
from dataclasses import dataclass
from typing import List, Tuple

import pandas as pd
import requests
from dotenv import load_dotenv

from email_scraper import EmailScraper

logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %H:%M:%S", level=logging.INFO
)


load_dotenv()


@dataclass
class PlaceRawInfo:
    place_id: str
    address: str
    user_ratings_total: int
    rating: float
    types: list[str]


@dataclass
class PlaceFullInfo:
    place_id: str
    business_profile_url: str
    company_name: str
    business_type: list[str]
    average_rating: float
    address: str
    phone_number: str
    website_url: str
    user_ratings_total: int
    email: str
    first_name: str
    last_name: str


@dataclass
class Response:
    results: List[PlaceFullInfo]
    next_page_token: str | None


class GoogleMapsScraper:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url_search = (
            "https://maps.googleapis.com/maps/api/place/textsearch/json"
        )
        self.base_url_detail = "https://maps.googleapis.com/maps/api/place/details/json"
        self.email_scraper = EmailScraper(True, 20)

    def get(self, url: str, query_params: dict) -> dict:
        query_params["key"] = self.api_key
        return requests.get(url, query_params).json()

    def get_places_raw(
        self, query: str, next_page_token: str = None
    ) -> Tuple[List[PlaceRawInfo], str]:
        """
        Returns a list of places for the given query, and a next_page_token if exists
        """

        query_params = {}
        if next_page_token:
            query_params["pagetoken"] = next_page_token
        else:
            query_params["query"] = query

        logging.info(
            f"Requesting places raw with query {query} and next_page_token {next_page_token}"
        )
        all_locations_list = self.get(self.base_url_search, query_params)
        return [
            PlaceRawInfo(
                resp.get("place_id"),
                resp.get("formatted_address"),
                resp.get("user_ratings_total"),
                resp.get("rating"),
                resp.get("types"),
            )
            for resp in all_locations_list["results"]
        ], all_locations_list.get("next_page_token")

    def get_place_details(self, place: PlaceRawInfo) -> PlaceFullInfo:
        query_params = {
            "place_id": place.place_id,
            "fields": "name,international_phone_number,url,website",
        }

        logging.info(f"Requesting place detail for place id {place.place_id}")
        results = self.get(self.base_url_detail, query_params)["result"]
        email = None
        first_name = None
        last_name = None
        if results.get("website"):
            logging.info(
                f"Scraping email for place id {place.place_id} website {results.get('website')}"
            )
            emails = self.email_scraper.scrape_url(results.get("website"))
            if emails:
                email = emails[0]
                logging.info(f"Found email: {email}")
                before_at = email.split("@")[0]
                if "." in before_at:
                    first_name = before_at.split(".")[0].capitalize()
                    last_name = before_at.split(".")[1].capitalize()
        return PlaceFullInfo(
            business_profile_url=results["url"],
            company_name=results.get("name"),
            business_type=", ".join(place.types) if place.types else None,
            average_rating=place.rating,
            address=place.address,
            user_ratings_total=place.user_ratings_total,
            phone_number=results.get("international_phone_number"),
            website_url=results.get("website"),
            place_id=place.place_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
        )

    def get_full_places(self, query: str, next_page_token: str | None = None) -> Response:
        full_places = []
        places, next_page_token = self.get_places_raw(query, next_page_token)
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_to_place = {
                executor.submit(self.get_place_details, place): place
                for place in places
            }
            for future in concurrent.futures.as_completed(future_to_place):
                full_places.append(future.result())
        return Response(full_places, next_page_token)


if __name__ == "__main__":
    scraper = GoogleMapsScraper(os.getenv("GOOGLE_PLACES_API_KEY"))
    df = pd.DataFrame(scraper.get_full_places("Mortgage Broker Adelaide"))
    df.to_csv("results.csv")
