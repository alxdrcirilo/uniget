import re
import urllib.request
from collections import OrderedDict, defaultdict

import certifi
from PyQt5.QtCore import QThread, pyqtSignal


class GetPathwaysFilters(QThread):
    done = pyqtSignal(object)
    progress = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.collection = OrderedDict()
        self.master = defaultdict(OrderedDict)

    def get_count(self, url):
        self.progress.emit(0)
        pathway_txt = urllib.request.urlopen(url, cafile=certifi.where())
        pattern = r"//"
        count = len(re.findall(pattern, str(pathway_txt.read())))
        # Ignore "//" from header
        count -= 4

        return count

    def initialize(self, d: defaultdict = None):
        if d is None:
            d = defaultdict(list)
        for k in self.master.keys():
            if not self.master[k].get("HI") and not self.master[k].get("HP"):
                d[k] = list()

        return d

    def populate(self, d: dict) -> dict:
        for r in d.keys():
            for k, v in self.master.items():
                if v.get("HI") and r in v.get("HI"):
                    subd = {k: list()}
                    d[r].append(subd)
                    self.populate(d=subd)
                if v.get("HP"):
                    subk = v.get("HP")
                    subidx = subk.find("; ") + 2
                    subk = subk[subidx:].strip(".")
                    if subk == r:
                        d[subk].append(k)

        return d

    def run(self):
        pathway_url = "https://ftp.uniprot.org/pub/databases/uniprot/current_release/knowledgebase/complete/docs/pathlist.txt"
        pathway_txt = urllib.request.urlopen(pathway_url)

        # Number of entries
        n_entries = self.get_count(url=pathway_url)

        flag = False
        counter = 0
        keys = ("ID", "AC", "CL", "DE", "SY", "HI", "HP", "DR")
        for line in pathway_txt:
            str_line = str(line, "utf-8")

            # Ignore header
            header_delim = "_" * 75 + "\n"
            if str_line == header_delim:
                flag = True

            # Pathway
            if flag:
                if str_line.startswith(keys):
                    # Get key (e.g. "ID")
                    key = str_line[:2]
                    # Exclude start (e.g. "ID   ") and strip newline ("\n")
                    val = str_line[5:].strip("\n")

                    if key == "ID":
                        counter += 1
                        tmp_counter = round(counter / n_entries * 100)
                        self.progress.emit(tmp_counter)
                        # Strip final char (".")
                        last_id = val.strip(".")
                        self.master[last_id] = OrderedDict()
                    else:
                        if key != last_key:
                            self.master[last_id][key] = val
                        else:
                            self.master[last_id][last_key] += " " + val

                    last_key = key

        roots = self.initialize()
        self.collection = self.populate(d=roots)
        self.collection = OrderedDict(sorted(self.collection.items()))

        self.done.emit({"master": self.master, "collection": self.collection})
