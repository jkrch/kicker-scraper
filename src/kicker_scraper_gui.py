#!venv/bin/python

import os
import sys

from PySide2 import QtCore
from PySide2.QtGui import QIcon
from PySide2.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from kicker_scraper_cli import (
    add_sum_mean_std,
    check_internet,
    create_stats_tables,
    create_visitors_tables,
    get_stats_matchday,
    get_teams,
    get_urls_matchday,
    get_visitors_matchday,
    replace_ballbesitz,
    write_to_xlsx,
)


class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Kicker Scraper")
        self.setWindowFlags(
            QtCore.Qt.WindowCloseButtonHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )

        # # Download folder
        # self.dir_json = "Downloads"
        # if not os.path.isdir(self.dir_json):
        #     os.mkdir(self.dir_json)

        # Initialize variables
        self.init_vars()

        # Initialize layout
        self.init_layout()

        # Worker for the scraping
        self.worker = Worker(self)
        self.worker.updateProgress.connect(self.update_progressbar)

    def init_vars(self):

        # League
        self.leagues = [
            "bundesliga",
            "la-liga",
            "premier-league",
            "serie-a",
        ]
        self.leagues_edit = [
            "Bundesliga",
            "La Liga",
            "Premier League",
            "Serie A",
        ]
        self.lengths = [34, 38, 38, 38]
        self.length = self.lengths[0]
        self.league = self.leagues[0]

        self.seasons = {
            "bundesliga": [
                "2021-22",
                "2020-21",
                "2019-20",
                "2018-19",
                "2017-18",
                "2016-17",
                "2015-16",
                "2014-15",
                "2013-14",
            ],
            "la-liga": [
                "2021-22",
                "2020-21",
                "2019-20",
                "2018-19",
            ],
            "premier-league": [
                "2021-22",
                "2020-21",
                "2019-20",
                "2018-19",
            ],
            "serie-a": [
                "2021-22",
                "2020-21",
                "2019-20",
                "2018-19",
            ],
        }
        self.season = self.seasons[self.league][0]

    def init_layout(self):

        # Main layout
        vlayout = QVBoxLayout()

        # Combobox league
        self.combobox_league = QComboBox()
        self.combobox_league.addItems(self.leagues_edit)
        self.combobox_league.currentTextChanged.connect(
            self.combobox_league_changed
        )
        hlayout_league = QHBoxLayout()
        hlayout_league.addWidget(self.combobox_league)
        vlayout.addLayout(hlayout_league)

        # Combobox season
        self.combobox_season = QComboBox()
        self.combobox_season.addItems(self.seasons[self.league])
        self.combobox_season.currentIndexChanged.connect(
            self.combobox_season_changed
        )
        hlayout_season = QHBoxLayout()
        hlayout_season.addWidget(self.combobox_season)
        vlayout.addLayout(hlayout_season)

        # # Download
        # hlayout_download = QHBoxLayout()
        # self.label_download = QLabel("Download")
        # hlayout_download.addWidget(self.label_download)
        # self.checkbox_download = QCheckBox()
        # self.update_checkbox_download()
        # hlayout_download.addWidget(self.checkbox_download)
        # hlayout_download.setAlignment(QtCore.Qt.AlignLeft)
        # vlayout.addLayout(hlayout_download)

        # Button and line edit Excel folder
        self.line_edit_folder = QLineEdit()
        self.line_edit_folder.setEnabled(False)
        self.button_folder = QPushButton()
        self.button_folder.setIcon(QIcon.fromTheme("folder"))
        self.button_folder.clicked.connect(self.button_folder_clicked)
        hlayout_folder = QHBoxLayout()
        hlayout_folder.addWidget(self.line_edit_folder)
        hlayout_folder.addWidget(self.button_folder)
        vlayout.addLayout(hlayout_folder)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 34 + 2)
        self.progress_bar.setTextVisible(False)
        vlayout.addWidget(self.progress_bar)

        # Buttons cancel and ok
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.setMinimumWidth(90)
        self.button_cancel.setMaximumWidth(90)
        self.button_cancel.clicked.connect(self.button_cancel_clicked)
        self.button_ok = QPushButton("OK")
        self.button_ok.setMinimumWidth(70)
        self.button_ok.setMaximumWidth(70)
        self.button_ok.setEnabled(False)
        self.button_ok.clicked.connect(self.button_ok_clicked)
        hlayout_buttons = QHBoxLayout()
        hlayout_buttons.addWidget(self.button_cancel)
        hlayout_buttons.addWidget(self.button_ok)
        hlayout_buttons.setAlignment(QtCore.Qt.AlignRight)
        vlayout.addLayout(hlayout_buttons)

        # Set as central widget
        main_window = QWidget()
        main_window.setLayout(vlayout)
        self.setCentralWidget(main_window)

    def combobox_league_changed(self):
        i = self.combobox_league.currentIndex()
        self.league = self.leagues[i]
        self.length = self.lengths[i]
        self.combobox_season.clear()
        self.combobox_season.addItems(self.seasons[self.league])
        self.progress_bar.setRange(0, self.length + 2)
        self.progress_bar.setValue(0)
        # self.update_checkbox_download()

    def combobox_season_changed(self):
        self.season = self.combobox_season.currentText()
        self.progress_bar.setValue(0)
        # self.update_checkbox_download()

    # def update_checkbox_download(self):
    #     f = self.league + "_" + self.season + ".json"
    #     if f in os.listdir(self.dir_json):
    #         self.checkbox_download.setEnabled(True)
    #         self.checkbox_download.setChecked(False)
    #     else:
    #         self.checkbox_download.setEnabled(False)
    #         self.checkbox_download.setChecked(True)

    def button_ok_clicked(self):

        # Check internet
        # TODO: If get_teams gets offline solution, only check internet if
        #       dowload checkbox is toggled
        # if self.checkbox_download.isChecked():
        if not check_internet():
            self.widget_internet = InternetWidget()
            self.widget_internet.show()
            return 0

        # Disable widget
        self.combobox_league.setEnabled(False)
        self.combobox_season.setEnabled(False)
        # self.checkbox_download.setEnabled(False)
        # self.label_download.setEnabled(False)
        self.button_folder.setEnabled(False)
        self.button_ok.setEnabled(False)

        # Reset progress bar
        self.progress_bar.setValue(0)

        # Start worker
        self.worker.start()

    def button_cancel_clicked(self):
        self.close()

    def update_progressbar(self, progress):
        self.progress_bar.setValue(progress)
        # Enable widgets
        if progress == self.length + 2:
            self.combobox_league.setEnabled(True)
            self.combobox_season.setEnabled(True)
            # self.label_download.setEnabled(True)
            # self.update_checkbox_download()
            self.button_folder.setEnabled(True)
            self.button_ok.setEnabled(True)

    def button_folder_clicked(self):
        self.folder = QFileDialog.getExistingDirectory()
        self.line_edit_folder.setText(self.folder)
        if self.line_edit_folder.text() == "":
            self.button_ok.setEnabled(False)
        else:
            self.button_ok.setEnabled(True)
        # self.worker.folder = self.folder


