import requests
import asyncio
import aiohttp
from bs4 import BeautifulSoup

url = "https://tiktok.com/@jayd3nn.x"
url2 = "https://tiktok.com/@terrycrews"

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86-64; rv:90.0) Gecko/20100101 Firefox/90.0"
}


async def fetch():
    async with aiohttp.ClientSession() as session:
        async with session.get(url2, headers=headers) as res:
            return await res.read()


resp = asyncio.run(fetch())
soup = BeautifulSoup(resp, "html.parser")
print(soup.select_one('[title="Followers"]').text)
