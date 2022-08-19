import os
import requests

F2FAUTH = 'https://raw.githubusercontent.com/ObisoftDev/database/main/f2fauth.txt'

def auth(username):
    list = []
    try:
        resp = requests.get(F2FAUTH)
        text = resp.text
        list = str(text).split('\n')
    except Exception as ex:pass
    return username in list