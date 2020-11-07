import asyncio
from collections import namedtuple
from urllib.parse import urlencode
from random import choice
from asyncio import BaseEventLoop, Future

import requests
from requests import Response
from bs4 import BeautifulSoup
import openpyxl

from annotations import url_type, query_str_for_url

# CONSTANTS
HOST = "https://www.betexplorer.com"


async def get_response_from_url(
        url: url_type, parameters: dict = {}
) -> Response:
    """
    Get response by url with parameters(if they are have).

    :url(url_type) -> Url without parameters.
    :parameter(dict) = {} -> Dictionary with parameters that be specified in url.

    :return(Response) -> Response from url with parameters.
    """

    loop = asyncio.get_event_loop()

    user_agent = choice(open('user_agents.txt').readlines()).strip()
    params_for_url: query_str_for_url = f'/?{urlencode(parameters)}' if urlencode(parameters) != '' else ''

    future: Future = loop.run_in_executor(None,
                                          requests.get,
                                          url + params_for_url,
                                          {'headers': {'User-Agent': user_agent}}
                                          )
    response = await future

    return response


async def get_list_of_links_to_matches(url: url_type, parameters: dict = {}) -> list[url_type]:
    """
    Get url and parameters(if they are have) and by this
    arguments get page with matches and return list of link to matches
    """
    page_with_matches: Response = await get_response_from_url(url, parameters)
    bs_page_with_matches: BeautifulSoup = BeautifulSoup(page_with_matches.content, 'lxml')

    list_of_links_to_matches: list[url_type] = [HOST + path.get('href') for path in
                                                bs_page_with_matches.select('.table-main__tt>a')]
    return list_of_links_to_matches


def run():
    # date = input('Введите дату (дд.мм.гггг): ').split('.') # asyncio
    loop: BaseEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    asyncio.run(get_list_of_links_to_matches('https://www.betexplorer.com/results/soccer/?year=2017&month=10&day=1'))
    print(2 + 2)


if __name__ == '__main__':
    run()