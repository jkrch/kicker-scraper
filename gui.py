import sys

from PySide2.QtWidgets import (
    QMainWindow, QWidget, QComboBox, QApplication, QLabel, QVBoxLayout,
    QHBoxLayout, QProgressBar, QPushButton, )
from PySide2.QCoreApplication import processEvents

from scraper import main as scraper_main


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Kicker Scraper")

        # Main layout
        vlayout = QVBoxLayout()

        # League
        self.leagues = ["bundesliga", "la-liga", "premier-league", "serie-a"]
        self.league = self.leagues[0]
        self.combobox_league = QComboBox()
        self.combobox_league.addItems(self.leagues)
        self.combobox_league.currentTextChanged.connect(
            self.combobox_league_changed)
        hlayout_league = QHBoxLayout()
        hlayout_league.addWidget(QLabel("League:"))
        hlayout_league.addWidget(self.combobox_league)
        vlayout.addLayout(hlayout_league)

        # Season
        self.seasons = {
            "bundesliga": [
                "2021-22", "2020-21", "2019-20", "2018-19", "2017-18",
                "2016-17", "2015-16", "2014-15", "2013-14"
            ],
            "la-liga": [
                "2021-22", "2020-21", "2019-20", "2018-19"
            ],
            "premier-league": [
                "2021-22", "2020-21", "2019-20", "2018-19"
            ],
            "serie-a": [
                "2021-22", "2020-21", "2019-20", "2018-19"
            ],
        }
        self.season = self.seasons[self.league][0]
        self.combobox_season = QComboBox()
        self.combobox_season.addItems(self.seasons[self.league])
        self.combobox_season.currentTextChanged.connect(
            self.combobox_season_changed)
        hlayout_season = QHBoxLayout()
        hlayout_season.addWidget(QLabel("Season:"))
        hlayout_season.addWidget(self.combobox_season)
        vlayout.addLayout(hlayout_season)

        # Progressbar
        self.progressbar = QProgressBar()
        self.progressbar.setRange(0, 34 + 1)
        self.progressbar.setTextVisible(False)
        vlayout.addWidget(self.progressbar)

        # Buttons
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.button_cancel_clicked)
        self.button_ok = QPushButton("OK")
        self.button_ok.clicked.connect(self.button_ok_clicked)
        hlayout_buttons = QHBoxLayout()
        hlayout_buttons.addWidget(self.button_cancel)
        hlayout_buttons.addWidget(self.button_ok)
        vlayout.addLayout(hlayout_buttons)

        # Central widget
        widget = QWidget()
        widget.setLayout(vlayout)
        self.setCentralWidget(widget)

    def combobox_league_changed(self, s):
        self.league = s
        self.combobox_season.clear()
        self.combobox_season.addItems(self.seasons[self.league])
        self.progressbar.setValue(0)
        if s == "bundesliga":
            self.progressbar.setRange(0, 34 + 1)
        else:
            self.progressbar.setRange(0, 38 + 1)

    def combobox_season_changed(self, s):
        self.season = s
        self.progressbar.setValue(0)

    def button_ok_clicked(self):

        # Update progressbar
        self.progressbar.setValue(1)
        processEvents()

        # Deactivate button
        # self.button_ok.isVisible(False)

        # Get stats and save to disk
        scraper_main(self.league, self.season, self.progressbar)

        # Update progessbar
        self.progressbar.setValue(self.progressbar.maximum())

        # Activate button
        # self.button_ok.isVisible(True)

    def button_cancel_clicked(self):
        self.close()


app = QApplication(sys.argv)
window = MainWindow()
window.show()

app.exec_()
