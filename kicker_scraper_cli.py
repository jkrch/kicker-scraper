#!venv/bin/python

import argparse
import os
import sys
from typing import Dict, List, Tuple

import pandas as pd
import requests
from bs4 import BeautifulSoup


def check_internet():
    """Check if internet and/or kicker.de is working."""
    try:
        requests.get("https://www.kicker.de", timeout=10)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False


def get_teams(league: str, season: str) -> list:
    """Returns list with all teams in a league in a season sorted from
    best to worst at the end of the season.

    Parameters:
    -----------
        league : str
            Name of the league.
        season : str
            The season.

    Returns:
    --------
        teams : list
            The name of the teams.
    """

    soup = BeautifulSoup(
        requests.get(f"https://www.kicker.de/{league}/vereine/{season}").text,
        "html.parser",
    )

    # Get list with all teams
    class_ = (
        "kick__t__a__l kick__table--ranking__teamname kick__table--"
        "ranking__index kick__respt-m-w-160"
    )
    teams = soup.find_all("td", class_=class_)
    teams = [team.text.replace("\n", "") for team in teams]

    return teams


def get_urls_matchday(
    league: str, season: str, matchday: int, url_type=0
) -> List[str]:
    """Returns list of strings with all matches from a match day.

    Parameters:
    -----------
        league : str
            Name of the league.
        season : str
            The season.
        matchday : int
            The number of the match day.
        url_type : int
            If 0, then the urls for the game stats are returned. If 1,
            then the urls for the game info are returned.

    Returns:
    --------
        urls : List[str]
            The urls to all game stats sites of each match.
    """

    soup = BeautifulSoup(
        requests.get(
            f"https://www.kicker.de/{league}/spieltag/{season}/{str(matchday)}"
        ).text,
        "html.parser",
    )

    # Getting all analyse links
    urls = []
    for link in soup.find_all("a"):
        link_href = link.get("href")
        if isinstance(link_href, str):
            link_ends = ["/analyse", "/schema", "/spielbericht"]
            for link_end in link_ends:
                if link_end in link_href:
                    urls.append(link_href)

    # Remove duplicates
    urls = urls[::2]

    # Replace 'analyse', 'schema', 'spielbericht' with 'spieldaten' or
    # 'spielinfo'
    if url_type == 0:
        for link_end in link_ends:
            urls = [i.replace(link_end, "/spieldaten") for i in urls]
    elif url_type == 1:
        for link_end in link_ends:
            urls = [i.replace(link_end, "/spielinfo") for i in urls]

    return urls


def get_stats_matchday(urls: List[str]) -> List[pd.DataFrame]:
    """Returns all game stats from a match day."""

    stats_matchday = []

    # Iterate over all matches
    for url in urls:

        soup = BeautifulSoup(
            requests.get("https://www.kicker.de" + url).content, "html.parser"
        )

        # Getting the data grid
        data_grid = soup.find("div", class_="kick__compare-select")

        # Getting list of data grid rows
        list_data_grid = data_grid.find_all("div", class_="kick__stats-bar")

        # Getting the data grid
        class_ = "kick__data-grid--max-width kick_" "_data-grid--max-width"
        data_grid = soup.find("div", class_=class_)

        # Getting list of data grid rows
        list_data_grid = data_grid.find_all("div", class_="kick__stats-bar")

        # Get data for title and teams
        title, team1, team2 = [], [], []
        for i_list_data_grid in list_data_grid:
            class_ = "kick__stats-bar__title"
            title.append(i_list_data_grid.find("div", class_=class_).text)
            class_ = "kick__stats-bar__value kick__stats-bar__value--opponent"
            team1.append(
                i_list_data_grid.find("div", class_=class_ + "1").text
            )
            team2.append(
                i_list_data_grid.find("div", class_=class_ + "2").text
            )

        # Get team names
        class1 = "kick__compare-select__row kick__compare-select__row--left"
        class2 = "kick__compare-select__row kick__compare-select__row--right"
        col1 = soup.find("div", class_=class1).text.replace("\n", "")
        col2 = soup.find("div", class_=class2).text.replace("\n", "")

        # Add stats as dataframe
        stats_matchday.append(
            pd.DataFrame(
                list(zip(team1, team2)), columns=[col1, col2], index=title
            )
        )

    return stats_matchday


def save_stats_matchday(
    stats_matchday: pd.DataFrame, matchday: int, filepath: str
):
    with pd.ExcelWriter(filepath, mode="a+") as writer:
        stats_matchday.to_excel(writer, sheet_name=str(matchday), index=False)


