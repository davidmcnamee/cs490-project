from async_lru import alru_cache
import os
import requests
import asyncio
from typing import List

headers = {
  "accept": "application/json",
  "content-type": "application/json"
}
params = {
    'token': os.environ['PRICE_API_TOKEN']
}

async def get_prices(product_category: str) -> List[float]:
  payload = {
      'source': 'amazon',
      'country': 'ca',
      'topic': 'search_results',
      'key': 'term',
      'values': product_category,
      'max_pages': '1',
      'max_age': '1440',
      'timeout': '5',
  }
  loop = asyncio.get_event_loop()
  create_job = lambda: requests.post("https://api.priceapi.com/v2/jobs", headers=headers, json=payload, params=params)
  response = await loop.run_in_executor(None, create_job)
  job = response.json()
  job_id = job['job_id']

  get_job_status = lambda: requests.get(f'https://api.priceapi.com/v2/jobs/{job_id}', params=params)
  response = await loop.run_in_executor(None, get_job_status)
  while response.json()['status'] != 'finished':
    if response.json()['status'] == 'cancelled':
      raise Exception('An error occurred, the job was cancelled by PriceAPI')
    await asyncio.sleep(1)
    response = await loop.run_in_executor(None, get_job_status)

  get_job_results = lambda: requests.get(f'https://api.priceapi.com/v2/jobs/{job_id}/download.json', params=params)
  response = await loop.run_in_executor(None, get_job_results)
  search_results = response.json()['results']['content']['search_results']
  return [
      (r['min_price'] + r['max_price']) / 2
      for r in search_results
  ]

@alru_cache(maxsize=200)
async def get_average_price(product_category: str) -> float:
  prices = await get_prices(product_category)
  assert len(prices) > 0, f"No prices found for category {product_category}"
  return sum(prices) / len(prices)
