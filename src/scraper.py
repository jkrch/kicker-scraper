import os
import requests
import json

from bs4 import BeautifulSoup
from pandas import DataFrame, ExcelWriter, read_json
from copy import deepcopy


def get_teams(league, season):
    """Returns list with all teams in a league in a season.

    Parameters:
        league : str
            Name of the league.
        season : str
            The season.

    Returns:
        teams : list
            The name of the teams.
    """

    # Get site as soup
    url = 'https://www.kicker.de/' + league + '/vereine/' + season
    reqs = requests.get(url)
    soup = BeautifulSoup(reqs.text, 'html.parser')

    # Get list with all teams
    class_ = ('kick__t__a__l kick__table--ranking__teamname kick__table--'
              'ranking__index kick__respt-m-w-160')
    teams = soup.find_all('td', class_=class_)
    teams = [team.text.replace('\n', '') for team in teams]

    return teams


def get_matchday_urls(league, season, matchday):
    """Returns list of strings with all matches from a match day.

    Parameters:
        league : str
            Name of the league.
        season : str
            The season.
        matchday : str or int
            The number of the match day.

    Returns:
        urls : list of str
            The urls to all game stats sites of each match.
    """

    # Get site as soup
    url = 'https://www.kicker.de/' + league + '/spieltag/' + season + '/' + (
        str(matchday))
    reqs = requests.get(url)
    soup = BeautifulSoup(reqs.text, 'html.parser')

    # Getting all analyse links
    urls = []
    for link in soup.find_all('a'):
        link_href = link.get('href')
        if isinstance(link_href, str):
            link_ends = ['analyse', 'schema', 'spielbericht']
            for link_end in link_ends:
                if link_end in link_href:
                    urls.append(link_href)

    # Remove duplicates
    urls = urls[::2]

    # Replace 'analyse', 'schema', 'spielbericht' with 'spieldaten'
    for link_end in link_ends:
        urls = [i.replace(link_end, 'spieldaten') for i in urls]

    return urls


def get_matchday_stats(league, season, matchday):
    """Returns all game stats from a match day.

    Parameters:
        league : str
            Name of the league.
        season : str
            The season.
        matchday : str or int
            The number of the match day.

    Returns:
        matchday_stats : list
            The game stats of all matches.
    """
    matchday_stats = []

    # Iterate over all matches
    for url in get_matchday_urls(league, season, matchday):

        # Making a GET request
        r = requests.get('https://www.kicker.de' + url)

        # Parsing the HTML
        soup = BeautifulSoup(r.content, 'html.parser')

        # Getting the data grid
        data_grid = soup.find('div', class_='kick__compare-select')
        type(data_grid)

        # Getting list of data grid rows
        list_data_grid = data_grid.find_all('div', class_='kick__stats-bar')

        # Getting the data grid
        data_grid = soup.find('div', class_=('kick__data-grid--max-width kick_'
                                             '_data-grid--max-width'))

        # Getting list of data grid rows
        list_data_grid = data_grid.find_all('div', class_='kick__stats-bar')

        # Get data for title, opponent 1 and opponent 2
        title, opp1, opp2 = [], [], []
        for i_list_data_grid in list_data_grid:
            class_ = "kick__stats-bar__title"
            title.append(i_list_data_grid.find('div', class_=class_).text)
            class_ = 'kick__stats-bar__value kick__stats-bar__value--opponent'
            opp1.append(i_list_data_grid.find('div', class_=class_ + '1').text)
            opp2.append(i_list_data_grid.find('div', class_=class_ + '2').text)

        # Get team names
        class1 = 'kick__compare-select__row kick__compare-select__row--left'
        class2 = 'kick__compare-select__row kick__compare-select__row--right'
        col1 = soup.find('div', class_=class1).text.replace('\n', '')
        col2 = soup.find('div', class_=class2).text.replace('\n', '')

        # Add stats as dataframe
        matchday_stats.append(
            DataFrame(list(zip(opp1, opp2)), columns=[col1, col2],
                      index=title).to_json())

    return matchday_stats


def get_season_stats(league, season, length, qt_signal=None):
    """Returns all game stats from a whole season.

    Parameters:
        league : str
            Name of the league.
        season : str
            The season.
        length : int
            Length of the season.
        qt_signal : QtCore.Signal, default=None
            Signal that returns matchday.

    Returns:
        season_stats : list of list of dataframe
            The game stats of all matches of the season.
    """
    season_stats = []
    if league == "bundesliga":
        n_matchdays = 34
    else:
        n_matchdays = 38
    for matchday in range(1, n_matchdays + 1):
        print(matchday)
        if qt_signal:
            qt_signal.emit(matchday)
        season_stats.append(get_matchday_stats(league, season, matchday))
    return season_stats


