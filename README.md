# TZIGANE

A Bokeh based application to visualize and edit timeseries.
It aims at creating higher-level and easy-to-use objects. It packs a number of predefined data visualizations templates, along with edition toolbars. 

## Objectives
- Annotate Time Series for supervised learning
- Subject algorithm results to visual inspections
- Explore large swaths of data quickly and efficiently
- Manual edits to improve customer satisfaction pending full automation
- Generally create interactive data visualization toolbox to support learning, communication and marketing

## Content of the repository
- static : static objects for the browser visualization
- templates: templates for the visualization
- tzigane: objects' definitions.

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
