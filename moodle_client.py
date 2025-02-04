from random import random
from typing import Callable
import aiohttp
from aiohttp_socks import ProxyConnector
from python_socks import ProxyType
from yarl import URL
from bs4 import BeautifulSoup
import asyncio

import re
import json
from plugins.file2free import ProxyCloud as proxyCloud

from io import BufferedReader, FileIO
from pathlib import Path
import time

STATUS_LOGED = 1
STATUS_NOTLOGED = 0
STATUS_FINISHUPLOAD = 2
STATUS_FINISHDELETE = 3

def is_support(host):
    return 'moodle.ismm' in host \
           or 'moodle.cujae' in host \
           or 'moodle.eem.minem' in host

class MProgressFile(BufferedReader):
    def __init__(self, filename, read_callback=None,args=None):
        f = FileIO(file=filename, mode="r")
        self.__read_callback = read_callback
        self.__args = args
        self.__filename = filename
        super().__init__(raw=f)
        self.length = Path(filename).stat().st_size
        self.current = 0
        self.time_start = time.time()
        self.time_total = 0
        self.size_per_second = 0
        self.clock_start = time.time()
        self.chunk_por = 0

    def read(self, size=None):
        global download_status
        calc_sz = size
        self.chunk_por += size
        if not calc_sz:
            calc_sz = self.length - self.tell()
        if self.__read_callback:
            self.size_per_second += size
            tcurrent = time.time() - self.time_start
            self.time_total += tcurrent
            self.time_start = time.time()
            if self.time_total >= 1:
                clock_time = (self.length - self.chunk_por) / (self.size_per_second)
                self.__read_callback(self,self.__filename, self.tell(), self.length,self.size_per_second,clock_time,self.__args)
                self.time_total = 0
                self.size_per_second = 0
        return super(MProgressFile, self).read(size)


