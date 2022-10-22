from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import *


class About(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setWindowIcon(QIcon(":resources/icons/main.png"))

        title = QLabel("UniGet")
        title.setStyleSheet("color: black;" "font-size: 20px")
        title.setAlignment(Qt.AlignCenter)

        icon = QLabel()
        icon.setPixmap(
            QPixmap(":resources/icons/main.png").scaledToHeight(
                100, Qt.SmoothTransformation
            )
        )

        info = QLabel()
        text = """
        UniGet is a tool written in Python used to search, filter, and fetch records from the <a 
        href='https://www.uniprot.org'>UniProt</a> database.
        """
        info.setAlignment(Qt.AlignCenter)
        info.setText(text)
        info.setOpenExternalLinks(True)
        info.setWordWrap(True)

        hline = QFrame()
        hline.setFrameShape(QFrame.HLine)
        hline.setFrameShadow(QFrame.Sunken)

        groupbox = QGroupBox()
        vlayout = QVBoxLayout()
        vlayout.addStretch()
        vlayout.addWidget(title)
        vlayout.addWidget(hline)
        vlayout.addWidget(info)
        vlayout.addStretch()
        groupbox.setLayout(vlayout)

        layout = QHBoxLayout()
        layout.addWidget(icon)
        layout.addWidget(groupbox)

        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())
