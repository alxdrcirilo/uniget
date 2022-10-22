from PyQt5.QtCore import QAbstractTableModel, Qt
from PyQt5.QtGui import QBrush, QColor, QPixmap


class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        QAbstractTableModel.__init__(self)
        self._data = data

        try:
            # Color (normalized) for the length (bp) and mass (Da) of each record
            self.length_normalized_color = (
                self._data["Length"].values / max(self._data["Length"].values) * 100
            )
            self.mass_normalized_color = (
                self._data["Mass"].values / max(self._data["Mass"].values) * 100
            )
        except:
            pass

        # Set state of checkboxes
        self._checked = [
            [False for i in range(self.columnCount())] for j in range(self.rowCount())
        ]

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parent=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        data = self._data.iloc[index.row(), index.column()]
        if index.isValid():
            if role == Qt.ToolTipRole:
                text = str(data).replace(") (", ")\n(")
                return text
            if role == Qt.BackgroundRole and index.column() == 0:
                return QBrush(QColor("#f1f0e8"))
            if (
                role == Qt.BackgroundRole
                and index.column() == 6
                and self._data.columns[6] == "Length"
            ):
                return QBrush(
                    QColor(
                        100, 100, 255, int(self.length_normalized_color[index.row()])
                    )
                )
            if (
                role == Qt.BackgroundRole
                and index.column() == 7
                and self._data.columns[7] == "Mass"
            ):
                return QBrush(
                    QColor(255, 100, 100, int(self.mass_normalized_color[index.row()]))
                )
            if role == Qt.ForegroundRole and data == "Unreviewed":
                return QBrush(QColor("#d62d20"))
            if role == Qt.ForegroundRole and data == "Reviewed":
                return QBrush(QColor("#008744"))
            if role == Qt.DisplayRole:
                return str(data)
            if role == Qt.TextAlignmentRole:
                return Qt.AlignCenter
            # Add checkboxes to first column to allow selection of IDs
            if role == Qt.CheckStateRole and index.column() == 0:
                return self._checked[index.row()][index.column()]
        return None

    def flags(self, index):
        if index.isValid():
            if index.column() == 0:
                return Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled
            else:
                return Qt.ItemIsSelectable | Qt.ItemIsEnabled

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[col]
        if orientation == Qt.Horizontal and role == Qt.DecorationRole:
            return QPixmap("resources/table/header_{}.png".format(col))
        return None

    def setData(self, index, value, role):
        if not index.isValid() or role != Qt.CheckStateRole:
            return False
        self._checked[index.row()][index.column()] = value
        self.dataChanged.emit(index, index)
        return True
