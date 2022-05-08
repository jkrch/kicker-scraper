import sys

from PySide2 import QtCore
from PySide2.QtWidgets import (
    QMainWindow, QWidget, QComboBox, QApplication, QVBoxLayout, QHBoxLayout,
    QProgressBar, QPushButton)

from scraper import main as scraper_main


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Kicker Scraper")

        self.setWindowFlags(QtCore.Qt.WindowCloseButtonHint
                            | QtCore.Qt.WindowMinimizeButtonHint)

        # Main layout
        vlayout = QVBoxLayout()

        # League
        self.leagues = ["bundesliga", "la-liga", "premier-league", "serie-a"]
        self.leagues_edit = ["Bundesliga", "La Liga", "Premier League",
                             "Serie A"]
        self.lengths = [34, 38, 38, 38]
        self.length = self.lengths[0]
        self.league = self.leagues[0]
        self.combobox_league = QComboBox()
        self.combobox_league.addItems(self.leagues_edit)
        self.combobox_league.currentTextChanged.connect(
            self.combobox_league_changed)
        hlayout_league = QHBoxLayout()
        # hlayout_league.addWidget(QLabel("League:"))
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
        self.combobox_season.currentIndexChanged.connect(
            self.combobox_season_changed)
        hlayout_season = QHBoxLayout()
        # hlayout_season.addWidget(QLabel("Season:"))
        hlayout_season.addWidget(self.combobox_season)
        vlayout.addLayout(hlayout_season)

        # progress_bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 34 + 2)
        self.progress_bar.setTextVisible(False)
        vlayout.addWidget(self.progress_bar)

        # Buttons
        self.button_cancel = QPushButton("Cancel")
        self.button_cancel.clicked.connect(self.button_cancel_clicked)
        self.button_ok = QPushButton("OK")
        self.button_ok.clicked.connect(self.button_ok_clicked)
        hlayout_buttons = QHBoxLayout()
        hlayout_buttons.addWidget(self.button_cancel)
        hlayout_buttons.addWidget(self.button_ok)
        vlayout.addLayout(hlayout_buttons)

        # Create worker for the actual work
        self.worker = Worker(self.league, self.season, self.length)
        self.worker.updateProgress.connect(self.setProgress)

        # Central widget
        widget = QWidget()
        widget.setLayout(vlayout)
        self.setCentralWidget(widget)

    def combobox_league_changed(self):
        i = self.combobox_league.currentIndex()
        self.league = self.leagues[i]
        self.length = self.lengths[i]
        self.combobox_season.clear()
        self.combobox_season.addItems(self.seasons[self.league])
        self.progress_bar.setRange(0, self.length + 2)
        self.progress_bar.setValue(0)

    def combobox_season_changed(self):
        self.season = self.combobox_season.currentText()
        self.progress_bar.setValue(0)

    def button_ok_clicked(self):
        self.button_ok.setEnabled(False)
        self.combobox_league.setEnabled(False)
        self.combobox_season.setEnabled(False)

        # Update and start worker
        self.progress_bar.setValue(0)
        self.worker.league = self.league
        self.worker.season = self.season
        self.worker.length = self.length
        self.worker.start()

    def button_cancel_clicked(self):
        self.close()

    def setProgress(self, progress):
        self.progress_bar.setValue(progress)
        if progress == self.length + 2:
            self.button_ok.setEnabled(True)
            self.combobox_league.setEnabled(True)
            self.combobox_season.setEnabled(True)


class Worker(QtCore.QThread):
    """ Worker class for scraping the seasonal stats, building the home/away
    tables and writing the tables to Excel.
    """
    updateProgress = QtCore.Signal(int)

    def __init__(self, league, season, length):
        QtCore.QThread.__init__(self)
        self.league = league
        self.season = season
        self.length = length

    def run(self):
        """ Get stats and save to disk."""
        scraper_main(self.league, self.season, self.length,
                     self.updateProgress)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
