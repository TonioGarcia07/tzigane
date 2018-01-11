# TZIGANE

A Bokeh based application to visualize and edit timeseries.
It aims at creating higher-level and easy-to-use objects, specificially for Infinite Uptime needs. It packs a number of predefined data visualizations templates, along with edition toolbars. 

## Objectives
- Annotate Time Series for supervised learning
- Subject algorithm results to visual inspections
- Explore large swaths of data quickly and efficiently
- Manual edits to improve customer satisfaction pending full automation
- Generally create interactive data visualization toolbox to support learning, communication and marketing

## Content of the repository
- static : static objects for the browser visualization
- templates: templates for the visualization
- .heroku-financial-app: working Bokeh deployment on Heroku (based on https://github.com/blakeboswell/heroku-financial-app)
- .tzigane-heroku : folder for the deployment of Tzigane on Heroku:
    - lib : includes dataforge / tigane / dataforge. Dataforge needs a special treatment for 3 modules:
        - baseschemas / reporting / summary (see the README.md of the forlder)
    - cloudsql :  has to be there even if it's empty because we need it for the unix sockets and we can't mkdir on Heroku.
    - prod-ac1c3416cbdd.json : credentials of the service account used to connect to GAE.
    - app.py : similar to main.py from tzigane (except for the imports / pre-treatment).
    - Procfile : Heroku configuration.
- tzigane


## How to run Tzigane
 [$ git clone <link to git repo>]
 [$ cd tzigane]
- install all the dependencies (or make sureyou have bokeh version 0.12.9 with [$ pip install bokeh==0.12.9]):
 [$ pip install -r requirements.txt]
- run the application (will automatically load the environment and devices and open a new window)
 [$ python main.py]


## HEROKU Deployment
To deploy with heroku:
- [$ heroku create <name>]
- commit your changes
- [git push heroku master]

Visible on browser (https://<name>.herokuapp.com/) with:
- [heroku open]

To check the logs when there is an issue:
- [heroku logs (--tail)]