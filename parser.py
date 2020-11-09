import asyncio
from typing import Any
from collections import namedtuple
from urllib.parse import urlencode
from random import choice
from asyncio import BaseEventLoop, Future

import requests
from requests import Response
from bs4 import BeautifulSoup, Tag
import openpyxl

import make_pattern_xlsx
from annotations import url_type, query_str_for_url, column_name, numeric_str, name

# CONSTANTS
HOST = "https://www.betexplorer.com"


async def get_response_from_url(
        url: url_type, parameters_in_url: dict = {}, **request_parameters
) -> Response:
    """
    Get response by url with parameters(if they are have).

    :param url(url_type) -> Url without parameters.
    :param parameters_in_url(dict) = {} -> Dictionary with parameters that be specified in url.
    :param **request_parameters -> Parameters specified in requests.get method.

    :return(Response) -> Response from url with parameters.
    """

    loop = asyncio.get_event_loop()

    user_agent = choice(open('user_agents.txt').readlines()).strip()
    params_for_url: query_str_for_url = f'/?{urlencode(parameters_in_url)}' if urlencode(
        parameters_in_url) != '' else ''
    request_parameters['headers'] = request_parameters.get('headers', {}) | {'User-Agent': user_agent}
    try:
        future: Future = loop.run_in_executor(None,
                                              requests.get,
                                              **{'url': url + params_for_url} | request_parameters
                                              )
    except TypeError:
        raise TypeError('You have to change the asyncio.run_in_executor function in the base_events.py file. '
                        'See readme.md for details.')
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


async def get_data_about_match(url: url_type):
    """
    This function get content by url from match page and distributes
    information to the keys specified in the make_pattern_xlsx.py module
    in the column variable.

    :param url(url_type) -> link on match page.
    :return namedtuple(data_about_match, link_on_match) -> named tuple which contains data about the match and a link
    """
    match_page: Response = await get_response_from_url(url)
    odds_table: Response = await get_response_from_url(f'https://www.betexplorer.com/match-odds/'
                                                       f'{match_page.url.split("/")[-2]}'
                                                       f'/1/1x2/',
                                                       headers={'Referer': match_page.url})

    bs_match_page: BeautifulSoup = BeautifulSoup(match_page.content, 'lxml')
    bs_odds_table: BeautifulSoup = BeautifulSoup(odds_table.text.replace(r'\n', '\n').replace(r'\ '[0], ""), 'html.parser')

    data_with_link: namedtuple = namedtuple('data_with_link', ['data_about_match', 'link_on_match'])
    data_about_match: dict[column_name, Any] = {col: '-' for col in make_pattern_xlsx.columns}

    # Set date and time
    date_and_time: list[numeric_str] = bs_match_page.select('#match-date')[0].get('data-dt').split(',')
    data_about_match['Дата'] = '.'.join(date_and_time[:3])
    data_about_match['Время'] = ':'.join(date_and_time[3:])

    # Set match name
    match_name: name = bs_match_page.select('.list-breadcrumb__item__in')[-1].get_text()
    data_about_match['Название матча'] = match_name

    # Set league name
    league_name: name = (f"{bs_match_page.select('.list-breadcrumb__item__in')[-3].get_text()}: "
                         f"{bs_match_page.select('.list-breadcrumb__item__in')[-2].get_text()}")
    data_about_match['Название лиги'] = league_name

    # Set Game Scope
    game_scope: str = bs_match_page.select('#js-score')[0].get_text()
    data_about_match['Счет матча'] = game_scope

    # Set the score for the first and second half
    try:
        first_half_score, second_half_score = bs_match_page.select('#js-partial')[0].get_text().split(', ')
        data_about_match['Счет первого тайма'] = first_half_score[1:]
        data_about_match['Счет второго тайма'] = second_half_score[:-1]
    except ValueError:
        data_about_match['Счет первого тайма'] = '0:0'
        data_about_match['Счет второго тайма'] = '0:0'

    # Set average odds
    average_odds: list[Tag] = bs_odds_table.select('#sortable-1>tfoot>tr>.table-main__detail-odds')
    data_about_match['Средний коэффициент на домашнюю команду'] = average_odds[0].get('data-odd')
    data_about_match['Средний коэффициент на ничью'] = average_odds[1].get('data-odd')
    data_about_match['Средний коэффициент на гостевую команду'] = average_odds[2].get('data-odd')

    # Set the minute at which the first goal was scored
    goals_tables: list[Tag] = [table for table in bs_match_page.select('.list-details--shooters>li>table')]
    if goals_tables:
        times_of_goals_scored: list[int] = []
        for table in goals_tables:
            for tr in table.select('tr'):
                try:
                    times_of_goals_scored.append(int(tr.select('td')[1].get_text().replace('.', '')))
                except ValueError:
                    times_of_goals_scored.append(int(tr.select('td')[0].get_text().replace('.', '')))
        data_about_match['Минута, на которой был забит первый гол'] = min(times_of_goals_scored)
    else:
        data_about_match['Минута, на которой был забит первый гол'] = '-'

    # Set odds of winnings at bookmakers
    rows_of_bookmakers_with_odds: list[Tag] = bs_odds_table.select('#sortable-1>tbody>tr')
    for row in rows_of_bookmakers_with_odds:
        bookmaker_name: name = row.select('td>a.in-bookmaker-logo-link')[0].get_text()
        if bookmaker_name not in make_pattern_xlsx.columns[11:]:
            continue
        coefficient: float = row.select('td.table-main__detail-odds')[0].get('data-odd')
        data_about_match[bookmaker_name] = coefficient

    # Set maximal win coefficient
    list_of_odds_from_bookmakers: list[float] = [float(coefficient)
                                                 for coefficient in list(data_about_match.values())[11:]
                                                 if coefficient != '-']
    data_about_match['Максимальный коэффициент на победу фаворита'] = f'{max(list_of_odds_from_bookmakers):<04}'

    return data_with_link(data_about_match, match_page.url)


def run():
    # date = input('Введите дату (дд.мм.гггг): ').split('.') # asyncio
    loop: BaseEventLoop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # asyncio.run(get_list_of_links_to_matches('https://www.betexplorer.com/results/soccer/?year=2017&month=10&day=1'))
    print(asyncio.run(
        get_data_about_match('https://www.betexplorer.com/soccer/panama/lpf/plaza-amador-arabe-unido/bu4IFbXq/')))
    print(2 + 2)


if __name__ == '__main__':
    run()
