import asyncio
import json
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
from . import zipfile

#states
STATEFILE = 'states.st'
def check_access(auth,max=3):
    states = {}
    try:
        if os.path.isfile(STATEFILE):
            sf = open(STATEFILE, 'r')
            jsonread = str(sf.read()).replace("'", '"')
            states = json.loads(jsonread)
            sf.close()
    except Exception as ex:
        print(str(ex))
        pass
    counter = 0
    for item in states:
        if states[item]['auth'] == auth:
            counter+=1
    if counter>=max:return False
    return True
def delete_state(token):
    states = {}
    try:
        if os.path.isfile(STATEFILE):
            sf = open(STATEFILE, 'r')
            jsonread = str(sf.read()).replace("'", '"')
            states = json.loads(jsonread)
            sf.close()
    except Exception as ex:
        print(str(ex))
        pass
    try:
        states.pop(token)
    except:pass
    sf = open(STATEFILE, 'w')
    sf.write(str(states))
    sf.close()

def get_state(token):
    states = {}
    try:
        if os.path.isfile(STATEFILE):
            sf = open(STATEFILE, 'r')
            jsonread = str(sf.read()).replace("'", '"')
            states = json.loads(jsonread)
            sf.close()
    except Exception as ex:
        print(str(ex))
        return {}
        pass
    if token in states:
        return states[token]
    return None
def write_state(token,key,data):
    states = {}
    try:
        if os.path.isfile(STATEFILE):
            sf = open(STATEFILE,'r')
            jsonread = str(sf.read()).replace("'",'"')
            states = json.loads(jsonread)
            sf.close()
    except Exception as ex:
        print(str(ex))
        pass
    try:
        states[token][key] = data
    except:
        states[token] = {}
        states[token][key] = data
    sf = open(STATEFILE,'w')
    sf.write(str(states))
    sf.close()
#end states

def progress_down(dl,file,current,total,speed,time,token):
    if token:
        write_state(token, 'state', 1)
        write_state(token, 'file', file)
        write_state(token, 'current', current)
        write_state(token, 'total', total)
        write_state(token, 'speed', speed)
        write_state(token, 'time', time)
    pass
def progress_upt(dl,file,current,total,speed,time,token):
    if token:
        write_state(token, 'state', 2)
        write_state(token, 'file', file)
        write_state(token, 'current', current)
        write_state(token, 'total', total)
        write_state(token, 'speed', speed)
        write_state(token, 'time', time)
    pass

def process(*args):
    urls = args[0]
    token = args[1]
    host = args[2]
    authname = args[3]
    passw = args[4]
    repoid = args[5]
    parse = args[6]
    zips = args[7]
    downloader = dl.Downloader()
    uploadlist = []
    proxy = None
    try:
        proxy = pxcl.parse(os.environ.get('env_proxy'))
        #proxy = pxcl.ProxyCloud('181.225.255.129',8080)
    except:pass
    for url in urls:
        try:
            file = downloader.download_url(url, progressfunc=progress_down,args=(token))
            if not downloader.stoping:
                if file:
                    filesize = utils.get_file_size(file)
                    progress_upt(downloader,file,0,filesize,0,0,token)
                    write_state(token, 'state', 2)
                    #upload
                    if 'nube' in host or 'icloud' in host:
                        pass
                    else:
                        mcli = moodle_client.MoodleClient(host,authname,passw,repoid,Proxy=proxy)
                        files = []
                        if filesize>=zips*1024*1024:
                            mult_file = zipfile.MultiFile(file,1024*1024*zips)
                            zip = zipfile.ZipFile(mult_file,  mode='w', compression=zipfile.ZIP_DEFLATED)
                            zip.write(file)
                            zip.close()
                            mult_file.close()
                            files = mult_file.files
                        else:
                            files.append(file)
                        for f in files:
                            data = asyncio.run(mcli.LoginUpload(f, progress_upt, (token)))
                            while mcli.status is None: pass
                            data = mcli.get_store(f)
                            if data:
                                if 'error' in data:
                                    err = data['error']
                                else:
                                    uploadlist.append({'file': f, 'url': data['url']})
                            os.unlink(f)
        except Exception as ex:
            print(str(ex))
            pass
    write_state(token, 'uploadlist', uploadlist)
    write_state(token, 'state', 3)
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
            zips = 100
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
            if 'zips' in jsondata:
                zips =jsondata['zips']
            if auth.auth(authname) and urls and check_access(authname):
                token = utils.createID(20)
                result['state'] = states.OK
                result['token'] = token
                write_state(token,'auth',authname)
                th = threads.ObigramThread(process,args=([urls,token,host,authname,authpassw,repoid,parse,zips]))
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
                try:
                    if state['state'] ==3:
                        delete_state(token)
                except:pass
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
                else:
                    result['state'] = 'No Existe El Parse En La Api'
        return jsonify(result)
