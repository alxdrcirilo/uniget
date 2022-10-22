import os
import pickle


def get_columns():
    dir, d = os.path.join("src", "misc", "columns"), {}
    for n, file in enumerate(sorted(os.listdir(dir))):
        fp = os.path.join(dir, file)
        tmp = {}
        with open(fp) as f:
            for line in f:
                (key, val) = line.split("\t")

                # Strip newline
                val = val.replace("\n", "")

                tmp[key] = val

            # Store info for all categories
            name = file[:-4].replace("_", " ").capitalize()
            d[name] = tmp

    path = os.path.join("data", "columns.pkl")
    with open(path, "wb") as file:
        pickle.dump(d, file)
