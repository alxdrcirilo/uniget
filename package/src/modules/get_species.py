import re
import urllib.request

import certifi
import pandas as pd
from PyQt5.QtCore import QThread, pyqtSignal


class GetSpeciesFilters(QThread):
    done = pyqtSignal(object)
    progress = pyqtSignal(int)

    def get_count(self, url):
        self.progress.emit(0)
        spec_txt = urllib.request.urlopen(url, cafile=certifi.where())
        pattern = "Total number of identification codes currently defined: ([0-9]+?)[.]"
        count = int(re.search(pattern, str(spec_txt.read())).group(1))

        return count

    def run(self):
        spec_url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/speclist.txt"
        spec_txt = urllib.request.urlopen(spec_url)
        entries = ["Taxon Node", "Code", "Taxonomy", "Scientific name"]
        spec_dict = {}

        naming = ["N=", "C=", "S="]

        # Number of entries
        n_entries = self.get_count(url=spec_url)

        flag = False
        counter = 0
        for line in spec_txt:
            # Header
            if b"speclist.txt" in line:
                continue
            # Start
            if b"_____" in line:
                flag = True
                continue
            # End
            if b"-----" in line:
                flag = False
                continue

            if flag:
                str_line = str(line, "utf-8")

                try:
                    index = str_line.index(":")
                    tmp = str_line[:index].split(" ")
                    tmp = [_ for _ in tmp if _]
                except ValueError:
                    pass

                try:
                    key = int(tmp[2])
                    spec_dict[key]
                except KeyError:
                    spec_dict[key] = {key: [] for key in entries}

                    counter += 1
                    tmp_counter = round(counter / n_entries * 100)

                    try:
                        global_counter
                    except NameError:
                        global_counter = tmp_counter

                    if tmp_counter != global_counter:
                        self.progress.emit(tmp_counter)

                spec_dict[key]["Code"] = tmp[0]
                spec_dict[key]["Taxonomy"] = tmp[1]
                spec_dict[key]["Taxon Node"] = tmp[2]

                for name in naming:
                    try:
                        index = str_line.index(name)

                        if name == "N=":
                            spec_dict[key]["Scientific name"] = str_line[index + 2 : -1]

                        # Do not include "Common name"
                        # if name == "C=":
                        #     spec_dict[key]["Common name"] = str_line[index + 2:-1]

                        # Do not include "Synonym"
                        # if name == "S=":
                        #     spec_dict[key]["Synonym"] = str_line[index + 2:-1]
                    except ValueError:
                        continue
                for k, v in spec_dict[key].items():
                    if not v:
                        spec_dict[key][k] = "NA"

        spec_dict = {k: spec_dict[k] for k in sorted(spec_dict)}

        # Remove root
        spec_dict.pop(1)

        self.done.emit(pd.DataFrame.from_dict(spec_dict).T)
