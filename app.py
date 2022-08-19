from flask import Flask,send_file,send_from_directory,jsonify,redirect,abort,request,render_template
import json
import os
import uuid
import importer

#import Plugins
import plugins.file2free._init_ as f2f

PLUGINS_PATH = 'plugins/'

template_dir = os.path.abspath('www')
app = Flask(__name__,template_folder=template_dir)

#plugins = [item for item in os.listdir(PLUGINS_PATH)]
#for path in plugins:
#    try:
#        plug = importer.load_from_file(PLUGINS_PATH+path+'_init_.py')
#        plug.config(app)
#    except:print('Error To Import Plugin '+path)

f2f.config(app)

if __name__ == "__main__":
    app.run(host='0.0.0.0',port=443)