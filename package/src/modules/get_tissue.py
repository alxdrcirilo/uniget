import re
import urllib.request
from copy import copy

import certifi
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal


class GetTissueFilters(QThread):
    done = pyqtSignal(object)
    progress = pyqtSignal(int)

    def get_count(self, url):
        self.progress.emit(0)
        tissue_txt = urllib.request.urlopen(url, cafile=certifi.where())
        pattern = r"[\\n]\/\/[\\n]"
        count = len(re.findall(pattern, str(tissue_txt.read())))

        return count

    def run(self):
        tissue_url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/tisslist.txt"
        tissue_txt = urllib.request.urlopen(tissue_url)
        tissue_dict = {}
        default_subdict = {"ID": [], "AC": []}

        # Number of entries
        n_entries = self.get_count(url=tissue_url)

        flag = False
        counter = 0
        for line in tissue_txt:
            str_line = str(line, "utf-8")

            if "____" in str_line:
                flag = True
                continue

            if flag:
                # Cleanup all identifiers for one given entry
                if "//" in str_line:
                    for key in default_subdict.keys():
                        tissue_dict[AC][key] = "".join(tissue_dict[AC][key])
                    continue

                if str_line.startswith("ID"):
                    ID = str_line[5:-1]
                    continue

                # Create entry in tissue_dict
                if str_line.startswith("AC"):
                    AC = str_line[5:-1]
                    tissue_dict[AC] = copy(default_subdict)
                    tissue_dict[AC]["AC"] = AC

                    try:
                        # Exclude the "." at the end of string
                        tissue_dict[AC]["ID"] = ID[:-1]
                    except:
                        pass

                    counter += 1
                    tmp_counter = round(counter / n_entries * 100)
                    try:
                        global_counter
                    except NameError:
                        global_counter = tmp_counter
                    if tmp_counter != global_counter:
                        self.progress.emit(tmp_counter)
                    global_counter = tmp_counter

                    continue

                # Fill entry children in default_subdict
                if str_line.startswith(tuple(default_subdict.keys())):
                    identifier = str_line[:2]
                    tissue_dict[AC][identifier].append(str_line[5:-1])

        tissue_dict = {k: tissue_dict[k] for k in sorted(tissue_dict)}
        self.done.emit(pd.DataFrame.from_dict(tissue_dict).T)
