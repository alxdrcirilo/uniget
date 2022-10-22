import urllib.request

import certifi
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal


class GetDBFilters(QThread):
    done = pyqtSignal(object)
    progress = pyqtSignal(int)

    def get_count(self, url):
        self.progress.emit(0)
        db_txt = urllib.request.urlopen(url, cafile=certifi.where())
        pattern = "Abbrev:"
        count = str(db_txt.read()).count(pattern)

        return count

    def run(self):
        db_url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/dbxref.txt"
        db_txt = urllib.request.urlopen(db_url)
        entries = ["AC", "Abbrev", "Name", "Server", "Db_URL", "Cat"]
        db_dict = {key: [] for key in entries}

        # Number of entries
        n_entries = self.get_count(url=db_url)

        counter = 0
        for line in db_txt:
            if b"dbxref.txt" in line:
                continue
            for id in entries:
                if line.startswith(id.encode()):
                    str_line = str(line, "utf-8")
                    index = str_line.index(":")
                    db_dict[id].append(str_line[index + 2 : -1])

                    counter += 1
                    tmp_counter = round(counter / n_entries * 100)

                    try:
                        global_counter
                    except NameError:
                        global_counter = tmp_counter

                    if tmp_counter != global_counter:
                        self.progress.emit(tmp_counter)

                    global_counter = tmp_counter

        self.done.emit(pd.DataFrame.from_dict(db_dict))
