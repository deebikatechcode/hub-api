from pydantic import BaseModel, HttpUrl
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
from fastapi import HTTPException
from groqAPI import groqAPI

class SummarizeRequest(BaseModel):
    url: HttpUrl
    allRoutes: int = 0


def fetch_webpage_content(url: str) -> str:
   
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        paragraphs = soup.find_all('p')
        text = ' '.join([para.get_text() for para in paragraphs])
        if not text.strip():
            raise HTTPException(status_code=422, detail="Unable to extract meaningful content from the webpage.")
        return text
    else:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch the webpage.")


async def summarize_text(text_content: str, model: str) -> str:
   
    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes web content."},
        {"role": "user", "content": f"Summarize the following content:\n\n{text_content}"}
    ]
    summary = await groqAPI(messages, model)
    return summary.strip()


def get_internal_links(url: str) -> set:
    """Finds all internal links within a given URL."""
    internal_links = set()
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, "html.parser")
        base_url = "{0.scheme}://{0.netloc}".format(urlparse(url))

        for link in soup.find_all("a", href=True):
            href = link.get("href")
            full_url = urljoin(base_url, href)
            if full_url.startswith(base_url):
                internal_links.add(full_url)
    except Exception as e:
        print(f"Error while crawling {url}: {e}")
    return internal_links