class InternetWidget(QWidget):
    """Window that pops up if internet or kicker.de not working."""

    def __init__(self):
        super(InternetWidget, self).__init__()
        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint)
        self.setWindowTitle("Kicker Scraper")
        vlayout = QVBoxLayout()
        vlayout.addWidget(QLabel("Internet or kicker.de down!"))
        self.setLayout(vlayout)


class Worker(QtCore.QThread):
    """Worker class for scraping stats from kicker.de"""

    updateProgress = QtCore.Signal(int)

    def __init__(self, parent=None):
        QtCore.QThread.__init__(self)
        self.parent = parent

    def run(self):

        league = self.parent.league
        season = self.parent.season
        length = self.parent.length
        filepath = os.path.join(
            self.parent.line_edit_folder.text(), f"{league}_{season}.xlsx"
        )

        teams = get_teams(league, season)

        stats_season = []
        visitors_season = []
        for matchday in range(1, length + 1):
            print(matchday)
            self.updateProgress.emit(matchday)

            urls_matchday = get_urls_matchday(league, season, matchday)
            stats_matchday = get_stats_matchday(urls_matchday)
            stats_season.append(stats_matchday)

            urls_matchday = get_urls_matchday(
                league, season, matchday, url_type=1
            )
            visitors_matchday = get_visitors_matchday(urls_matchday)
            visitors_season.append(visitors_matchday)

        stats_tables_home, stats_tables_away = create_stats_tables(
            stats_season, teams
        )
        stats_tables_home = add_sum_mean_std(stats_tables_home)
        stats_tables_away = add_sum_mean_std(stats_tables_away)

        visitors_season = replace_ballbesitz(visitors_season)
        visitors_tables = create_visitors_tables(visitors_season, teams)

        self.updateProgress.emit(self.parent.length + 1)

        write_to_xlsx(
            filepath, stats_tables_home, stats_tables_away, visitors_tables
        )

        self.updateProgress.emit(self.parent.length + 2)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
