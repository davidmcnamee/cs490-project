"""
Fetches prices from PriceAPI
"""
import asyncio
import os
import sys
from typing import List

import requests
from async_lru import alru_cache

headers = {"accept": "application/json", "content-type": "application/json"}
params = {"token": os.environ["PRICE_API_TOKEN"]}


class PriceAPIException(Exception):
    """Custom exception for PriceAPI errors"""


async def get_prices(product_category: str) -> List[float]:
    """Returns a list of price for a product, fetched from PriceAPI"""
    payload = {
        "source": "amazon",
        "country": "ca",
        "topic": "search_results",
        "key": "term",
        "values": product_category,
        "max_pages": "1",
        "max_age": "1440",
        "timeout": "5",
    }
    loop = asyncio.get_event_loop()

    def create_job():
        return requests.post(
            "https://api.priceapi.com/v2/jobs",
            headers=headers,
            json=payload,
            params=params,
            timeout=5,
        )

    response = await loop.run_in_executor(None, create_job)
    job = response.json()
    job_id = job["job_id"]

    def get_job_status():
        return requests.get(
            f"https://api.priceapi.com/v2/jobs/{job_id}", params=params, timeout=5
        )

    response = await loop.run_in_executor(None, get_job_status)
    while response.json()["status"] != "finished":
        if response.json()["status"] == "cancelled":
            raise PriceAPIException(
                "An error occurred, the job was cancelled by PriceAPI"
            )
        await asyncio.sleep(1)
        response = await loop.run_in_executor(None, get_job_status)

    def get_job_results():
        return requests.get(
            f"https://api.priceapi.com/v2/jobs/{job_id}/download.json",
            params=params,
            timeout=5,
        )

    response = await loop.run_in_executor(None, get_job_results)
    search_results = response.json()["results"][0]["content"]["search_results"]
    return [(float(r["min_price"]) + float(r["max_price"])) / 2 for r in search_results]


@alru_cache(maxsize=200)
async def get_average_price(product_category: str) -> float:
    """Returns the average price for a product, fetched from PriceAPI"""
    try:
        prices = await get_prices(product_category)
        assert len(prices) > 0, f"No prices found for category {product_category}"
    except Exception as e:
        print(f'failed to fetch prices for {product_category}:', e, file=sys.stderr)
        return 0
    return sum(prices) / len(prices)