def get_visitors_matchday(urls_matchday: List[str]) -> pd.DataFrame:
    """Returns all the visitors of all matches from a match day."""

    df_visitors_matchday = pd.DataFrame(
        columns=["Heimteam", "Auswärtsteam", "Zuschauer", "Ausverkauft"]
    )

    # Iterate over all matches
    for i, url in enumerate(urls_matchday):

        soup = BeautifulSoup(
            requests.get("https://www.kicker.de" + url).content, "html.parser"
        )

        # Get team names
        class_ = "kick__v100-gameCell kick__v100-gameCell--big"
        teams = soup.find("div", class_=class_)
        class_ = "kick__v100-gameCell__team__name"
        teams = teams.find_all("div", class_=class_)
        team_home = teams[0].text[:-1]
        team_away = teams[1].text[:-1]

        # Getting the visitors
        visitors = soup.find(
            "div", class_="kick__gameinfo-block kick__tabular-nums"
        )
        if visitors:
            visitors = (
                visitors.text.replace("Zuschauer", "")
                .replace("\r", "")
                .replace("\n", "")
                .replace(".", "")
            )
        else:
            visitors = None

        # Check if sold out
        sold_out_str = "(ausverkauft)"
        if sold_out_str in visitors:
            sold_out = True
            visitors = visitors.replace(sold_out_str, "")
        else:
            sold_out = False

        # Add to DataFrame
        df_visitors_matchday.loc[i] = [
            team_home,
            team_away,
            visitors,
            sold_out,
        ]

    return df_visitors_matchday


def create_stats_tables(
    stats_season: List[pd.DataFrame], teams: List[str]
) -> Dict[str, pd.DataFrame]:
    """Order stats in home and away tables."""

    # Get keys for dict
    keys = list(stats_season[0][0].index)

    # Change keys for some stats
    subs = {
        "Laufleistung": "Laufleistung in km",
        "Passquote": "Passquote in %",
        "Ballbesitz": "Ballbesitz in %",
        "Zweikampfquote": "Zweikampfquote in %",
    }
    keys = [subs.get(key, key) for key in keys]

    # Create empty dicts
    stats_home = dict(zip(keys, [None] * len(keys)))
    stats_away = dict(zip(keys, [None] * len(keys)))

    # Iterate over keys/stats
    for i, key in enumerate(keys):
        df_home = pd.DataFrame(index=teams, columns=teams)
        df_away = pd.DataFrame(index=teams, columns=teams)
        for matchday in range(len(stats_season)):
            for match in range(len(stats_season[matchday])):
                series = stats_season[matchday][match].iloc[i]
                index = list(series.index)
                values = list(series.values)

                # Convert from string
                if key == "Laufleistung in km":
                    values0 = float(
                        values[0].replace(",", ".").replace(" km", "")
                    )
                    values1 = float(
                        values[1].replace(",", ".").replace(" km", "")
                    )
                else:
                    values0 = int(values[0].replace("%", ""))
                    values1 = int(values[1].replace("%", ""))
                df_home.loc[index[0]][index[1]] = values0
                df_away.loc[index[1]][index[0]] = values1
        stats_home[key] = df_home
        stats_away[key] = df_away

    return stats_home, stats_away


def add_sum_mean_std(stats_tables: List[pd.DataFrame]) -> List[pd.DataFrame]:
    # stats_extra = deepcopy(stats)
    for key, df in stats_tables.items():
        n_rows, n_cols = df.shape
        df.loc["Summe"] = df.iloc[:n_rows, :n_cols].sum()
        df["Summe"] = df.iloc[:n_rows, :n_cols].sum(axis=1)
        df.loc["Mittelwert"] = df.iloc[:n_rows, :n_cols].mean()
        df["Mittelwert"] = df.iloc[:n_rows, :n_cols].mean(axis=1)
        df.loc["Standardabweichung"] = df.iloc[:n_rows, :n_cols].std()
        df["Standardabweichung"] = df.iloc[:n_rows, :n_cols].std(axis=1)
    return stats_tables


def replace_ballbesitz(
    visitors_season: List[pd.DataFrame],
) -> List[pd.DataFrame]:
    """Replaces the 'Ballbesitz' entries for matches with 0 visitors."""
    for visitors_matchday in visitors_season:
        for row_index, row in visitors_matchday.iterrows():
            print
            if row.Zuschauer.startswith("Ballbesitz"):
                visitors_matchday.loc[row_index, "Zuschauer"] = "0"
    return visitors_season


# def write_to_xlsx(visitors_season: List[pd.DataFrame], filepath: str):
#     for i, df_visitors in enumerate(visitors_season):
#         if i == 0:
#             mode = "w"
#         else:
#             mode = "a"
#         with pd.ExcelWriter(filepath, mode=mode) as writer:
#             df_visitors.to_excel(writer, sheet_name=str(i + 1), index=False)


# def read_from_xlsx(filepath: str) -> List[pd.DataFrame]:
#     visitors_season = []
#     xlsx = pd.ExcelFile(filepath)
#     for sheet_name in range(len(xlsx.sheet_names)):
#         visitors_season.append(pd.read_excel(xlsx, sheet_name=sheet_name))
#     return visitors_season


