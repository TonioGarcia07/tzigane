#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: antoine

If you can't connect to the proxy, and you have the error :
    couldn't connect to "infinite-uptime-1232:us-central1:server2":
    googleapi: Error 401: Invalid Credentials, authError.
    ...
    mysql.connector.errors.InterfaceError: 2013: Lost connection to MySQL
    server during query

Please run:
    sudo netstat -nlp | grep 3306
        tcp  0  0  127.0.0.1:3306  0.0.0.0:*  LISTEN  31319/cloud_sql_pro

    sudo kill -9 [PID] (where PID is 31319 here)

"""
# ===================================================================
# Imports
# ===================================================================

import os
from threading import Thread
from flask import Flask, render_template

# Make sure you have run 'pip install bokeh==0.12.9'
from bokeh.embed import server_document
from bokeh.server.server import BaseServer
from bokeh.server.tornado import BokehTornado
from bokeh.server.util import bind_sockets

from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop

import anaximander as nx
from tzigane import LOGGER
import tzigane.pages as tpg
from tzigane.scores import load_accounts

import webbrowser
import warnings
warnings.filterwarnings("ignore")

path = 'prod-ac1c3416cbdd.json'
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = path
app = Flask(__name__)
PORT = 8000
LOCAL = nx.LOCAL


# ===================================================================
# Pages
# ===================================================================


@app.route('/')
def index():
    url_docs = [['/score/' + k, k, v.__doc__] for k, v in APPS.items()]
    return render_template("index.html", url_docs=url_docs, title="Tzigane")


@app.route('/score/<score_title>', methods=['GET'])
def base(score_title):
    LOGGER.info("you're on {}".format(score_title))
    url = '/' + score_title
    score = APPS[score_title](score_title)
    LOGGER.info("starting score...")
    score()
    LOGGER.info("starting server...")
    bokeh_tornado = BokehTornado({url: score.app},
                                 extra_websocket_origins=["localhost:8000"])
#                                 extra_websocket_origins=["52.53.126.244:8000"])
    # A non-blocking, single-threaded HTTP server (from Tornado)
    bokeh_http = HTTPServer(bokeh_tornado)

    # If port is 0, the OS automatically chooses a free port
    # sockets will listen to localhost
    # Opens a new process (visible with netstat) on the port
    sockets, port = bind_sockets('127.0.0.1', 0)
#    sockets, port = bind_sockets('0.0.0.0', 0)    
    bokeh_http.add_sockets(sockets)
    LOGGER.info("sockets, port: {}, {}".format(sockets, port))

    def bk_worker():
        # An Input/Output event loop for non-blocking sockets (from tornado)
        io_loop = IOLoop.instance()
        # Explicitly coordinate the level Tornado components
        # required to run a Bokeh server:
        #    - IOLoop to run the Bokeh server machinery.
        #    - Tornado application that defines the Bokeh server machinery.
        #    - HTTPServer to direct HTTP requests
        server = BaseServer(io_loop, bokeh_tornado, bokeh_http)
        server.start()
        server.io_loop.start()

    LOGGER.info("starting thread...")
    Thread(target=bk_worker).start()
    script = server_document('http://localhost:{}{}'.format(port, url))
#    script = server_document('http://52.53.126.244:{}{}'.format(port, url))
    return render_template("base.html", script=script, title=score_title)


# ===================================================================
# Main
# ===================================================================


APPS = {'batch': tpg.PressProdBatchScore,
        'streaming': tpg.PressProdStreamingScore,
        'condition': tpg.ConditionBatchScore,
        'feature_summary': tpg.FeatureSummaryBatchScore,
        'metric_summary': tpg.MetricSummaryBatchScore}


if __name__ == '__main__':
    webbrowser.open_new("http://localhost:8000")
    load_accounts()
    app.run(host='localhost', port=8000)
#    app.run(host='0.0.0.0', port=8000)
