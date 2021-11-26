import aiohttp
import demjson
import re
import random
from urllib import parse
from .utils import generate_google_request, parse_data, parse_google_json

LOAD_IMAGE_RPCID = 'HoAMBc'


class GoogleScraper:
    """Google Image Scrapper"""

    def __init__(self, host='https://www.google.com') -> None:
        self.host = host
        self._session = aiohttp.ClientSession(
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36'})

        self.af_data_regex = re.compile(
            r"AF_initDataCallback\({key: 'ds:1'(.|\n)*?}}")
        self.wiz_regex = re.compile(
            r"window.WIZ_global_data = {(.|\n)*?}"
        )

    async def close(self):
        """Closes aiohttp session"""
        await self._session.close()

    async def scrape(self, query: str, amount=100, safe_search=False) -> list:
        """Scrapes image from google"""
        query = parse.quote(query)

        url = '{0}/search?q={1}&tbm=isch'.format(
            self.host, query + '&safe=active' if safe_search else query)

        site = await self._session.get(url)
        if site.status != 200:
            raise Exception('Google is weird today')
        site_data = await site.text()
        site.close()

        wiz_data_result = self.wiz_regex.search(site_data)
        wiz_string = wiz_data_result.group(0).replace(
            'window.WIZ_global_data = ', '') + '}'
        wiz_data = demjson.decode(wiz_string)

        af_data_result = self.af_data_regex.search(site_data)
        af_string = af_data_result.group(0).replace(
            'AF_initDataCallback', '').strip('()')
        af_data = demjson.decode(af_string)

        result = []
        cursor = {}

        for data in af_data['data']:
            if isinstance(data, list):
                if len(data) == 1:
                    if 'b-GRID_STATE0' in data[0]:
                        parse_result, last_cursor = parse_data(data)
                        cursor = last_cursor
                        result = result + parse_result
                        break

        while len(result) < amount:
            if cursor == {}:
                raise Exception('No cursor provided from google.')

            request = generate_google_request(LOAD_IMAGE_RPCID, query, cursor)
            site = await self._session.post(
                self.host + '/_/VisualFrontendUi/data/batchexecute' +
                '?rpcids=' + LOAD_IMAGE_RPCID +
                '&f.sid=' + wiz_data.get('FdrFJe') +
                '&bl=' + wiz_data.get('cfb2h') +
                '&hl=en-US&soc-app=1&soc-platform=1&soc-device=1&_reqid=' +
                str(random.randint(10000, 200000)) + '&rt=c', data={'f.req': request, 'at': wiz_data.get('SNlM0e'), '': ''})
            if site.status != 200:
                raise Exception('Google is weird today')

            site_text = await site.text()
            site.close()
            site_data = site_text[5:].split('\n')[2]
            site_data = parse_google_json(site_data)

            parse_result, last_cursor = parse_data(data)
            cursor = last_cursor
            result = result + parse_result

        return result[:amount]