def create_visitors_tables(
    visitors_season: List[pd.DataFrame], teams: List[str]
) -> Dict[str, pd.DataFrame]:

    visitors_tables = {
        "Zuschauer": pd.DataFrame(index=teams, columns=teams),
        "Ausverkauft": pd.DataFrame(index=teams, columns=teams),
    }
    for visitors_matchday in visitors_season:
        for match in visitors_matchday.iterrows():
            match = match[1]
            visitors_tables["Zuschauer"].loc[match[0]][match[1]] = match[2]
            visitors_tables["Ausverkauft"].loc[match[0]][match[1]] = match[3]

    # visitors_tables["Ausverkauft"].replace(1, "x")
    # visitors_tables["Ausverkauft"].replace(0, "")

    return visitors_tables


def write_table_visitors(
    visitors_tables: Tuple[pd.DataFrame, pd.DataFrame], filepath: str
):
    with pd.ExcelWriter(filepath, mode="w") as writer:
        visitors_tables[0].to_excel(writer, sheet_name="Zuschauer")
        visitors_tables[1].to_excel(writer, sheet_name="Ausverkauft")


def write_to_xlsx(
    filepath: str,
    stats_tables_home: Dict[str, pd.DataFrame],
    stats_tables_away: Dict[str, pd.DataFrame],
    visitors_tables: Dict[str, pd.DataFrame],
):
    with pd.ExcelWriter(filepath) as writer:
        keys = stats_tables_home.keys()
        sheet_names = [key.replace("/", " oder ") for key in keys]
        for key, sheet_name in zip(keys, sheet_names):
            stats_tables_home[key].to_excel(
                writer,
                sheet_name=sheet_name,
            )
            stats_tables_away[key].to_excel(
                writer,
                sheet_name=sheet_name,
                startrow=len(stats_tables_home[list(keys)[0]]) + 2,
            )
        for sheet_name, visitors_table in visitors_tables.items():
            visitors_table.to_excel(writer, sheet_name=sheet_name)


def main():

    leagues = [
        "bundesliga",
        "la-liga",
        "premier-league",
        "serie-a",
    ]
    seasons_buli = [
        "2021-22",
        "2020-21",
        "2019-20",
        "2018-19",
        "2017-18",
        "2016-17",
        "2015-16",
        "2014-15",
        "2013-14",
    ]
    seasons_others = [
        "2021-22",
        "2020-21",
        "2019-20",
        "2018-19",
    ]
    matchdays = {
        "bundesliga": 34,
        "la-liga": 38,
        "premier-league": 38,
        "serie-a": 38,
    }

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-l",
        "--league",
        const="league",
        nargs="?",
        help=f"Choose from {leagues}.",
        required=True,
        # choices=leagues,
    )
    parser.add_argument(
        "-s",
        "--season",
        const="season",
        nargs="?",
        help=(
            f"Choose from {seasons_buli} for 'bundesliga' or "
            f"{seasons_others} for the other leagues."
        ),
        required=True,
        # choices=seasons_buli,
    )
    parser.add_argument(
        "-d",
        "--dir",
        const="dir",
        nargs="?",
        help="The path for the directory for the Excel files.",
        required=False,
        default=".",
    )
    args = parser.parse_args()

    if args.league not in leagues:
        raise ValueError(f"The league most be one of {leagues}.")
        sys.exit()
    if args.season not in seasons_buli:
        raise ValueError(f"The season most be one of {seasons_buli}.")
        sys.exit()
    if args.league != "bundesliga" and args.seasons not in seasons_others:
        raise ValueError(
            f"The season for {args.league} must be one of "
            f"{seasons_others}."
        )
        sys.exit()

    if not check_internet():
        print("Internet connection or kicker.de down!")
        sys.exit()

    # if args.season == "all":
    #     seasons = seasons[args.league]
    # else:
    #     seasons = [args.season]

    league = args.league
    season = args.season

    teams = get_teams(league, season)

    stats_season = []
    visitors_season = []
    for matchday in range(1, matchdays[league] + 1):
        print(matchday)

        urls_matchday = get_urls_matchday(league, season, matchday)
        stats_matchday = get_stats_matchday(urls_matchday)
        stats_season.append(stats_matchday)

        urls_matchday = get_urls_matchday(league, season, matchday, url_type=1)
        visitors_matchday = get_visitors_matchday(urls_matchday)
        visitors_season.append(visitors_matchday)

    stats_tables_home, stats_tables_away = create_stats_tables(
        stats_season, teams
    )
    stats_tables_home = add_sum_mean_std(stats_tables_home)
    stats_tables_away = add_sum_mean_std(stats_tables_away)

    visitors_season = replace_ballbesitz(visitors_season)
    visitors_tables = create_visitors_tables(visitors_season, teams)

    filepath = os.path.join(args.dir, f"{league}_{season}.xlsx")
    write_to_xlsx(
        filepath, stats_tables_home, stats_tables_away, visitors_tables
    )


if __name__ == "__main__":
    main()
