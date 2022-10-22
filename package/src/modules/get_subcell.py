import re
import urllib.request
from copy import copy

import certifi
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal


class GetSubcellFilters(QThread):
    done = pyqtSignal(object)
    progress = pyqtSignal(int)

    def get_count(self, url):
        self.progress.emit(0)
        subcell_txt = urllib.request.urlopen(url, cafile=certifi.where())
        pattern = r"[\\n]\/\/[\\n]"
        count = len(re.findall(pattern, str(subcell_txt.read())))

        return count

    def run(self):
        subcell_url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/subcell.txt"
        subcell_txt = urllib.request.urlopen(subcell_url)
        subcell_dict = {}
        default_subdict = {
            "ID": [],
            "IT": [],
            "IO": [],
            "AC": [],
            "DE": [],
            "SY": [],
            "SL": [],
            "HI": [],
            "HP": [],
            "KW": [],
            "GO": [],
            "AN": [],
            "RX": [],
            "WW": [],
        }

        # Number of entries
        n_entries = self.get_count(url=subcell_url)

        flag = False
        counter = 0
        for line in subcell_txt:
            str_line = str(line, "utf-8")

            if "____" in str_line:
                flag = True
                continue

            if flag:
                # Cleanup all identifiers for one given entry
                if "//" in str_line:
                    for key in default_subdict.keys():
                        subcell_dict[AC][key] = "".join(subcell_dict[AC][key])
                    continue

                if str_line.startswith("ID"):
                    ID = str_line[5:-1]
                    continue

                if str_line.startswith("IT"):
                    IT = str_line[5:-1]
                    continue

                if str_line.startswith("IO"):
                    IO = str_line[5:-1]
                    continue

                # Create entry in subcell_dict
                if str_line.startswith("AC"):
                    AC = str_line[5:-1]
                    subcell_dict[AC] = copy(default_subdict)
                    subcell_dict[AC]["AC"] = AC

                    try:
                        # Exclude the "." at the end of string
                        subcell_dict[AC]["ID"] = ID[:-1]
                    except:
                        pass
                    try:
                        subcell_dict[AC]["IT"] = IT
                    except:
                        pass
                    try:
                        subcell_dict[AC]["IO"] = IO
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
                    subcell_dict[AC][identifier].append(str_line[5:-1])

        subcell_dict = {k: subcell_dict[k] for k in sorted(subcell_dict)}
        self.done.emit(pd.DataFrame.from_dict(subcell_dict).T)