def get_stats_home_away(league, season, season_stats):
    """Order stats in home and away tables.

    Parameters:
        league : str
            Name of the league.
        season : str
            The season.
        season_stats : list
            List with the stats from all games from a season.

    Returns:
        stats_home : dict
            Statistics for home teams.
        stats_away : dict
            Statistics for away teams.
    """
    # Get keys for dict
    keys = list(read_json(season_stats[0][0]).index)
    keys[2] += ' in km'
    keys[6] += ' in %'
    keys[7] += ' in %'
    keys[8] += ' in %'

    # Create empty dicts
    stats_home = dict(zip(keys, [None] * len(keys)))
    stats_away = dict(zip(keys, [None] * len(keys)))

    # Get team names
    teams = get_teams(league, season)

    # Iterate over keys/stats
    for i, key in enumerate(keys):
        df_home = DataFrame(index=teams, columns=teams)
        df_away = DataFrame(index=teams, columns=teams)
        for matchday in range(len(season_stats)):
            for match in range(len(season_stats[matchday])):
                series = read_json(season_stats[matchday][match]).iloc[i]
                index = list(series.index)
                values = list(series.values)

                # Convert from string
                if key == 'Laufleistung in km':
                    values0 = float(values[0].replace(',', '.').replace(
                        ' km', ''))
                    values1 = float(values[1].replace(',', '.').replace(
                        ' km', ''))
                else:
                    values0 = int(values[0].replace('%', ''))
                    values1 = int(values[1].replace('%', ''))
                df_home.loc[index[0]][index[1]] = values0
                df_away.loc[index[1]][index[0]] = values1
        stats_home[key] = df_home
        stats_away[key] = df_away
    return stats_home, stats_away


def add_sum_mean_std(stats):
    """Returns stats with added sum, mean and standard derivation to stats.

    Parameters:
        stats : list
            All statistics.
    Returns:
        stats_extra : list
            All statistics with added sum, mean, std.
    """
    stats_extra = deepcopy(stats)
    for key, df in stats_extra.items():
        n_rows, n_cols = df.shape
        df.loc['Summe'] = df.iloc[:n_rows, :n_cols].sum()
        df['Summe'] = df.iloc[:n_rows, :n_cols].sum(axis=1)
        df.loc['Mittelwert'] = df.iloc[:n_rows, :n_cols].mean()
        df['Mittelwert'] = df.iloc[:n_rows, :n_cols].mean(axis=1)
        df.loc['Standardabweichung'] = df.iloc[:n_rows, :n_cols].std()
        df['Standardabweichung'] = df.iloc[:n_rows, :n_cols].std(axis=1)
    return stats_extra


def main(league, season, length, qt_signal=None):
    """Scrape or load stats of a season in a league and write to excel file
    stats wise.

    Parameters:
        league : str
            Name of the league.
        season : str
            The season.
        length : int
            Length of the season.
        qt_signal : QtCore.Signal, default=None
            Signal that returns matchday.
    """

    # Get season stats from disk or scrape and write to disk using JSON
    dir_name = 'json'
    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)
    file_name = league + '_' + season
    file_path = os.path.join(dir_name, file_name) + '.json'
    if os.path.isfile(file_path):
        if qt_signal:
            qt_signal.emit(length)
        with (open(file_path, 'r')) as f:
            season_stats = json.load(f)
    else:
        season_stats = get_season_stats(league, season, length, qt_signal)
        with (open(file_path, 'w')) as f:
            f.write(json.dumps(season_stats, indent=len(season_stats)))

    # Create home and away tables
    stats_home, stats_away = get_stats_home_away(league, season, season_stats)

    # Add sum, mean, standard derivation
    stats_home_extra = add_sum_mean_std(stats_home)
    stats_away_extra = add_sum_mean_std(stats_away)

    # Write stats to Excel file
    dir_name = 'excel'
    if not os.path.isdir(dir_name):
        os.mkdir(dir_name)
    file_name = league + '_' + season + '.xlsx'
    file_path = os.path.join(dir_name, file_name)
    keys = stats_home.keys()
    sheet_names = [key.replace('/', ' oder ') for key in keys]
    with ExcelWriter(file_path) as writer:
        for key, sheet_name in zip(keys, sheet_names):
            stats_home_extra[key].to_excel(writer, sheet_name=sheet_name)
            startrow = len(stats_home_extra[key]) + 2
            stats_away_extra[key].to_excel(writer, sheet_name=sheet_name,
                                           startrow=startrow)
    qt_signal.emit(length + 2)
