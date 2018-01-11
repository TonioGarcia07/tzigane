#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The basic classes are defined in this file.
"""
# ===================================================================
# Imports
# ===================================================================

import abc
import time
import pandas as pd
from bokeh.io import curdoc
from threading import Thread
from tzigane.util import _qrange
from functools import partial
from dataforge import PROJECT_ID
import dataforge.environment as env
from bokeh.models.widgets import TextInput, Select, Button, Div
from bokeh.models import ColumnDataSource
from bokeh.layouts import layout, row, widgetbox

import tzigane.staves as stv
from tzigane.util import sequence
from tzigane.gadgets import Base
from tzigane import LOGGER

ACCEL = 'accel_energy_512'

ACCOUNTS = None
ACCOUNTS_LOADED = False

FEATURE_SUMMARIES = ['summary_10s', 'summary_1m', 'summary_5m', 'summary_30m',
                     'summary_6H', 'summary_1D', 'summary_7D']

METRIC_SUMMARIES = ['MetricSummary5m', 'MetricSummary30m', 'MetricSummaryS1',
                    'MetricSummaryS2', 'MetricSummaryS3', 'MetricSummary1D',
                    'MetricSummary1M']

# ===================================================================
# Helper function
# ===================================================================


def remove_tool(name, tools):
    tools.children = list(filter(lambda x: x.name != name, tools.children))


def load_accounts():
    def _load():
        global ACCOUNTS, ACCOUNTS_LOADED
        LOGGER.info("Loading accounts...")
        start = time.time()
        ACCOUNTS = env.Account.requery_all()
        ACCOUNTS_LOADED = True
        LOGGER.info("Accounts loaded in {:.2f}s".format(time.time() - start))

    Thread(target=_load).start()


def get_feature_range_from(start, end):
    duration = end - start
    if duration < pd.Timedelta(2, 'h'):
        return 'summary_10s'
    elif duration < pd.Timedelta(6, 'h'):
        return 'summary_1m'
    elif duration < pd.Timedelta(1, 'd'):
        return 'summary_5m'
    elif duration < pd.Timedelta(7, 'd'):
        return 'summary_30m'


def get_metric_range_from(start, end):
    duration = end - start
    if duration < pd.Timedelta(1, 'd'):
        return 'MetricSummary5m'
    elif duration < pd.Timedelta(7, 'h'):
        return 'MetricSummary30m'
    elif duration < pd.Timedelta(30, 'd'):
        return 'MetricSummary1D'


# ===================================================================
# Class definitions
# ===================================================================


class Score(Base):
    """Class to gather all the elements in a document."""
    def __init__(self, title, *args, **kwargs):
        super().__init__()
        self.doc = self.app.create_document()
        self.title = title
        self.doc.title = self.title
        self.project = PROJECT_ID
        self.staves = {}

        # Global layout
        self.logo = Div(text="""
                        <img src="../static/logo1.png" width="200">
                        """)
        self.toolbar = layout()
        html = """<br><br><br><br><br><br><br><br><br><br><br><br>
        <div style="text-align:center;vertical-align: middle;">
        <img id="spinner" src="../static/iuspinner.gif" width="200">
        <br>Loading...</div>
        """
        self.spinner = Div(text=html)
        self.panel = layout()
        self.plots = layout()
        self.plots.children = [self.spinner]
        self.layout = layout([[self.toolbar], [self.panel, self.plots]])

        # Time concerns
        self._start = TextInput(title="Start:")
        self._end = TextInput(title="End:")
        self._refresh = Button(label="Refresh")
        self._submit = Button(label="Submit")
        self._initialized = False

    def __call__(self):
        self._init_environment()
        self._init_toolbar()
        self.refresh_range()

        self._refresh.on_click(self.refresh_range)
        self._submit.on_click(partial(self.refresh_range, 'submit'))
        self._initialized = True

    def _init_environment(self):
        """This has to be modified to consider devices other than presses."""
        global ACCOUNTS, ACCOUNTS_LOADED
        start = time.time()
        while not ACCOUNTS_LOADED:
            msg = "Waiting for the accounts to be loaded... {:.2f}s."
            LOGGER.info(msg.format(time.time() - start))
            time.sleep(5)
        self.accounts = ACCOUNTS
        if hasattr(self, 'function'):
            self.macs = [d.mac for acc in self.accounts for d in acc.devices()
                         if d.function == self.function]
        else:
            self.macs = [d.mac for acc in self.accounts for d in acc.devices()]
        # Needed for condition. Accounts are empty
        self.devices = [env.Device[mac] for mac in self.macs]
        df = {'mac': self.macs,
              'device': [str(d) for d in self.devices],
              'account': [d.account.name for d in self.devices]}
        self.df = pd.DataFrame(df, index=self.macs)

    def _init_toolbar(self):
        self._project = TextInput(title="Project:", value=self.project)
        if hasattr(self, 'mac'):
            mac = self.mac
        else:
            mac = self.df.mac.sample(1)[0]
        dev = self.df[self.df.mac == mac].device.iloc[0]
        acc = self.df[self.df.mac == mac].account.iloc[0]
        self._account = Select(title="Account:", value=acc,
                               options=list(set(self.df.account)))
        self._device = Select(title="Device:", value=dev,
                              options=list(set(self.df[self.df.account ==
                                                       acc].device)))
        self._mac = TextInput(title="Mac:", value=mac)
        self._account.on_change('value', self.update_account)
        self._device.on_change('value', self.update_device)
        self._mac.on_change('value', self.update_mac)
        self.toolbar.children.append(row(self.logo,
                                         self._project,
                                         self._mac,
                                         self._account,
                                         self._device))

    def refresh_range(self, *args, **kwargs):
        if 'submit' in args:
            self.start, self.end = _qrange(self._start.value, self._end.value)
        else:
            self.start, self.end = _qrange()
        self.s_start, self.s_end = _qrange(self.start, self.end, res="string")
        self._start.value, self._end.value = self.s_start, self.s_end
        self.refresh_plot()

    def refresh_plot(self):
        self.update_staves({'time_range': (self.start, self.end)})

    def update_account(self, attr, old, new, device=None):
        """Mandatory for toolbar."""
        if device is not None:
            self._device.value = device
        else:
            self._device.options = list(self.df.loc[self.df.account == new,
                                                    'device'])
            self._device.value = self._device.options[0]

    def update_mac(self, attr, old, new):
        """Mandatory for toolbar."""
        if new in self.df.mac:
            acc, dev = self.df.loc[new, ['account', 'device']]
            self._account.value = acc
            self.update_account('value', acc, acc, device=dev)
        else:
            self._mac.value = old

    def update_device(self, attr, old, new):
        """Mandatory for toolbar."""
        self._mac.value = self.df.loc[self.df.device == new, 'mac'].iloc[0]
        self.update_staves({'mac': self._mac.value})

    def update_staves(self, val={}):
        if 'mac' in val.keys():
            self._plot()
        if 'time_range' in val.keys():
            for name, stave in self.staves.items():
                stave.update_time_range(*val['time_range'])
            for name, stave in self.staves.items():
                stave._update_fig()
                stave._update_gadgets()

    @abc.abstractproperty
    def _plot(self):
        return NotImplemented


class BatchScore(Score):
    """Class to study in batch mode."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)

    def __call__(self):
        super().__call__()
        self.panel.children.append(widgetbox([self._start,
                                              self._end,
                                              self._refresh,
                                              self._submit]))


