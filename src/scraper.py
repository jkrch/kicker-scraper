import requests

from bs4 import BeautifulSoup
from pandas import DataFrame, read_json
from copy import deepcopy


def check_internet():
    """Check if internet and/or kicker.de is working."""
    url = "https://www.kicker.de"
    timeout = 10
    try:
        requests.get(url, timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


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

    # Change keys for some stats
    subs = {
        'Laufleistung': 'Laufleistung in km',
        'Passquote': 'Passquote in %',
        'Ballbesitz': 'Ballbesitz in %',
        'Zweikampfquote': 'Zweikampfquote in %'
    }
    keys = [subs.get(key, key) for key in keys]

    # Create empty dicts
    stats_home = dict(zip(keys, [None] * len(keys)))
    stats_away = dict(zip(keys, [None] * len(keys)))

    # Get team names
    # TODO: Find offline solution
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
