from io import BytesIO

import pandas as pd
import requests
from PyQt5.QtCore import QThread, pyqtSignal


class GetData(QThread):
    done = pyqtSignal(tuple)
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, query, parent=None, columns: str = None):
        QThread.__init__(self, parent)
        self.query = query
        self.columns = columns

    def run(self):
        url = (
            "https://rest.uniprot.org/uniprotkb/search?compressed=false&download=false"
        )
        url += "&fields=accession%2Creviewed%2Cid%2Cprotein_name%2Cgene_names%2Corganism_name%2Clength%2Cmass"
        if self.columns:
            url += f"%2C{self.columns}"
        url += "&format=tsv"
        url += f"&query={self.query}"

        # TODO
        print(url)

        try:
            # Total number of hits
            n = int(requests.get(url=url).headers.get("X-Total-Results"))

            with requests.get(url=url.replace("search", "stream"), stream=True) as r:
                # Create buffer
                file = BytesIO()

                # Track progress (number of lines)
                last_n = 0
                for i, line in enumerate(r.iter_lines()):
                    file.write(line)
                    # Add new line
                    file.write("\n".encode())
                    # Emit progress
                    current_n = int(i / n * 100)
                    if current_n > last_n:
                        last_n = current_n
                        self.progress.emit(current_n)

                file.seek(0)
                query_df = pd.read_csv(file, sep="\t", header=0)
                file.close()

            # Capitalize "Reviewed" column
            query_df["Reviewed"] = query_df["Reviewed"].str.capitalize()

            self.done.emit((query_df, query_df.shape[0]))

        except TypeError:
            self.error.emit("No records found!")