class StreamingScore(Score):
    """Class to study in streaming mode."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)

    def __call__(self):
        super().__call__()
        """Tab with text input [range] and button [play/pause stream]"""
        self._freq = TextInput(title="Update frequency:", value="2s")

        def streaming_update():
            td_freq = pd.Timedelta(self._freq.value)
            self.start, self.end = _qrange(self.start + td_freq,
                                           self.end + td_freq)
            self.s_start, self.s_end = _qrange(self.start, self.end,
                                               res="string")
            self._start.value, self._end.value = self.s_start, self.s_end
            self.update_staves({'time_range': (self.start, self.end)})

        def stream():
            if self._stream.label == "► Play":
                self._stream.label = "❚❚ Pause"
                frq = 1000 * pd.Timedelta(self._freq.value).seconds
                curdoc().add_periodic_callback(streaming_update, frq)
            else:
                self._stream.label = "► Play"
                curdoc().remove_periodic_callback(streaming_update)

        self._stream = Button(label="► Play")
        self._stream.on_click(stream)
        self.panel.children.append(widgetbox([self._start,
                                              self._end,
                                              self._submit,
                                              self._freq,
                                              self._stream,
                                              self._refresh]))


class PressProdScore(Score):
    """Class to study the Production of presses."""
    def __init__(self, title, *args, **kwargs):
        self.function = 'pressprod'
        self.mac = '88:4A:EA:69:E1:59'
        super().__init__(title, *args, **kwargs)

    def __call__(self):
        super().__call__()
        self._plot()

    def _plot(self):
        _kw = {'mac': self._mac.value, 'start': self.start, 'end': self.end}
        self.staves[ACCEL] = stv.PressProdStave(ACCEL, **_kw)
        self.staves['pressprod'] = stv.CycleStave('pressprod', **_kw)
        self.staves['pressprod'].fig.x_range = self.staves[ACCEL].fig.x_range
        self.plots.children = [stave.plot for stave in self.staves.values()]


class ConditionScore(Score):
    """Class to study the Condition and the related thresholds."""
    def __init__(self, title, *args, **kwargs):
        self.function = 'vibrations'
        self.mac = '88:4A:EA:69:36:F5'
        super().__init__(title, *args, **kwargs)

    def __call__(self):
        super().__call__()
        self.features = [ACCEL, 'velocity_x', 'velocity_y', 'velocity_z']
        th = env.Device[self._mac.value].specs['thresholds']
        self.thresholds = {k: [v.high, v.med, v.low] for k, v in th.items()
                           if k in self.features}
        self.thresholds['index'] = ['high', 'med', 'low']
        self.thresh_source = ColumnDataSource(self.thresholds)
        self._plot()

    def _plot(self):
        self.plots.children = [self.spinner]
        th = env.Device[self._mac.value].specs['thresholds']
        self.thresholds.update({k: [v.high, v.med, v.low]
                                for k, v in th.items() if k in self.features})
        self.thresh_source.data.update(self.thresholds)
        _kw = {'mac': self._mac.value, 'start': self.start, 'end': self.end}
        for ft in self.features:
            self.staves[ft] = stv.ConditionStave(ft, self.thresh_source, **_kw)
            self.staves[ft].fig.x_range = self.staves[ACCEL].fig.x_range
        self.staves['condition'] = stv.AssessmentStave(self, 'condition',
                                                       **_kw)
        self.staves['condition'].fig.x_range = self.staves[ACCEL].fig.x_range
        # We want the assessment to appear on top
        self.plots.children = [self.staves[el].plot
                               for el in ['condition'] + self.features]


class SummaryScore(Score):
    """Class to study the features summary over a long period of time."""
    def __init__(self, title, *args, **kwargs):
        self.mac = '88:4A:EA:69:E1:59'
        super().__init__(title, *args, **kwargs)
        self.summary_range = Select(value=self.summaries[0],
                                    options=self.summaries)
        self.summary_range.on_change('value', self._update_summary_range)

    def __call__(self):
        super().__call__()
        self.panel.children[0].children.append(self.summary_range)
        self._plot()

    def _update_summary_range(self, attr, old, new):
        self._plot()


class FeatureSummaryScore(SummaryScore):
    """Class to study the features summary over a long period of time."""
    def __init__(self, title, *args, **kwargs):
        self.mac = '88:4A:EA:69:E1:59'
        self.summaries = FEATURE_SUMMARIES
        super().__init__(title, *args, **kwargs)

    def _plot(self):
        self.plots.children = [self.spinner]
        self.data = sequence(self._mac.value, self.summary_range.value,
                             start=self.start, end=self.end)

        self.staves = {}
        _kw = {'data': self.data,
               'score': self,
               'start': self.start,
               'end': self.end}

        if self.summary_range.value != 'summary_10s':
            mapper = {'summary_1m': 'summary_10s',
                      'summary_5m': 'summary_10s',
                      'summary_30m': 'summary_1m',
                      'summary_6H': 'summary_1m',
                      'summary_1D': 'summary_5m',
                      'summary_7D': 'summary_30m'}
            self.summary_feat = mapper[self.summary_range.value]
            self.data_feat = sequence(self._mac.value, self.summary_feat,
                                      start=self.start, end=self.end)
            _kw['data_feat'] = self.data_feat

        self.device = env.Device[self._mac.value]
        for feature in self.device.features:
            f0 = self.device.features[0]
            _kw['feature'] = feature
            self.staves[feature] = stv.FeatureSummaryStave(feature, **_kw)
            self.staves[feature].fig.x_range = self.staves[f0].fig.x_range
        self.plots.children = [stave.plot for stave in self.staves.values()]

    def refresh_plot(self):
        self.summary_range.value = get_feature_range_from(self.start, self.end)
        self._plot()


class MetricSummaryScore(SummaryScore):
    """Class to study the features summary over a long period of time."""
    def __init__(self, title, *args, **kwargs):
        self.mac = '88:4A:EA:69:E1:59'
        self.summaries = METRIC_SUMMARIES
        super().__init__(title, *args, **kwargs)

    def _plot(self):
        self.plots.children = [self.spinner]
        self.data = sequence(self._mac.value, self.summary_range.value,
                             start=self.start, end=self.end)
        self.staves = {}
        _kw = {'mac': self._mac.value,
               'score': self,
               'start': self.start,
               'end': self.end}

        if self.end - self.start > pd.Timedelta(2, 'h'):
            mapper = {'MetricSummary5m': 'summary_10s',
                      'MetricSummary30m': 'summary_10s',
                      'MetricSummaryS1': 'summary_10s',
                      'MetricSummaryS2': 'summary_10s',
                      'MetricSummaryS3': 'summary_10s',
                      'MetricSummary1D': 'summary_5m',
                      'MetricSummary1M': 'summary_6H'}
            self.summary_feat = mapper[self.summary_range.value]
            self.data_feat = sequence(self._mac.value,
                                      self.summary_feat,
                                      start=self.start,
                                      end=self.end)
            _kw['data'] = self.data_feat
            self.staves[ACCEL] = stv.FeatureSummaryStave(ACCEL, **_kw)
            self.staves[ACCEL].fig.plot_height = 300
        else:
            self.staves[ACCEL] = stv.PressProdStave(ACCEL, **_kw)
            self.staves[ACCEL].fig.plot_height = 300
        _kw['data'] = self.data

        CC = {'pressprod': {}}
        CC['connectivity'] = {'connectivity_connected': 'lightgreen',
                              'connectivity_disconnected': 'lightblue',
                              'connectivity_na': 'white'}
        CC['activity'] = {'activity_producing': 'lightgreen',
                          'activity_idle': 'lightgrey',
                          'activity_operating': 'lightblue',
                          'activity_setup': 'lightyellow',
                          'activity_off': 'lightyellow',
                          'activity_na': 'white'}
        CC['condition'] = {'condition_critical': 'red',
                           'condition_warning': 'orange',
                           'condition_operating': 'lightblue',
                           'condition_idle': 'lightgreen',
                           'condition_na': 'white'}

        # Inclusion with self.device.features
        to_show = {'pressprod': {'connectivity', 'activity', 'pressprod'},
                   'vibrations': {'connectivity', 'condition'}}

        self.device = env.Device[self._mac.value]
        for f in set(CC.keys()) & to_show[self.device.function]:
            if f == 'pressprod':
                self.staves[f] = stv.HeatMapStave('production_count', **_kw)
            else:
                self.staves[f] = stv.StackedPercentageStave(f, cc=CC[f], **_kw)
            self.staves[f].fig.x_range = self.staves[ACCEL].fig.x_range
        self.plots.children = [stave.plot for stave in self.staves.values()]

    def refresh_plot(self):
        self.summary_range.value = get_metric_range_from(self.start, self.end)
        self._plot()
