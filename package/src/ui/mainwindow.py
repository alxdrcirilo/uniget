import datetime
import os
import pickle
import platform
import re
import subprocess
import sys
import time
import webbrowser
from functools import partial

import pandas as pd
from PyQt5.QtCore import QRegExp, QSize, QSortFilterProxyModel, Qt
from PyQt5.QtGui import QIcon, QMovie
from PyQt5.QtWidgets import *

from package.src.models.pandas import PandasModel
from package.src.modules.get_data import GetData
from package.src.modules.get_db import GetDBFilters
from package.src.modules.get_families import GetFamiliesFilters
from package.src.modules.get_file import GetUniProt
from package.src.modules.get_pathways import GetPathwaysFilters
from package.src.modules.get_species import GetSpeciesFilters
from package.src.modules.get_subcell import GetSubcellFilters
from package.src.modules.get_tissue import GetTissueFilters
from package.src.qrc.icons import *
from package.src.ui.about import About
from package.src.ui.columns import TwoListSelection
from package.src.ui.tree import ViewTree


class UniProtGet(QMainWindow):
    def __init__(self):
        super().__init__()

        self.default_query = None

        self.initUI()

    def centre(self, window):
        qr = window.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        window.move(qr.topLeft())

    def combo_changed(self, sender: QComboBox):
        if sender.currentText() not in ["All", "Custom"]:
            sender.setStyleSheet(
                "QComboBox {background-color: lightgreen; combobox-popup: 0}"
            )
        elif sender.currentText() == "Custom":
            sender.setStyleSheet(
                "QComboBox {background-color: lightyellow; combobox-popup: 0}"
            )
            try:
                self.db_combo.setToolTip("\n".join(list(self.selected.keys())))
            except AttributeError:
                self.db_combo.setCurrentText("All")
        else:
            sender.setStyleSheet(
                "QComboBox {background-color: None; combobox-popup: a0}"
            )

    def error_table(self, error):
        # Hide table
        self.output_widget.hide()
        self.showNormal()
        self.setFixedSize(self.size)
        self.centre(window=self)

        # Update statusbar
        self.statusBar().clearMessage()
        self.statusBar().setStyleSheet(
            "QStatusBar {"
            "color: #ff4242;"
            "background-color: #d6d6d6"
            "}"
            "QStatusBar QSizeGrip {width: 2px}"
        )
        self.statusBar().showMessage(error, 1000)

        # Disable fetch
        self.statusbar_fetch.setEnabled(False)
        self.statusbar_format.setEnabled(False)

        # Reset progressbar
        self.progressbar.hide()
        self.progressbar.setValue(0)
        self.progressbar.setFixedWidth(100)

        # Reset loading
        self.loading_label.hide()

        # Wait
        app.processEvents()
        time.sleep(1)

        # Reset GUI
        self.reset_gui()

    def download_records(self):
        self.statusBar().removeWidget(self.statusbar_fetch)
        self.statusbar_fetch.deleteLater()
        self.statusBar().removeWidget(self.statusbar_format)
        self.statusbar_format.deleteLater()
        self.statusbar_fetch_loading = QLabel()
        self.statusbar_fetch_loading.setMovie(self.loading_gif)
        self.loading_gif.start()
        self.statusBar().addPermanentWidget(self.statusbar_fetch_loading)

        to_fetch = []
        for row in range(self.row_count):
            if self.table.model().index(row, 0).data(Qt.CheckStateRole) == Qt.Checked:
                to_fetch.append(self.table.model().index(row, 0).data())

        assert to_fetch, QMessageBox.warning(
            self, "Warning", "Databases are still loading.\nWait for completion."
        )

        self.progressbar.show()

        selected_format = self.statusbar_format.currentText()[1:]
        self.uniprot_get = GetUniProt(ids=to_fetch, format=selected_format)
        self.uniprot_get.progress.connect(self.get_uniprot_progress)
        self.uniprot_get.done.connect(self.get_uniprot_done)
        self.uniprot_get.start()

    def force_update(self):
        try:
            combos = [
                self.db_combo,
                self.spec_combo,
                self.family_combo,
                self.pathway_toolbutton,
                self.subcell_combo,
                self.tissue_combo,
            ]
            progressbars = [
                self.db_progressbar,
                self.spec_progressbar,
                self.family_progressbar,
                self.pathway_progressbar,
                self.subcell_progressbar,
                self.tissue_progressbar,
            ]
        except:
            QMessageBox.warning(
                self, "Warning", "Databases are still loading.\nWait for completion."
            )
            return

        self.update_times = pickle.load(open(os.path.join("data", "logs.pkl"), "rb"))

        msg_data = []
        [msg_data.extend([k, v]) for k, v in self.update_times.items()]
        update_table = (
            "\n"
            "        <table border='1'>\n"
            "            <tr>\n"
            "                <th style='padding: 10px'; align='center'>Source</th>\n"
            "                <th style='padding: 10px'; align='center'>Timestamp</th>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "        </table>\n"
            "        "
        ).format(*msg_data)
        msg = QMessageBox.question(
            self,
            "Update databases",
            "<h3>Last update</h3><hr>{}".format(update_table),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if msg == QMessageBox.Yes:
            # Remove data
            dir = "data"
            for file in os.listdir(dir):
                fp = os.path.join(dir, file)
                if os.path.isfile(fp) and "columns.pkl" not in fp:
                    os.remove(fp)

            # Clear and hide combobox
            for combo in combos:
                # If QToolButton, hide only
                try:
                    combo.clear()
                except AttributeError:
                    pass
                combo.hide()

            # Reset and show progressbar
            for progress in progressbars:
                progress.setValue(0)
                progress.show()

            self.get_data()

        else:
            return

    def get_base_filters_groupbox(self):
        groupbox = QGroupBox("Base Filters")
        groupbox.setStyleSheet("QGroupBox {font: bold}")
        layout = QGridLayout()
        layout.setColumnStretch(1, 1)

        self.db_label = QLabel("Databases:")
        self.db_progressbar = QProgressBar()
        self.db_progressbar.setStyleSheet(
            "QProgressBar {border:0px; text-align: center; background:#707070; color:white}"
        )
        layout.addWidget(self.db_label, 1, 0)
        layout.addWidget(self.db_progressbar, 1, 1)

        self.button_db = QPushButton(text="+", objectName="button_db")
        self.button_db.setStyleSheet(
            """QPushButton {border:0px;color:green;font:22px bold;} \
                                        QPushButton:hover {border:0px;color:orange;font:22px bold;}"""
        )

        self.button_db.clicked.connect(lambda: self.get_db_table(self.db_df))
        layout.addWidget(self.button_db, 1, 2)

        self.spec_label = QLabel("Species:")
        self.spec_progressbar = QProgressBar()
        self.spec_progressbar.setStyleSheet(
            "QProgressBar {border:0px;text-align:center;background:#707070;color:white}"
        )

        layout.addWidget(self.spec_label, 2, 0)
        layout.addWidget(self.spec_progressbar, 2, 1)

        self.button_spec = QPushButton(text="+", objectName="button_spec")
        self.button_spec.setStyleSheet(
            """QPushButton {border:0px;color:green;font:22px bold;} \
                                          QPushButton:hover {border:0px;color:orange;font:22px bold;}"""
        )

        self.button_spec.clicked.connect(lambda: self.get_spec_table(self.spec_df))
        layout.addWidget(self.button_spec, 2, 2)

        self.review_label = QLabel("Review status:")
        self.review_check = QCheckBox("Unspecified")
        self.review_check.setTristate(True)
        self.review_check.setCheckState(Qt.Unchecked)
        self.review_check.stateChanged.connect(self.set_review_status)
        layout.addWidget(self.review_label, 3, 0)
        layout.addWidget(self.review_check, 3, 1, Qt.AlignCenter)

        groupbox.setLayout(layout)
        groupbox.setFixedHeight(groupbox.sizeHint().height())

        return groupbox

    def get_columns(self):
        columns = self.selector.get_selected()
        selected_columns = [
            self.selector.d.get(col).replace(" ", "%20") for col in columns
        ]
        selected_columns = "%2C".join(selected_columns)
        # Set default query
        self.set_default_query(format=selected_columns)

    def get_data(self):
        # Refresh GUI
        app.processEvents()

        # Save update times for each database
        try:
            self.update_times = pickle.load(
                open(os.path.join("data", "logs.pkl"), "rb")
            )
        except FileNotFoundError:
            self.update_times = {}

        # Databases
        self.path_databases = os.path.join("data", "databases.pkl")
        if not os.path.exists(self.path_databases):
            self.get_db_filters = GetDBFilters()
            self.get_db_filters.progress.connect(self.get_db_progress)
            self.get_db_filters.done.connect(self.get_db_done)
            self.get_db_filters.start()

            self.update_times["Databases"] = datetime.datetime.now().strftime(
                "%Y-%m-%d&nbsp;&nbsp;&nbsp;&nbsp;%H:%M:%S"
            )
        else:
            self.db_df = pickle.load(open(self.path_databases, "rb"))
            self.get_db_combo()

        # Species
        self.path_species = os.path.join("data", "species.pkl")
        if not os.path.exists(self.path_species):
            self.get_species_filters = GetSpeciesFilters()
            self.get_species_filters.progress.connect(self.get_spec_progress)
            self.get_species_filters.done.connect(self.get_spec_done)
            self.get_species_filters.start()

            self.update_times["Species"] = datetime.datetime.now().strftime(
                "%Y-%m-%d&nbsp;&nbsp;&nbsp;&nbsp;%H:%M:%S"
            )
        else:
            self.spec_df = pickle.load(open(self.path_species, "rb"))
            self.get_spec_combo()

        # Families
        self.path_families = os.path.join("data", "families.pkl")
        if not os.path.exists(self.path_families):
            self.get_families_filters = GetFamiliesFilters()
            self.get_families_filters.progress.connect(self.get_families_progress)
            self.get_families_filters.done.connect(self.get_families_done)
            self.get_families_filters.start()

            self.update_times["Families"] = datetime.datetime.now().strftime(
                "%Y-%m-%d&nbsp;&nbsp;&nbsp;&nbsp;%H:%M:%S"
            )
        else:
            self.family_dict = pickle.load(open(self.path_families, "rb"))
            self.get_families_combo()

        # Pathways
        self.path_pathways = os.path.join("data", "pathways.pkl")
        if not os.path.exists(self.path_pathways):
            self.get_pathways_filters = GetPathwaysFilters()
            self.get_pathways_filters.progress.connect(self.get_pathways_progress)
            self.get_pathways_filters.done.connect(self.get_pathways_done)
            self.get_pathways_filters.start()

            self.update_times["Pathways"] = datetime.datetime.now().strftime(
                "%Y-%m-%d&nbsp;&nbsp;&nbsp;&nbsp;%H:%M:%S"
            )
        else:
            self.pathway_dict = pickle.load(open(self.path_pathways, "rb"))
            self.get_pathways_toolbutton()

        # Subcellular locations
        self.path_subcellular = os.path.join("data", "subcellular.pkl")
        if not os.path.exists(self.path_subcellular):
            self.get_subcell_filters = GetSubcellFilters()
            self.get_subcell_filters.progress.connect(self.get_subcell_progress)
            self.get_subcell_filters.done.connect(self.get_subcell_done)
            self.get_subcell_filters.start()

            self.update_times["Subcellular"] = datetime.datetime.now().strftime(
                "%Y-%m-%d&nbsp;&nbsp;&nbsp;&nbsp;%H:%M:%S"
            )
        else:
            self.subcell_df = pickle.load(open(self.path_subcellular, "rb"))
            self.get_subcell_combo()

        # Tissues
        self.path_tissues = os.path.join("data", "tissues.pkl")
        if not os.path.exists(self.path_tissues):
            self.get_tissue_filters = GetTissueFilters()
            self.get_tissue_filters.progress.connect(self.get_tissue_progress)
            self.get_tissue_filters.done.connect(self.get_tissue_done)
            self.get_tissue_filters.start()

            self.update_times["Tissues"] = datetime.datetime.now().strftime(
                "%Y-%m-%d&nbsp;&nbsp;&nbsp;&nbsp;%H:%M:%S"
            )
        else:
            self.tissue_df = pickle.load(open(self.path_tissues, "rb"))
            self.get_tissue_combo()

        # Log timestamps of database updates
        if not os.path.exists("data"):
            os.makedirs("data")
        with open(os.path.join("data", "logs.pkl"), "wb") as file:
            pickle.dump(self.update_times, file)

        try:
            self.combos = {
                "database": self.db_combo,
                "species": self.spec_combo,
                "methods": self.methods_combo,
                "family": self.family_combo,
                "pathway": self.pathway_toolbutton,
                "location": self.subcell_combo,
                "tissue": self.tissue_combo,
            }
            for k, v in self.combos.items():
                v.setStyleSheet("combobox-popup: 0")
                v.currentTextChanged.connect(partial(self.combo_changed, sender=v))
        except AttributeError:
            pass

    def get_db_combo(self):
        self.groupbox_base_filters.layout().removeWidget(self.db_progressbar)
        self.db_progressbar.hide()
        self.db_combo = QComboBox()
        self.db_combo.setStyleSheet("combobox-popup: 0")
        self.db_combo.addItems(["All", "Custom"])
        self.db_combo.setSizeAdjustPolicy(
            self.db_combo.AdjustToMinimumContentsLengthWithIcon
        )
        self.db_combo.addItems(self.db_df["Abbrev"])
        self.groupbox_base_filters.layout().addWidget(self.db_combo, 1, 1)

    def get_db_done(self, data):
        with open(self.path_databases, "wb") as file:
            pickle.dump(data, file)
        self.db_df = data
        self.get_db_combo()

    def get_db_progress(self, progress):
        self.db_progressbar.setValue(progress)

    def get_db_table(self, df):
        self.db_table = QTableView()
        model = PandasModel(df)
        self.db_table.setModel(model)
        self.db_table.setAlternatingRowColors(True)
        self.db_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.db_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.db_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.db_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)
        height = QDesktopWidget().availableGeometry().height()
        self.db_table.setMaximumHeight(height * 2 // 3)

        self.window = QWidget()
        self.window.setWindowTitle("Database table")
        self.window.setWindowModality(Qt.ApplicationModal)
        dialog = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog.accepted.connect(
            partial(
                self.get_selection, sender=self.db_table, combo=self.db_combo, flag="db"
            )
        )
        dialog.rejected.connect(self.window.close)
        dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        filter_proxy_model.setFilterKeyColumn(1)
        line = QLineEdit()
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.db_table.setModel(filter_proxy_model)
        self.db_table.setSortingEnabled(True)
        self.db_table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        win_layout = QGridLayout()
        win_layout.addWidget(line, 0, 0, 1, 1)
        win_layout.addWidget(dialog, 0, 1, 1, 1)
        win_layout.addWidget(self.db_table, 1, 0, 1, 2)
        self.window.setLayout(win_layout)
        self.window.show()

    def get_experimental_filters_groupbox(self):
        groupbox = QGroupBox("Experimental Filters")
        groupbox.setStyleSheet("QGroupBox {font: bold}")
        layout = QGridLayout()

        self.methods_label = QLabel("Methods:")
        # TODO: test this
        self.methods = {
            "All": "any",
            "Electron microscopy": "em",
            "Fiber diffraction": "fiber",
            "Infrared spectroscopy": "ir",
            "Model": "models",
            "NMR": "nmr",
            "Neutron diffraction": "neutron",
            "X-ray": "x-ray",
        }
        self.methods_combo = QComboBox()
        self.methods_combo.setStyleSheet("combobox-popup: 0")
        self.methods_combo.addItems(list(self.methods.keys()))
        layout.addWidget(self.methods_label, 1, 0)
        layout.addWidget(self.methods_combo, 1, 1)

        layout.addWidget(self.hline, 2, 0, 1, 3)

        self.mass_label = QLabel("Mass:")
        self.mass_spinbox = QSpinBox()
        self.mass_spinbox.setRange(0, int(1e9))
        self.mass_label_unit = QLabel("Da")
        layout.addWidget(self.mass_label, 3, 0)
        layout.addWidget(self.mass_spinbox, 3, 1)
        layout.addWidget(self.mass_label_unit, 3, 2)

        self.length_label = QLabel("Length:")
        self.length_spinbox = QSpinBox()
        self.length_spinbox.setRange(0, int(1e9))
        self.length_label_unit = QLabel("residues")
        layout.addWidget(self.length_label, 4, 0)
        layout.addWidget(self.length_spinbox, 4, 1)
        layout.addWidget(self.length_label_unit, 4, 2)

        groupbox.setLayout(layout)
        groupbox.setFixedHeight(groupbox.sizeHint().height())

        return groupbox

    def get_families_table(self, dict):
        self.window = QWidget()
        self.window.setWindowTitle("Family table")
        self.window.setWindowModality(Qt.ApplicationModal)

        tree = ViewTree(dict)
        tree.setHeaderLabel("Family")
        tree.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        tree.header().setStretchLastSection(False)

        win_layout = QGridLayout()
        win_layout.addWidget(tree, 0, 0, 1, 1)

        self.window.setLayout(win_layout)
        self.window.resize(self.sizeHint().height(), tree.width())
        self.window.show()

    def get_families_done(self, data):
        with open(self.path_families, "wb") as file:
            pickle.dump(data, file)
        self.family_dict = data
        self.get_families_combo()

    def get_families_progress(self, progress):
        self.family_progressbar.setValue(progress)

    def get_families_combo(self):
        self.groupbox_gene_filters.layout().removeWidget(self.family_progressbar)
        self.family_progressbar.hide()
        self.family_combo = QComboBox()

        # TODO
        self.family_combo.setEnabled(False)
        self.button_family.setEnabled(False)
        self.button_family.setStyleSheet(
            """QPushButton {border:0px;color:gray;font:22px bold;}"""
        )

        self.family_combo.setStyleSheet("combobox-popup: 0")
        self.family_combo.addItem("All")
        self.family_combo.addItems(list(self.family_dict.keys()))
        for n, key in enumerate(self.family_dict.keys()):
            self.family_combo.setItemData(n + 1, key, QtCore.Qt.ToolTipRole)
        self.family_combo.setSizeAdjustPolicy(
            self.family_combo.AdjustToMinimumContentsLengthWithIcon
        )
        self.groupbox_gene_filters.layout().addWidget(self.family_combo, 1, 1)

    def get_gene_filters_groupbox(self):
        groupbox = QGroupBox("Genetic Filters")
        groupbox.setStyleSheet("QGroupBox {font: bold}")
        layout = QGridLayout()

        self.family_label = QLabel("Family:")
        self.family_progressbar = QProgressBar()
        self.family_progressbar.setStyleSheet(
            "QProgressBar {border:0px;text-align:center;background:#707070;color:white}"
        )

        layout.addWidget(self.family_label, 1, 0)
        layout.addWidget(self.family_progressbar, 1, 1)

        self.button_family = QPushButton(text="+", objectName="button_family")
        self.button_family.setStyleSheet(
            """QPushButton {border:0px;color:green;font:22px bold;} \
                                            QPushButton:hover {border:0px;color:orange;font:22px bold;}"""
        )

        self.button_family.clicked.connect(
            lambda: self.get_families_table(self.family_dict)
        )
        layout.addWidget(self.button_family, 1, 2)

        self.gene_label = QLabel("Gene:")
        self.gene_input = QLineEdit()
        layout.addWidget(self.gene_label, 2, 0)
        layout.addWidget(self.gene_input, 2, 1)

        hline_1 = QFrame()
        hline_1.setFrameShape(QFrame.HLine)
        hline_1.setFrameShadow(QFrame.Sunken)
        layout.addWidget(hline_1, 4, 0, 1, 3)

        self.pathway_label = QLabel("Pathway:")
        self.pathway_progressbar = QProgressBar()
        self.pathway_progressbar.setStyleSheet(
            "QProgressBar {border:0px;text-align:center;background:#707070;color:white}"
        )

        layout.addWidget(self.pathway_label, 5, 0)
        layout.addWidget(self.pathway_progressbar, 5, 1)

        self.button_pathway = QPushButton(text="+", objectName="button_pathway")
        self.button_pathway.setStyleSheet(
            """QPushButton {border:0px;color:green;font:22px bold;} \
                                             QPushButton:hover {border:0px;color:orange;font:22px bold;}"""
        )

        self.button_pathway.clicked.connect(
            lambda: self.get_pathways_table(self.pathway_dict)
        )

        # TODO
        self.button_pathway.setEnabled(False)
        self.button_pathway.setStyleSheet(
            """QPushButton {border:0px;color:gray;font:22px bold;}"""
        )

        layout.addWidget(self.button_pathway, 5, 2)

        hline_2 = QFrame()
        hline_2.setFrameShape(QFrame.HLine)
        hline_2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(hline_2, 6, 0, 1, 3)

        self.subcell_label = QLabel("Subcellular loc:")
        self.subcell_progressbar = QProgressBar()
        self.subcell_progressbar.setStyleSheet(
            "QProgressBar {border:0px;text-align:center;background:#707070;color:white}"
        )

        self.button_subcell = QPushButton(text="+", objectName="button_subcell")
        self.button_subcell.setStyleSheet(
            """QPushButton {border:0px;color:green;font:22px bold;} \
                                             QPushButton:hover {border:0px;color:orange;font:22px bold;}"""
        )

        self.button_subcell.clicked.connect(
            lambda: self.get_subcell_table(self.subcell_df[["AC", "ID"]])
        )

        self.tissue_label = QLabel("Tissue:")
        self.tissue_progressbar = QProgressBar()
        self.tissue_progressbar.setStyleSheet(
            "QProgressBar {border:0px;text-align:center;background:#707070;color:white}"
        )

        self.button_tissue = QPushButton(text="+", objectName="tissue_subcell")
        self.button_tissue.setStyleSheet(
            """QPushButton {border:0px;color:green;font:22px bold;} \
                                            QPushButton:hover {border:0px;color:orange;font:22px bold;}"""
        )

        self.button_tissue.clicked.connect(
            lambda: self.get_tissue_table(self.tissue_df[["AC", "ID"]])
        )

        layout.addWidget(self.subcell_label, 7, 0)
        layout.addWidget(self.subcell_progressbar, 7, 1)
        layout.addWidget(self.button_subcell, 7, 2)
        layout.addWidget(self.tissue_label, 8, 0)
        layout.addWidget(self.tissue_progressbar, 8, 1)
        layout.addWidget(self.button_tissue, 8, 2)

        groupbox.setLayout(layout)
        groupbox.setFixedHeight(groupbox.sizeHint().height())

        # TODO
        self.gene_input.setEnabled(False)

        return groupbox

    def get_pathways_toolbutton(self):
        self.groupbox_gene_filters.layout().removeWidget(self.pathway_progressbar)
        self.pathway_progressbar.hide()
        self.pathway_toolbutton = QToolButton()
        self.pathway_toolbutton.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.pathway_toolbutton.setFixedWidth(self.gene_input.size().width())
        self.pathway_toolbutton.setPopupMode(1)
        self.pathway_toolbutton.setText("All")

        def rename(s: str) -> str:
            # Renaming exceptions (e.g. "LOS ...", "mRNA", "DNA")
            pattern = r"^(.*)(\w+)([DR]NA)(.*)$"
            match = re.search(pattern, s)
            if match:
                m = [match.group(n) for n in range(1, 5)]
                # e.g. "rna"
                m[2] = m[2].upper()
                # e.g. "aminoacyl-tRNA"
                if m[0]:
                    m[0] = m[0].capitalize()
                return "".join(m)
            if s[0].isupper():
                return s
            else:
                return s.capitalize()

        def set_pathway_toolbutton_text(v):
            return lambda: self.pathway_toolbutton.setText(v[:15] + "...")

        def set_pathway_toolbutton_tooltip(v):
            return lambda: self.pathway_toolbutton.setToolTip(v)

        def fill_menu(d: dict, m: QMenu):
            for k, vals in d.items():
                root = rename(s=k)
                sub_menu = m.addMenu(root)
                for v in vals:
                    if type(v) is dict and list(v.values())[0]:
                        fill_menu(d=v, m=sub_menu)
                    else:
                        if type(v) is dict and not list(v.values())[0]:
                            v = list(v.keys())[0]
                        if type(v) is str:
                            pass

                        pathway = rename(s=v)
                        action = sub_menu.addAction(pathway)
                        action.triggered.connect(set_pathway_toolbutton_text(pathway))
                        action.triggered.connect(
                            set_pathway_toolbutton_tooltip(pathway)
                        )

        menu = QMenu()
        fill_menu(d=self.pathway_dict.get("collection"), m=menu)
        self.pathway_toolbutton.setMenu(menu)
        self.groupbox_gene_filters.layout().addWidget(self.pathway_toolbutton, 5, 1)

    def get_pathways_table(self, df):
        self.pathway_table = QTableView()
        model = PandasModel(df)
        self.pathway_table.setModel(model)
        self.pathway_table.setAlternatingRowColors(True)
        self.pathway_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.pathway_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.pathway_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.pathway_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.Stretch
        )
        height = QDesktopWidget().availableGeometry().height()
        self.pathway_table.setMaximumHeight(height * 2 // 3)

        self.window = QWidget()
        self.window.setWindowTitle("Pathways table")
        self.window.setWindowModality(Qt.ApplicationModal)
        dialog = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog.accepted.connect(
            partial(
                self.get_selection,
                sender=self.pathway_table,
                combo=self.pathway_toolbutton,
                flag="pathway",
            )
        )
        dialog.rejected.connect(self.window.close)
        dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Filter by "AC"
        filter_proxy_model.setFilterKeyColumn(0)
        line = QLineEdit()
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.pathway_table.setModel(filter_proxy_model)

        win_layout = QGridLayout()
        win_layout.addWidget(line, 0, 0, 1, 1)
        win_layout.addWidget(dialog, 0, 1, 1, 1)
        win_layout.addWidget(self.pathway_table, 1, 0, 1, 2)
        self.window.setLayout(win_layout)
        self.window.show()

    def get_pathways_done(self, data):
        with open(self.path_pathways, "wb") as file:
            pickle.dump(data, file)
        self.pathway_dict = data
        self.get_pathways_toolbutton()

    def get_pathways_progress(self, progress):
        self.pathway_progressbar.setValue(progress)

    # TODO
    # def get_pathway_query(self, id: str):
    #     keys = ["HI", "HP"]
    #     data = self.master.get(id)
    #     for key in keys:
    #         if key in data.keys():
    #             parent = data.get(key)
    #             parent_key = re.search(pattern=r";.*", string=parent).group(0)[2:-1]
    #             parent_uid = re.search(pattern=r".*;", string=parent).group(0).strip(";")
    #             parent_uid_to_int = int("".join(re.findall(pattern=r"\d", string=parent_uid)))
    #             print(parent_key, parent_uid, parent_uid_to_int)
    #             uid.insert(0, str(parent_uid_to_int))
    #             get_parent(id=parent_key)

    def get_query(self):
        query = self.input.text()
        try:
            assert len(query) > 0
        except AssertionError:
            error = QErrorMessage(self)
            error.setWindowTitle("Warning")
            error.showMessage("Query cannot be empty!")
            return

        self.search_button.setEnabled(False)
        self.statusbar_record_count.setText("")
        self.input.setEnabled(False)
        self.groupbox_base_filters.setEnabled(False)
        self.groupbox_experimental_filters.setEnabled(False)
        self.groupbox_gene_filters.setEnabled(False)
        self.statusBar().clearMessage()

        # Queries
        query_uniprot = query.replace(" ", "%20")

        db_query = self.db_combo.currentText()
        if db_query != "All":
            query_uniprot += f"%20AND%20database:{db_query}"
        spec_query = self.spec_combo.currentText()
        if spec_query != "All":
            query_uniprot += f"%20AND%20organism_idnu:{spec_query}"
        methods_query = self.methods_combo.currentText()
        if methods_query != "All":
            query_uniprot += f"%20AND%20method:{self.methods[methods_query]}"
        mass_query = self.mass_spinbox.value()
        if mass_query > 0:
            query_uniprot += f"%20AND%20mass:[{mass_query}%20TO%20*]"
        length_query = self.length_spinbox.value()
        if length_query > 0:
            query_uniprot += f"%20AND%20length:[{length_query}%20TO%20*]"
        family_query = self.family_combo.currentText()
        # TODO
        # if family_query != "All":
        #     family_query = family_query.replace(" ", "+")
        #     query_uniprot += f'%20AND%20family:"{family_query}"'
        gene_query = self.gene_input.text()
        if gene_query:
            query_uniprot += f"%20AND%20gene:{gene_query}"
        # TODO
        # pathway_query = self.pathway_toolbutton.text()
        # if pathway_query != "All":
        #     self.selected_pathway = pathway_query.lower() + "."
        #     print(self.selected_pathway)
        #     formatted_pathway_query = self.get_pathway_query(id=pathway_query)
        #     query_uniprot += f"%20AND%20pathway:{formatted_pathway_query}"
        subcell_query = self.subcell_combo.currentText()
        if subcell_query != "All":
            query_uniprot += f"%20AND%20locations%3A(location%3A{subcell_query})"
        tissue_query = self.tissue_combo.currentText()
        if tissue_query != "All":
            query_uniprot += f"%20AND%20tissue:{tissue_query}"

        self.loading_gif = QMovie(":resources/icons/loading.gif")
        self.loading_gif.setScaledSize(QSize(20, 20))
        self.loading_label.setMovie(self.loading_gif)
        self.loading_label.show()
        self.loading_gif.start()

        self.gen_table = GetData(query=query_uniprot, columns=self.default_query)
        self.gen_table.done.connect(self.update_table)
        self.gen_table.error.connect(self.error_table)
        self.gen_table.progress.connect(self.set_progress)
        self.progressbar.show()
        self.gen_table.start()

    def get_selection(self, sender: QTableView, combo: QComboBox, flag: str):
        # name: row
        self.selected = {}
        for row in range(sender.model().rowCount()):
            if sender.model().index(row, 0).data(Qt.CheckStateRole) == Qt.Checked:
                self.selected[sender.model().index(row, 0).data()] = row
        self.window.close()

        if len(self.selected) > 1:
            combo.setCurrentText("Custom")
        elif len(self.selected) == 1:
            row_index = list(self.selected.values())[0]
            idx = int()
            if flag == "db":
                idx = 1
            if flag == "spec":
                idx = 0
            if flag == "subcell":
                idx = 0
            combo.setCurrentText(sender.model().index(row_index, idx).data())

        # DEBUG
        print(self.selected)

    def get_spec_combo(self):
        self.groupbox_base_filters.layout().removeWidget(self.spec_progressbar)
        self.spec_progressbar.hide()
        self.spec_combo = QComboBox()
        self.spec_combo.setStyleSheet("combobox-popup: 0")
        self.spec_combo.addItem("All")
        self.spec_combo.setSizeAdjustPolicy(
            self.spec_combo.AdjustToMinimumContentsLengthWithIcon
        )
        self.spec_combo.addItems([str(k) for k in self.spec_df.index])
        self.groupbox_base_filters.layout().addWidget(self.spec_combo, 2, 1)

    def get_spec_table(self, df):
        self.spec_table = QTableView()
        model = PandasModel(df)
        self.spec_table.setModel(model)
        self.spec_table.setAlternatingRowColors(True)
        self.spec_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.spec_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        # TODO
        # self.spec_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        # self.spec_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        height = QDesktopWidget().availableGeometry().height()
        self.spec_table.setMaximumHeight(height * 2 // 3)

        self.window = QWidget()
        self.window.setWindowTitle("Species table")
        self.window.setWindowModality(Qt.ApplicationModal)
        dialog = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog.accepted.connect(
            partial(
                self.get_selection,
                sender=self.spec_table,
                combo=self.spec_combo,
                flag="spec",
            )
        )
        dialog.rejected.connect(self.window.close)
        dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        # Filter by "Scientific name"
        filter_proxy_model.setFilterKeyColumn(3)
        line = QLineEdit()
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.spec_table.setModel(filter_proxy_model)
        # Sorting disabled for spec_table (too slow)
        # self.spec_table.setSortingEnabled(True)
        # self.spec_table.sortByColumn(3, Qt.SortOrder.AscendingOrder)

        win_layout = QGridLayout()
        win_layout.addWidget(line, 0, 0, 1, 1)
        win_layout.addWidget(dialog, 0, 1, 1, 1)
        win_layout.addWidget(self.spec_table, 1, 0, 1, 2)
        self.window.setLayout(win_layout)
        self.window.show()

    def get_spec_done(self, data):
        with open(self.path_species, "wb") as file:
            pickle.dump(data, file)
        self.spec_df = data
        self.get_spec_combo()

    def get_spec_progress(self, progress):
        self.spec_progressbar.setValue(progress)

    def get_subcell_combo(self):
        self.groupbox_gene_filters.layout().removeWidget(self.subcell_progressbar)
        self.subcell_progressbar.hide()
        self.subcell_combo = QComboBox()
        self.subcell_combo.setStyleSheet("combobox-popup: 0")
        self.subcell_combo.addItem("All")
        self.subcell_combo.setSizeAdjustPolicy(
            self.subcell_combo.AdjustToMinimumContentsLengthWithIcon
        )
        self.subcell_combo.addItems(sorted(self.subcell_df.index.tolist()))
        self.groupbox_gene_filters.layout().addWidget(self.subcell_combo, 7, 1)

    def get_subcell_done(self, data):
        with open(self.path_subcellular, "wb") as file:
            pickle.dump(data, file)
        self.subcell_df = data

        self.get_subcell_combo()

    def get_subcell_progress(self, progress):
        self.subcell_progressbar.setValue(progress)

    def get_subcell_table(self, df):
        self.subcell_table = QTableView()
        model = PandasModel(df)
        self.subcell_table.setModel(model)
        self.subcell_table.setAlternatingRowColors(True)
        self.subcell_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.subcell_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.subcell_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        height = QDesktopWidget().availableGeometry().height()
        self.subcell_table.setMaximumHeight(height * 2 // 3)

        self.window = QWidget()
        self.window.setWindowTitle("Subcellular location table")
        self.window.setWindowModality(Qt.ApplicationModal)
        dialog = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog.accepted.connect(
            partial(
                self.get_selection,
                sender=self.subcell_table,
                combo=self.subcell_combo,
                flag="subcell",
            )
        )
        dialog.rejected.connect(self.window.close)
        dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        filter_proxy_model.setFilterKeyColumn(0)
        line = QLineEdit()
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.subcell_table.setModel(filter_proxy_model)
        self.subcell_table.setSortingEnabled(True)
        self.subcell_table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        win_layout = QGridLayout()
        win_layout.addWidget(line, 0, 0, 1, 1)
        win_layout.addWidget(dialog, 0, 1, 1, 1)
        win_layout.addWidget(self.subcell_table, 1, 0, 1, 2)
        self.window.setLayout(win_layout)
        self.window.show()

    def get_tissue_combo(self):
        self.groupbox_gene_filters.layout().removeWidget(self.tissue_progressbar)
        self.tissue_progressbar.hide()
        self.tissue_combo = QComboBox()
        self.tissue_combo.setStyleSheet("combobox-popup: 0")
        self.tissue_combo.addItem("All")
        self.tissue_combo.setSizeAdjustPolicy(
            self.tissue_combo.AdjustToMinimumContentsLengthWithIcon
        )
        self.tissue_combo.addItems(sorted(self.tissue_df.index.tolist()))
        self.groupbox_gene_filters.layout().addWidget(self.tissue_combo, 8, 1)

    def get_tissue_done(self, data):
        with open(self.path_tissues, "wb") as file:
            pickle.dump(data, file)
        self.tissue_df = data

        self.get_tissue_combo()

    def get_tissue_progress(self, progress):
        self.tissue_progressbar.setValue(progress)

    def get_tissue_table(self, df):
        self.tissue_table = QTableView()
        model = PandasModel(df)
        self.tissue_table.setModel(model)
        self.tissue_table.setAlternatingRowColors(True)
        self.tissue_table.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.tissue_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.tissue_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.Stretch
        )
        height = QDesktopWidget().availableGeometry().height()
        self.tissue_table.setMaximumHeight(height * 2 // 3)

        self.window = QWidget()
        self.window.setWindowTitle("Tissue table")
        self.window.setWindowModality(Qt.ApplicationModal)
        dialog = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        dialog.accepted.connect(
            partial(
                self.get_selection,
                sender=self.tissue_table,
                combo=self.tissue_combo,
                flag="tissue",
            )
        )
        dialog.rejected.connect(self.window.close)
        dialog.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        filter_proxy_model = QSortFilterProxyModel()
        filter_proxy_model.setSourceModel(model)
        filter_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        filter_proxy_model.setFilterKeyColumn(1)
        line = QLineEdit()
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line.textChanged.connect(filter_proxy_model.setFilterRegExp)
        self.tissue_table.setModel(filter_proxy_model)
        self.tissue_table.setSortingEnabled(True)
        self.tissue_table.sortByColumn(0, Qt.SortOrder.AscendingOrder)

        win_layout = QGridLayout()
        win_layout.addWidget(line, 0, 0, 1, 1)
        win_layout.addWidget(dialog, 0, 1, 1, 1)
        win_layout.addWidget(self.tissue_table, 1, 0, 1, 2)
        self.window.setLayout(win_layout)
        self.window.show()

    def get_uniprot_done(self):
        self.statusBar().removeWidget(self.statusbar_fetch_loading)
        self.statusbar_fetch_loading.deleteLater()
        self.statusbar_fetch = QPushButton("\tExport")
        self.statusbar_fetch.setToolTip("Fetch the selected records")
        self.statusbar_fetch.setIcon(QIcon.fromTheme("document-save"))
        self.statusbar_fetch.setStyleSheet(
            "QPushButton::hover {" "border:2px solid green;" "border-style:ridge" "}"
        )
        self.statusbar_fetch.clicked.connect(self.download_records)
        self.statusBar().addPermanentWidget(self.statusbar_fetch)

        # Add format selector (.fasta or .gbk)
        self.statusbar_format = QComboBox()
        self.statusbar_format.addItems([".fasta", ".gff", ".rdf/xml", ".txt", ".xml"])
        self.statusBar().addPermanentWidget(self.statusbar_format)

        self.progressbar.hide()
        self.progressbar.setValue(0)

    def get_uniprot_progress(self, value):
        progress_id, progress_value = value
        self.progressbar.setValue(int(progress_value))

    def initUI(self):
        self.hline = QFrame()
        self.hline.setFrameShape(QFrame.HLine)
        self.hline.setFrameShadow(QFrame.Sunken)

        self.statusBar().setStyleSheet(
            "QStatusBar {background-color: #d6d6d6}" "QStatusBar QSizeGrip {width: 2px}"
        )

        self.progressbar = QProgressBar(self)
        self.progressbar.setFixedWidth(100)
        self.progressbar.setValue(0)
        self.progressbar.setStyleSheet(
            "QProgressBar {"
            "border: 1px solid #909090;"
            "background-color: #707070;"
            "color: white;"
            "text-align:center;"
            "height: 16px"
            "}"
            "QProgressBar::chunk {"
            "background-color: #009900;"
            "}"
        )
        self.statusBar().addPermanentWidget(self.progressbar)
        self.progressbar.hide()

        self.statusbar_record_count = QLabel()
        self.statusBar().addWidget(self.statusbar_record_count)

        self.statusbar_fetch = QPushButton("\tExport")
        self.statusbar_fetch.setToolTip("Fetch the selected records")
        self.statusbar_fetch.setIcon(QIcon.fromTheme("document-save"))
        self.statusbar_fetch.setStyleSheet(
            "QPushButton::hover {" "border:2px solid green;" "border-style:ridge" "}"
        )
        self.statusbar_fetch.clicked.connect(self.download_records)
        self.statusbar_fetch.setEnabled(False)
        self.statusbar_format = QComboBox()
        self.statusbar_format.addItems([".fasta", ".gff", ".rdf/xml", ".txt", ".xml"])
        self.statusbar_format.setEnabled(False)
        self.statusBar().addPermanentWidget(self.statusbar_fetch)
        self.statusBar().addPermanentWidget(self.statusbar_format)

        self.input = QLineEdit()
        self.input.returnPressed.connect(self.get_query)
        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.get_query)

        self.toolbutton = QToolButton()
        self.toolbutton.setArrowType(Qt.DownArrow)
        self.toolbutton.setPopupMode(QToolButton.InstantPopup)
        self.toolbutton.setAutoRaise(True)
        self.toolbutton.setStyleSheet("QToolButton::menu-indicator{image:none;};")
        self.set_extra_menu()

        self.loading_label = QLabel()
        self.loading_label.hide()
        self.table_groupbox = QGroupBox("Data")
        self.table_groupbox.setStyleSheet("QGroupBox {font: bold}")
        self.table = QTableView()
        layout = QVBoxLayout()
        layout.addWidget(self.table)
        self.table_groupbox.setLayout(layout)

        self.layout = QGridLayout()

        self.search_groupbox = QGroupBox("Input")
        self.search_groupbox.setStyleSheet("QGroupBox {font: bold}")
        layout = QHBoxLayout()
        layout.addWidget(self.input)
        layout.addWidget(self.search_button)
        layout.addWidget(self.toolbutton)
        layout.addWidget(self.loading_label)
        self.search_groupbox.setLayout(layout)
        self.search_groupbox.setFixedHeight(self.search_groupbox.sizeHint().height())

        layout = QVBoxLayout()
        layout.addWidget(self.search_groupbox)
        self.groupbox_base_filters = self.get_base_filters_groupbox()
        layout.addWidget(self.groupbox_base_filters)
        self.groupbox_experimental_filters = self.get_experimental_filters_groupbox()
        layout.addWidget(self.groupbox_experimental_filters)
        self.groupbox_gene_filters = self.get_gene_filters_groupbox()
        layout.addWidget(self.groupbox_gene_filters)
        self.input_widget = QWidget()
        self.input_widget.setLayout(layout)
        self.input_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        layout = QVBoxLayout()
        layout.addWidget(self.table_groupbox)
        self.output_widget = QWidget()
        self.output_widget.setMinimumWidth(800)
        self.output_widget.setLayout(layout)
        self.output_widget.hide()

        self.layout = QHBoxLayout()
        self.layout.addWidget(self.input_widget, alignment=Qt.AlignTop | Qt.AlignLeft)
        self.layout.addWidget(self.output_widget)
        master_widget = QWidget()
        master_widget.setLayout(self.layout)

        self.setCentralWidget(master_widget)
        self.size = self.sizeHint()
        self.setFixedSize(self.size)
        self.setWindowTitle("UniGet")
        self.setWindowIcon(QIcon(":resources/icons/main.ico"))
        self.centre(window=self)
        self.show()

        self.get_data()

    def reset_gui(self):
        self.search_button.setEnabled(True)
        self.input.setEnabled(True)
        self.groupbox_base_filters.setEnabled(True)
        self.groupbox_experimental_filters.setEnabled(True)
        self.groupbox_gene_filters.setEnabled(True)
        try:
            # When importing from file, this should not be called
            self.loading_gif.stop()
            self.loading_label.hide()
        except:
            pass

        app.processEvents()
        self.statusBar().setStyleSheet(
            "QStatusBar {"
            "color: black;"
            "background-color: #d6d6d6"
            "}"
            "QStatusBar QSizeGrip {width: 2px}"
        )

    def show_query(self):
        self.combos = {
            "database": self.db_combo,
            "species": self.spec_combo,
            "methods": self.methods_combo,
            "family": self.family_combo,
            "pathway": self.pathway_toolbutton,
            "location": self.subcell_combo,
            "tissue": self.tissue_combo,
        }
        msg_data = []
        [
            msg_data.extend(
                [
                    k.capitalize(),
                    [v.currentText() if type(v) is QComboBox else v.text()][0],
                ]
            )
            for k, v in self.combos.items()
        ]
        update_table = (
            "\n"
            "        <table border='1'>\n"
            "            <tr>\n"
            "                <th style='padding: 10px'; align='center'>Source</th>\n"
            "                <th style='padding: 10px'; align='center'>Value</th>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "            <tr>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "                <td style='padding: 2px'; align='center'>{}</td>\n"
            "            </tr>\n"
            "        </table>\n"
            "        "
        ).format(*msg_data)
        msg = QMessageBox.question(
            self,
            "Query table",
            "<h3>Query</h3><hr>{}".format(update_table),
            QMessageBox.Close,
        )

    def set_default_query(self, format: str):
        self.default_query = format
        self.selector.close()

    def set_extra_menu(self):
        menu = QMenu(self)

        self.open_action = QAction("Open", self)
        self.open_action.setIcon(QIcon.fromTheme("document-open"))
        self.save_action = QAction("Save", self)
        self.save_action.setIcon(QIcon.fromTheme("document-save"))

        edit_menu = QMenu("Edit", self)
        edit_menu.setIcon(QIcon.fromTheme("accessories-text-editor"))
        self.select_all_action = QAction("Select all", self)
        edit_menu.addAction(self.select_all_action)
        self.select_none_action = QAction("Unselect all", self)
        edit_menu.addAction(self.select_none_action)
        edit_menu.addSeparator()
        self.open_downloads_action = QAction("Open downloads directory", self)
        edit_menu.addAction(self.open_downloads_action)

        view_menu = QMenu("View", self)
        view_menu.setIcon(QIcon.fromTheme("edit-find"))
        self.view_query_action = QAction("View query", self)
        view_menu.addAction(self.view_query_action)

        self.about_action = QAction("About", self)
        self.about_action.setIcon(QIcon.fromTheme("help-about"))
        self.feedback_action = QAction("Feedback", self)
        self.feedback_action.setIcon(QIcon.fromTheme("mail-send"))
        self.exit_action = QAction("Exit", self)
        self.exit_action.setIcon(QIcon.fromTheme("application-exit"))

        settings_menu = QMenu("Settings", self)
        settings_menu.setIcon(QIcon.fromTheme("emblem-system"))
        self.select_columns_action = QAction("Select columns", self)
        settings_menu.addAction(self.select_columns_action)
        self.select_columns_action.setShortcut("Alt+C")
        self.select_columns_action.triggered.connect(self.toolbutton_click)
        self.update_db_action = QAction("Update databases", self)
        settings_menu.addAction(self.update_db_action)
        self.update_db_action.setShortcut("Alt+U")
        self.update_db_action.triggered.connect(self.toolbutton_click)

        menu.addAction(self.open_action)
        menu.addAction(self.save_action)
        menu.addAction(self.exit_action)
        menu.addSeparator()
        menu.addMenu(edit_menu)
        menu.addMenu(view_menu)
        menu.addMenu(settings_menu)
        menu.addSeparator()
        menu.addAction(self.feedback_action)
        menu.addAction(self.about_action)

        self.open_action.triggered.connect(self.toolbutton_click)
        self.open_action.setShortcut("Ctrl+O")
        self.save_action.triggered.connect(self.toolbutton_click)
        self.save_action.setShortcut("Ctrl+S")
        self.select_all_action.triggered.connect(self.toolbutton_click)
        self.select_all_action.setShortcut("Ctrl+A")
        self.select_none_action.triggered.connect(self.toolbutton_click)
        self.select_none_action.setShortcut("Ctrl+Z")
        self.open_downloads_action.triggered.connect(self.toolbutton_click)
        self.open_downloads_action.setShortcut("Ctrl+D")
        self.view_query_action.triggered.connect(self.toolbutton_click)
        self.view_query_action.setShortcut("Alt+Q")
        self.about_action.triggered.connect(self.toolbutton_click)
        self.about_action.setShortcut("Alt+A")
        self.feedback_action.triggered.connect(self.toolbutton_click)
        self.feedback_action.setShortcut("Alt+F")
        self.exit_action.triggered.connect(self.toolbutton_click)
        self.exit_action.setShortcut("Ctrl+Q")

        self.toolbutton.setMenu(menu)

    def set_progress(self, value: int):
        self.progressbar.setValue(value)

    def set_review_status(self):
        try:
            status, colors = ["Unspecified", "Unreviewed", "Reviewed"], [
                "black",
                "red",
                "green",
            ]
            current_state = self.review_check.checkState()

            # Set filtering based on review status
            # ^/&: start/end delimiters
            self.proxy_model.setFilterRegExp(
                QRegExp(
                    ""
                    if status[current_state] == "Unspecified"
                    else "^" + status[current_state] + "$",
                    Qt.CaseInsensitive,
                )
            )
            self.statusbar_record_count.setText(
                f" {self.table.model().rowCount()} records"
            )

            self.review_check.setText(status[current_state])
            self.review_check.setStyleSheet("color:{}".format(colors[current_state]))

        except AttributeError:
            if self.review_check.checkState() != Qt.Unchecked:
                error = QErrorMessage(self)
                error.setWindowTitle("Warning")
                error.showMessage("Cannot set review status when no data is loaded!")
            self.review_check.setCheckState(Qt.Unchecked)

    def toolbutton_click(self):
        if self.sender() is self.open_action:
            try:
                name = QFileDialog.getOpenFileName(
                    self, "Open file", filter="csv(*.csv)"
                )
                self.df = pd.read_csv(name[0], index_col=0)
                row_count = self.df.shape[0]
                self.update_table((self.df, row_count))
                QMessageBox.information(self, "Info", "File successfully imported!")
            except:
                QMessageBox.warning(self, "Warning", "Unable to import data!")

        if self.sender() is self.save_action:
            try:
                name = QFileDialog.getSaveFileName(
                    self, "Save file", filter="csv(*.csv)"
                )
                self.df.to_csv(name[0], index=False)
                QMessageBox.information(self, "Info", "File successfully saved!")
            except:
                QMessageBox.warning(self, "Warning", "Unable to save data!")

        if self.sender() is self.exit_action:
            sys.exit(0)

        if self.sender() is self.select_all_action:
            for row in range(self.row_count):
                index = self.table.model().index(row, 0)
                self.table.model().setData(index, Qt.Checked, Qt.CheckStateRole)

        if self.sender() is self.select_none_action:
            for row in range(self.row_count):
                index = self.table.model().index(row, 0)
                self.table.model().setData(index, Qt.Unchecked, Qt.CheckStateRole)

        if self.sender() is self.open_downloads_action:
            path = os.path.abspath(os.path.join("export"))
            if not os.path.exists(path):
                os.makedirs(path)

            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])

        if self.sender() is self.view_query_action:
            self.show_query()

        if self.sender() is self.select_columns_action:
            self.selector = TwoListSelection()
            self.selector.setWindowModality(Qt.ApplicationModal)
            self.selector.signal.connect(self.get_columns)
            self.centre(window=self.selector)
            self.selector.show()

        if self.sender() is self.update_db_action:
            self.force_update()

        if self.sender() is self.feedback_action:
            recipient = "alxdrcirilo@outlook.com"
            subject = "Feedback: UniGet"
            webbrowser.open("mailto:?to=" + recipient + "&subject=" + subject, new=1)

        if self.sender() is self.about_action:
            self.about_widget = About()
            self.about_widget.setWindowModality(Qt.ApplicationModal)
            self.centre(window=self.about_widget)
            self.about_widget.show()

    def update_table(self, data):
        # Done with fetching data, hide progressbar
        self.progressbar.hide()
        self.progressbar.setFixedWidth(100)

        self.statusBar().clearMessage()
        self.df, self.row_count = data
        self.statusbar_record_count.setText("  {} records".format(self.row_count))

        model = PandasModel(self.df)
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(model)
        # Filter review status of record
        self.proxy_model.setFilterKeyColumn(1)
        self.table.setModel(self.proxy_model)
        self.table.setSortingEnabled(True)
        self.table.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(150)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        self.reset_gui()
        self.output_widget.show()
        self.setMinimumSize(self.sizeHint())
        self.setMaximumSize(QWIDGETSIZE_MAX, QWIDGETSIZE_MAX)
        self.centre(window=self)

        self.statusbar_fetch.setEnabled(True)
        self.statusbar_format.setEnabled(True)
        self.statusBar().setStyleSheet(
            "QStatusBar {background-color: #d6d6d6}" "QStatusBar QSizeGrip {width: 2px}"
        )


def run():
    global app
    app = QApplication(sys.argv)
    upg = UniProtGet()
    sys.exit(app.exec_())
