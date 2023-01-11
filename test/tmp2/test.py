import pickle

with open("download_result.fragment", "rb") as download_file:
    download_fragment = pickle.load(download_file)
print(download_fragment.keys())