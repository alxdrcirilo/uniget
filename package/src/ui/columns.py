import os
import pickle
from collections import defaultdict

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import *

from package.src.misc.get_columns import get_columns


class TwoListSelection(QWidget):
    signal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select columns")
        self.setWindowIcon(QIcon(":resources/icons/main.png"))
        self.setWindowFlag(Qt.WindowType.Dialog)

        self.initUI()

    def initUI(self):
        self.tabs = QTabWidget()

        fp = os.path.join("data", "columns.pkl")
        self.selection_buttons = defaultdict(list)
        self.up_down_buttons = defaultdict(list)
        self.lists = defaultdict(list)

        if not os.path.exists(fp):
            get_columns()

        # Contains all the data
        self.data = pickle.load(open(fp, "rb"))

        # Formatted specifically for mainwindow.py
        self.d = {}

        for n, (key, val) in enumerate(self.data.items()):
            # Get data for specific category
            d = self.data[key]

            # Populate self.d
            for k, v in val.items():
                self.d[k] = v

            # Create tab
            self.tab = QWidget()

            # Add tab
            self.tabs.addTab(self.tab, "{}. {}".format(n + 1, key))

            # Input and Output QListWidgets
            self.lists[n] = [QListWidget(), QListWidget()]
            for l in self.lists[n]:
                l.setAlternatingRowColors(True)

            # TODO: Add default non-removable columns to output QListWidgets
            # default_columns = ["Entry name",
            #                    "Reviewed",
            #                    "Protein names",
            #                    "Genes",
            #                    "Organism",
            #                    "Length",
            #                    "Mass"]
            # self.lists[n][1].addItems(default_columns)

            self.selection_buttons[n].append(
                QPushButton(">>", objectName="all_select_{}".format(n))
            )
            self.selection_buttons[n].append(
                QPushButton(">", objectName="one_select_{}".format(n))
            )
            self.selection_buttons[n].append(
                QPushButton("<", objectName="one_unsel_{}".format(n))
            )
            self.selection_buttons[n].append(
                QPushButton("<<", objectName="all_unsel_{}".format(n))
            )
            self.up_down_buttons[n].append(
                QPushButton("Up", objectName="up_{}".format(n))
            )
            self.up_down_buttons[n].append(
                QPushButton("Down", objectName="down_{}".format(n))
            )

            vlayout = QVBoxLayout()
            vlayout.addStretch()
            for button in self.selection_buttons[n]:
                vlayout.addWidget(button)
            vlayout.addStretch()

            vlayout_up_down = QVBoxLayout()
            vlayout_up_down.addStretch()
            for button in self.up_down_buttons[n]:
                vlayout_up_down.addWidget(button)

            dialog = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            dialog.setOrientation(Qt.Vertical)
            dialog.accepted.connect(lambda: self.signal.emit())
            dialog.rejected.connect(self.close)
            vlayout_up_down.addWidget(dialog)
            vlayout_up_down.addStretch()

            hlayout = QHBoxLayout(self)
            hlayout.addWidget(self.lists[n][0])
            hlayout.addLayout(vlayout)
            hlayout.addWidget(self.lists[n][1])
            hlayout.addLayout(vlayout_up_down)

            groupbox = QGroupBox("Selection:")
            groupbox.setStyleSheet("QGroupBox {font-weight: bold}")
            groupbox.setLayout(hlayout)
            groupbox_layout = QVBoxLayout()
            groupbox_layout.addWidget(groupbox)

            self.current_tab = n
            self.add_items(items=d)

            self.tab.setLayout(groupbox_layout)

        # Add tabs to widget
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)
        self.setMinimumSize(self.sizeHint())

        # Catch switching tabs
        self.tabs.currentChanged.connect(self.tab_changed)

        # Force first-setting self.x
        self.tab_changed()

        self.update_buttons_status()
        self.connections()

    def tab_changed(self):
        self.current_tab = self.tabs.currentIndex()

        (
            self.button_all_select,
            self.button_one_select,
            self.button_one_unsel,
            self.button_all_unsel,
        ) = self.selection_buttons[self.current_tab]
        self.button_up, self.button_down = self.up_down_buttons[self.current_tab]
        self.input, self.output = self.lists[self.current_tab]

        self.update_buttons_status()
        self.connections()

    def update_buttons_status(self):
        self.button_up.setDisabled(
            not bool(self.output.selectedItems()) or self.output.currentRow() == 0
        )
        self.button_down.setDisabled(
            not bool(self.output.selectedItems())
            or self.output.currentRow() == (self.output.count() - 1)
        )
        self.button_one_select.setDisabled(
            not bool(self.input.selectedItems()) or self.output.currentRow() == 0
        )
        self.button_one_unsel.setDisabled(not bool(self.output.selectedItems()))

    def connections(self):
        self.input.itemSelectionChanged.connect(self.update_buttons_status)
        self.output.itemSelectionChanged.connect(self.update_buttons_status)
        self.button_one_select.clicked.connect(self.button_clicked)
        self.button_one_unsel.clicked.connect(self.button_clicked)
        self.button_all_unsel.clicked.connect(self.button_clicked)
        self.button_all_select.clicked.connect(self.button_clicked)
        self.button_up.clicked.connect(self.button_clicked)
        self.button_down.clicked.connect(self.button_clicked)

    def button_clicked(self):
        button = self.sender()
        name = button.objectName()

        if name == "all_select_{}".format(self.current_tab):
            while self.input.count() > 0:
                self.output.addItem(self.input.takeItem(0))
        if name == "one_select_{}".format(self.current_tab):
            self.output.addItem(self.input.takeItem(self.input.currentRow()))
        if name == "one_unsel_{}".format(self.current_tab):
            self.input.addItem(self.output.takeItem(self.output.currentRow()))
        if name == "all_unsel_{}".format(self.current_tab):
            while self.output.count() > 0:
                self.input.addItem(self.output.takeItem(0))

        if name == "up_{}".format(self.current_tab):
            row = self.output.currentRow()
            item = self.output.takeItem(row)
            self.output.insertItem(row - 1, item)
            self.output.setCurrentRow(row - 1)
        if name == "down_{}".format(self.current_tab):
            row = self.output.currentRow()
            item = self.output.takeItem(row)
            self.output.insertItem(row + 1, item)
            self.output.setCurrentRow(row + 1)

    def add_items(self, items):
        self.lists[self.current_tab][0].addItems(items)

    def get_selected(self):
        selected = []
        for n in self.lists:
            output = self.lists[n][1]
            for i in range(output.count()):
                item = output.item(i)
                selected.append(item.text())

        return selected
