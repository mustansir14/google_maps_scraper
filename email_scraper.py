import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    format="%(asctime)s %(message)s", datefmt="%m/%d/%Y %H:%M:%S", level=logging.INFO
)


class EmailScraper:
    def __init__(self, get_only_one: bool = True, page_limit: int = None) -> None:
        self.page_limit = page_limit
        self.get_only_one = get_only_one

    def search_for_emails(self, soup: BeautifulSoup, emails_found=None) -> List[str]:
        if emails_found is None:
            emails_found = []

        regex = "^[a-z0-9]+[\._]?[a-z0-9]+[@]\w+[.]\w{2,3}$"
        try:
            for word in soup.text.split():
                word = word.strip(".,?-/()|:;")
                if re.search(regex, word) and word not in emails_found:
                    emails_found.append(word)
                    if self.get_only_one:
                        return emails_found
        except:
            pass
        return emails_found

    def request_and_make_soup(self, url: str) -> BeautifulSoup:
        res = requests.get(url, timeout=10)
        return BeautifulSoup(res.content, "html.parser")

    def get_contact_url_at_top(self, urls: List[str]) -> List[str]:
        for index, url in enumerate(urls):
            if "contact" in url:
                return [url] + urls[:index] + urls[index + 1 :]
        return urls

    def scrape_url(self, url: str) -> List[str]:
        if type(url) != str:
            logging.error(f"Invalid URL: " + str(url))
            return []
        url = url.rstrip("/")
        try:
            domain = url.split("://www.")[1]
        except:
            try:
                domain = url.split("://")[1]
            except:
                try:
                    domain = url.split("www.")[1]
                    url = "http://" + url
                except:
                    domain = url
                    url = "https://" + domain
        url = url.rstrip("/") + "/"
        logging.info(f"Searching on " + url)
        try:
            soup = self.request_and_make_soup(url)
        except:
            return []
        emails_found = self.search_for_emails(soup)
        if self.get_only_one and emails_found:
            return emails_found
        links = []
        for link in soup.find_all("a"):
            try:
                links.append(link["href"])
            except:
                pass
        links = self.get_contact_url_at_top(links)
        links_done = [url.split("://")[1]]
        slash_count = len(url.split("/"))
        for link in links:
            if not link:
                continue
            if link.startswith("mailto:"):
                if link.replace("mailto:", "") not in emails_found:
                    emails_found.append(link.replace("mailto:", ""))
            if link[0] == "/":
                link = url + link
            elif "http" not in link:
                continue
            if len(link.split("/")) > slash_count:
                continue
            try:
                link_without_http = link.split("://")[1]
            except:
                continue
            if link_without_http in links_done or domain not in link:
                continue

            logging.info(f"Searching on " + link)

            try:
                soup = self.request_and_make_soup(link)
            except:
                continue
            emails_found = self.search_for_emails(soup, emails_found)
            if self.get_only_one and (emails_found or "contact" in link):
                return emails_found
            links_done.append(link_without_http)
            if self.page_limit and len(links_done) == self.page_limit:
                return emails_found

        return emails_found
