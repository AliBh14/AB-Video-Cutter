import time
from win32api import GetSystemMetrics

def get_disp_size():
    return GetSystemMetrics(0), GetSystemMetrics(1) #W & H respectively

def format_seconds(seconds):
    return time.strftime('%H:%M:%S', time.gmtime(seconds)) + ':' + str(round(divmod(seconds, 1.00)[1]*100))


