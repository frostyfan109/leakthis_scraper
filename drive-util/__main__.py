import sys
import os
import pandas as pd
from drive import drive

printed_attrs = os.environ.get("LISTED_ATTRS") or ["title", "id"]

def get_files_as_dataframe():
    return pd.DataFrame(drive.ListFile().GetList())

def print_dataframe(df):
    print(df[printed_attrs])

if __name__ == "__main__":
    args = sys.argv[1:]
    if args[0] == "list":
        # list_attrs = args[1:]
        # If no attributes are passed in, list the file names.
        # if len(list_attrs) == 0: list_attrs.append("title")
        # files = get_files_as_dataframe()[list_attrs]
        files = get_files_as_dataframe()
        print_dataframe(files)
        # print("\n".join([", ".join([attr + ": " + file[attr] for attr in list_attrs]) for file in files]))
    elif args[0] == "get":
        if len(args) == 3:
            attr = args[1]
            value = args[2]
        else:
            # Use title as the default attribute
            attr = "title"
            value = args[1]
        files = get_files_as_dataframe()
        print_dataframe(files.loc[files[attr] == value])
    elif args[0] == "query":
        query = args[1]
        files = get_files_as_dataframe()
        print_dataframe(files.query(query))