class MoodleClient:

    ##############################################################################
    def __init__(self, ServerUrl: str, UserName: str, Password: str, RepoID: str,Proxy:proxyCloud.ProxyCloud=None) -> None:
        # Atributos públicos
        self.ServerUrl: str = ServerUrl
        self.UserName: str = UserName
        self.Password: str = Password
        self.RepoID: str = RepoID
        self.MaxTasks: int = 3
        self.TasksInProgress: int = 0
        self.store = {}
        self.status = None
        self.proxy = Proxy

        # Atributos privados
        self.__Session = None
        self.__Headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36"
        }
        self.__LoginLOCK: bool = False
        #SAVE VARIABLES
        self.sesskey = None
        self.query = None
        self.client_id = None
        self.loged = False
        self.cookie = None

    def get_store(self,name):
        if name in self.store:
            return self.store[name]
        return None

    async def __construct(self):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            if self.proxy:
                connector = ProxyConnector(
                     proxy_type=ProxyType.SOCKS5,
                     host=self.proxy.ip,
                     port=self.proxy.port,
                     rdns=True,
                     ssl=False
                )
        except:
            connector = aiohttp.TCPConnector(ssl=False)
            if self.proxy:
                connector = ProxyConnector(
                    proxy_type=ProxyType.SOCKS5,
                    host=self.proxy.ip,
                    port=self.proxy.port,
                    rdns=True,
                    ssl=False
                )
        self.__Session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True),connector=connector)

    async def __construct_cookie(self):
        try:
            connector = aiohttp.TCPConnector(ssl=False)
            if self.proxy:
                connector = ProxyConnector(
                     proxy_type=ProxyType.SOCKS5,
                     host=self.proxy.ip,
                     port=self.proxy.port,
                     rdns=True,
                     ssl=False
                )
        except:
            connector = aiohttp.TCPConnector(ssl=False)
            if self.proxy:
                connector = ProxyConnector(
                    proxy_type=ProxyType.SOCKS5,
                    host=self.proxy.ip,
                    port=self.proxy.port,
                    rdns=True,
                    ssl=False
                )
        self.__Session = aiohttp.ClientSession(cookie_jar=self.cookie,connector=connector)

    async def LogOut(self) -> None:
        await self.__Session.close()

    ##############################################################################
    async def LoginUpload(self,path: str, progress_callback: Callable = None,args=None,close=False) -> bool:
            if self.loged == False:
                await self.__construct()
            # Intentar iniciar sesión
                try:

                    # Extraer el token de inicio de sesión
                    timeout = aiohttp.ClientTimeout(total=20)
                    async with self.__Session.get(
                        url=self.ServerUrl + "/login/index.php",
                        headers=self.__Headers,
                        timeout=timeout,
                    ) as response:
                        html = await response.text()

                    # Preparar payload de inicio de sesión
                    try:
                        # Caso para veriones modernas de Moodle
                        soup = BeautifulSoup(html, "html.parser")
                        token = soup.find("input", attrs={"name": "logintoken"})["value"]
                        anchor = None
                        rememberusername = None
                        try:
                            anchor = soup.find("input", attrs={"name": "anchor"})["value"]
                        except:pass
                        try:
                            rememberusername = soup.find("input", attrs={"name": "rememberusername"})["value"]
                        except:pass
                        payload = {
                            "logintoken": token,
                            "username": self.UserName,
                            "password": self.Password
                        }
                        if anchor != None:
                            payload['anchor'] = anchor
                        if rememberusername:
                            payload['rememberusername'] = rememberusername
                    except:
                        # Caso para la versión obsoleta de Aulavirtual de SLD
                        soup = BeautifulSoup(html, "html.parser")
                        anchor = None
                        rememberusername = None
                        try:
                            anchor = soup.find("input", attrs={"name": "anchor"})["value"]
                        except:
                            pass
                        try:
                            rememberusername = soup.find("input", attrs={"name": "rememberusername"})["value"]
                        except:pass
                        payload = {
                            "username": self.UserName,
                            "password": self.Password
                        }
                        if anchor != None:
                            payload['anchor'] = anchor
                        if rememberusername:
                            payload['rememberusername'] = rememberusername

                    # Iniciar sesión
                    async with self.__Session.post(
                        url=self.ServerUrl + "/login/index.php",
                        headers=self.__Headers,
                        data=payload,
                        timeout=timeout,
                    ) as response:
                        await response.text()

                    # Comprobar si no redireccionó desde /login/index.php
                    if str(response.url).lower() == (self.ServerUrl + "/login/index.php").lower():
                        # Error, datos incorrectos
                        ret = False
                        self.status = STATUS_NOTLOGED
                    else:
                        # Sesión iniciada
                        self.loged = True
                        self.cookie = self.__Session.cookie_jar
                        # print(self.__Session.cookie_jar.filter_cookies(URL(self.ServerUrl)))

                except Exception as ex:
                    self.store[path] = {'error':str(ex)}
                    # Error desconocido (mayormente conexión)
                    ret = False
                    self.status = STATUS_NOTLOGED

                self.__LoginLOCK = False
            else:
                await self.__construct_cookie()
            if self.loged:
                data = await self.UploadDraft(path,progress_callback,args)
                self.status = STATUS_LOGED
            try:
                await self.LogOut()
            except:pass
            return self.loged

    ##############################################################################
    async def UploadDraft(self, path: str, progress_callback: Callable = None,args=None) -> dict:
        await asyncio.sleep(random())  # Para evitar colisiones en las tareas
        # Evita superar el máximo de tareas permitidas
        while self.TasksInProgress >= self.MaxTasks:
            await asyncio.sleep(random() * 4 + 1)

        self.TasksInProgress += 1

        try:
            # Obtener parámetros
            if self.sesskey and self.query and self.client_id:
                pass
            else:
                timeout = aiohttp.ClientTimeout(total=20)
                async with self.__Session.get(
                        url=self.ServerUrl + "/user/edit.php",  # Porque algunos bloquean el files.php
                        headers=self.__Headers,
                        timeout=timeout,
                ) as response:
                    resp_1 = await response.text()

                soup = BeautifulSoup(resp_1, "html.parser")
                self.sesskey = soup.find("input", attrs={"name": "sesskey"})["value"]
                self.query = URL(soup.find("object", attrs={"type": "text/html"})["data"]).query

                client_id_pattern = '"client_id":"\w{13}"'
                client_id = re.findall(client_id_pattern, resp_1)
                self.client_id = re.findall("\w{13}", client_id[0])[0]
            if self.sesskey and self.query and self.client_id:
                sesskey = self.sesskey
                query = self.query
                client_id = self.client_id
            itemid = query["itemid"]
            file = MProgressFile(filename=path, read_callback=progress_callback,args=args)
            # Crear payloads POST
            data = aiohttp.FormData()
            data.add_field("title", "")
            data.add_field("author", self.UserName)
            data.add_field("license", "allrightsreserved")
            data.add_field("itemid", itemid)
            data.add_field("repo_id", str(self.RepoID))
            data.add_field("p", "")
            data.add_field("page", "")
            data.add_field("env", "filemanager")
            data.add_field("sesskey", sesskey)
            data.add_field("client_id", client_id)
            ##################################################################################################
            data.add_field("maxbytes", query["maxbytes"])
            # data.add_field("areamaxbytes", query["areamaxbytes"])
            # Lo anterior es lo correcto, lo siguiente es un hack para sobrepasar el tamaño de archivo definido
            data.add_field("areamaxbytes", str(1024 * 1024 * 1024 * 4))
            #################################################################################################
            data.add_field("ctx_id", query["ctx_id"])
            data.add_field("savepath", "/")
            data.add_field("repo_upload_file", file)

            timeout = aiohttp.ClientTimeout(connect=30, total=60 * 60)  # 1H de timeout
            async with self.__Session.post(
                url=self.ServerUrl + "/repository/repository_ajax.php?action=upload",
                data=data,
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                resp = await response.text()
                print(resp)
                # resp = await response.json(content_type=None)
                resp = json.loads(resp)
        except Exception as ex:
            resp = {"error": str(ex) }

        try:
            file.close()
        except:pass
        self.TasksInProgress -= 1
        self.status = STATUS_FINISHUPLOAD
        self.store[path] = resp
        return resp

    # Dudoso: Experimentos hasta ahora demuestran que no elimina el archivo
    # directamente, solo borra el link, lo que podria acelerar o no la eliminación
    # por parte del servidor
    ##############################################################################
    async def DeleteDraft(self, url: str):

        try:
            # Obtener parámetros
            timeout = aiohttp.ClientTimeout(total=20)
            async with self.__Session.get(
                url=self.ServerUrl + "/user/edit.php",  # Porque algunos bloquean el files.php
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                resp_1 = await response.text()

            soup = BeautifulSoup(resp_1, "html.parser")
            sesskey = soup.find("input", attrs={"name": "sesskey"})["value"]

            client_id_pattern = '"client_id":"\w{13}"'
            client_id = re.findall(client_id_pattern, resp_1)
            client_id = re.findall("\w{13}", client_id[0])[0]

            file = URL(url).path.split("/")

            payload = {
                "sesskey": sesskey,
                "client_id": client_id,
                "filepath": "/",
                "itemid": file[-2],
                "filename": file[-1],
            }

            async with self.__Session.post(
                url=self.ServerUrl + "/repository/draftfiles_ajax.php?action=delete",
                data=payload,
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                self.status = STATUS_FINISHDELETE
                return json.loads(await response.text())
        except:
            self.status = STATUS_FINISHDELETE
            return {"error": "Error. Error desconocido."}


file = 'requirements.txt'
mcli = MoodleClient('https://moodle.uclv.edu.cu/','Cjmartinez','helencita25*','4')
data = asyncio.run(mcli.LoginUpload(file))
while mcli.status is None: pass
data = mcli.get_store(file)
print(data)
file = 'states.st'
data = asyncio.run(mcli.LoginUpload(file))
while mcli.status is None: pass
data = mcli.get_store(file)
print(data)