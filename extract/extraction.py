import customtkinter
from subprocess import call, Popen


def extract_data(address, whole_storage, app_name=None):
    wh="false"
    if (whole_storage):
        wh = "true"
    if app_name is not None:
        rc = call(["extract/extract.sh", address, wh, app_name])
    else:
        rc = call(["extract/extract.sh", address, wh])

