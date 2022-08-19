import asyncio
import os

from flask import Flask,send_file,send_from_directory,jsonify,redirect,abort,request,render_template

from . import states
from . import utils
from . import auth
from . import threads
from . import downloader as dl
from . import draft_to_calendar as d2c
from . import moodle_client
from . import ProxyCloud as pxcl

#states
States = {}
def check_access(auth,max=3):
    global States
    counter = 0
    for item in States:
        if States[item]['auth'] == auth:
            counter+=1
    if counter>=max:return False
    return True
def get_state(token):
    global States
    if token in States:
        return States[token]
    return None
#end states

def progress(dl,file,current,total,speed,time,token):
    global States
    if token:
        States[token]['state'] = 1
        States[token]['file'] = file
        States[token]['current'] = current
        States[token]['total'] = total
        States[token]['speed'] = speed
        States[token]['time'] = time
    pass


def process(*args):
    global States
    urls = args[0]
    token = args[1]
    host = args[2]
    authname = args[3]
    passw = args[4]
    repoid = args[5]
    parse = args[6]
    downloader = dl.Downloader()
    uploadlist = []
    proxy = None
    try:
        proxy = pxcl.parse(os.environ.get('env_proxy'))
        #proxy = pxcl.ProxyCloud('181.225.255.129',8080)
    except:pass
    for url in urls:
        try:
            file = downloader.download_url(url, progressfunc=progress,args=(token))
            if not downloader.stoping:
                if file:
                    filesize = utils.get_file_size(file)
                    progress(downloader,file,filesize,filesize,0,0,token)
                    States[token]['state'] = 2
                    #upload
                    mcli = moodle_client.MoodleClient(host,authname,passw,repoid,Proxy=proxy)
                    data = asyncio.run(mcli.LoginUpload(file, progress, (token)))
                    while mcli.status is None: pass
                    data = mcli.get_store(file)
                    if data:
                        if 'error' in data:
                            err = data['error']
                        else:
                            uploadlist.append({'file': file, 'url': data['url']})
                    os.unlink(file)
        except Exception as ex:
            print(str(ex))
            pass
    if len(uploadlist):
        if parse=='calendar':
            parser = d2c.Draft2Calendar()
            asyncio.run(parser.send_calendar(host, authname, passw, uploadlist,proxy=proxy))
            while parser.status == 0: pass
            if parser.data:
                uploadlist.clear()
                uploadlist = parser.data
    States[token]['uploadlist'] = uploadlist
    States[token]['state'] = 3
    pass

def config(app):

    @app.route('/file2free/create')
    def create():
        global States
        jsondata = None
        try:
            jsondata = request.json
        except:pass
        result = {'state':states.ERROR}
        if jsondata:
            authname = 'auth'
            authpassw = 'auth'
            host = ''
            repoid = '4'
            parse = ''
            urls = None
            if 'auth' in jsondata:
                authname = jsondata['auth']
            if 'clave' in jsondata:
                authpassw = jsondata['clave']
            if 'host' in jsondata:
                host = jsondata['host']
            if 'repoid' in jsondata:
                repoid = jsondata['repoid']
            if 'urls' in jsondata:
                urls =jsondata['urls']
            if 'parse' in jsondata:
                parse =jsondata['parse']
            if auth.auth(authname) and urls and check_access(authname):
                token = utils.createID(20)
                result['state'] = states.OK
                result['token'] = token
                States[token] = {}
                States[token]['auth'] = authname
                th = threads.ObigramThread(process,args=([urls,token,host,authname,authpassw,repoid,parse]))
                th.start()
            else:
                result['state'] = states.ERROR_NOT_AUTH
        else:
            result['state'] = states.ERROR_NOT_DATA
        return jsonify(result)

    @app.route('/file2free/state')
    def state():
        global States
        jsondata = None
        try:
            jsondata = request.json
        except:
            pass
        result = {'state': "NO STATE"}
        if jsondata:
            token = ''
            if 'token' in jsondata:
                token = jsondata['token']
            state = get_state(token)
            if state:
                result['state'] = 'OK'
                result['data'] = state
        return jsonify(result)

    @app.route('/file2free/parse')
    def parse():
        global States
        jsondata = None
        try:
            jsondata = request.json
        except:
            pass
        result = {'state': "ERROR PARSING"}
        if jsondata:
            type = None
            host = None
            authname = None
            authpassw = None
            urls = None
            if 'host' in jsondata:
                host = jsondata['host']
            if 'auth' in jsondata:
                authname = jsondata['auth']
            if 'clave' in jsondata:
                authpassw = jsondata['clave']
            if 'urls' in jsondata:
                urls = jsondata['urls']
            if 'type' in jsondata:
                type = jsondata['type']
            proxy = None
            try:
                proxy = pxcl.parse(os.environ.get('env_proxy'))
                # proxy = pxcl.ProxyCloud('181.225.255.129',8080)
            except:
                pass
            if host and authname and authpassw and urls:
                if type=='calendar':
                    parser = d2c.Draft2Calendar()
                    asyncio.run(parser.send_calendar(host, authname, authpassw, urls, proxy=proxy))
                    while parser.status == 0: pass
                    if parser.data:
                        result['state'] = 'OK'
                        result['data'] = parser.data
        return jsonify(result)
