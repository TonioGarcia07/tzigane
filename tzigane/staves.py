#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The basic classes are defined in this file.
"""
# ===================================================================
# Imports
# ===================================================================

import abc
import logging
import pandas as pd
import dataforge.condition as cnd
import dataforge.environment as env
from tzigane.util import _qrange, sequence
from anaximander.data.digest import HighlightDigest
from bokeh.models import WheelZoomTool, BoxSelectTool, ColumnDataSource
from bokeh.layouts import layout, widgetbox, row
from bokeh.models.widgets import Button
from bokeh.plotting import figure
from bokeh.models import Slider, HoverTool
from bokeh.palettes import magma

from tzigane.gadgets import Base, Gadget, hLine, hSlider, pFunction

ACCEL = 'accel_energy_512'
PALETTE = magma(40)[30:][::-1]


# ===================================================================
# Class definitions
# ===================================================================


class ADict(dict):
    def __init__(self, *args, **kwargs):
        super(ADict, self).__init__(*args, **kwargs)
        self.__dict__ = self


class Stave(Base):
    """Class to gather all the elements for a plot."""
    def __init__(self, title, *args, **kwargs):
        super().__init__()
        # Get arguments
        self.title = title
        self.mac = kwargs.setdefault('mac', None)
        self.start = kwargs.setdefault('start', None)
        self.end = kwargs.setdefault('end', None)

        # Definition of the global layout
        self.fig = figure(plot_width=1200, x_axis_type='datetime',
                          tools='pan,box_zoom,reset', active_drag='pan',
                          title=self.title, name=self.title)
        self.gadgets = []
        self.tools = widgetbox(self.gadgets)
        self.plot = layout(row([self.fig, self.tools]))

    def init_stave(self):
        self._init_fig()
        self._update_fig()
        self.update_time_range(self.start, self.end)
        self._init_gadgets()
        self._update_gadgets()

    def update_time_range(self, start, end):
        self.start, self.end = _qrange(start=start, end=end)
        self.fig.x_range.start = self.start.value / 1e6
        self.fig.x_range.end = self.end.value / 1e6

    def _init_fig(self):
        """Contains:
             - definition of all the attributes of the figure,
             - definition of the source,
             - definition of what to draw from the source."""
        pass

    @abc.abstractproperty
    def _update_fig(self):
        """Contains:
             - method to fetch the data,
             - update the source (automatically updates the fig)"""
        return NotImplemented

    def _init_gadgets(self):
        """List of all the gadgets to add to the stave."""
        self.gadgets = []

    def _update_gadgets(self):
        """Update the gadgets (mainly update the time range)."""
        for gadget in self.gadgets:
            gadget._update(start=self.start, end=self.end)


class FeatureStave(Stave):
    """Class for the time series.
    Warning: Please move the plot once if you want the time range to work."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)
        self.feature = kwargs.setdefault('feature', title)
        self.init_stave()

    def _init_fig(self):
        self.fig.add_tools(BoxSelectTool(dimensions="width"))
        self.fig.plot_height = 500
        self.source = ColumnDataSource({'timestamp': [],
                                        self.feature: []})
        self.fig.line('timestamp',
                      self.feature,
                      source=self.source)

    def _update_fig(self):
        self.data = sequence(self.mac, self.feature, start=self.start,
                             end=self.end)
        try:
            df = self.data.data[[self.feature]]
            self.source.data = self.source.from_df(df)
        except Exception as e:
            logging.exception(e)


class CycleStave(Stave):
    """Class for the events that last."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)
        self.init_stave()

    def _init_fig(self):
        self.fig.add_tools(WheelZoomTool(dimensions='width'))
        self.fig.plot_height = 150
        self.source = ColumnDataSource(data=dict(bottom=[], top=[],
                                                 left=[], right=[],
                                                 color=[]))
        self.fig.quad(bottom='bottom', top='top',
                      left='left', right='right',
                      color='color', source=self.source)

    def _update_fig(self):
        self.data = sequence(self.mac, self.title, start=self.start,
                             end=self.end)
        self._plot_fig()

    def _plot_fig(self):
        dg = self.data
        dg = dg.as_digest() if not isinstance(dg, HighlightDigest) else dg
        dfs = []
        for i, shade in enumerate(dg.shades()):
            highlighter = dg.highlighter_type(shade)
            color = highlighter.plargs.get('color', 'blank')
            res = [(el.lower, el.upper, shade, color, 0, 1)
                   for el in dg.highlights(shade)]
            index = [el[0] for el in res]
            dfs.append(pd.DataFrame(res, index=index,
                                    columns=['left', 'right', 'shade',
                                             'color', 'bottom', 'top']))
        dfs = list(filter(lambda x: not x.empty, dfs))
        self.source.data = self.source.from_df(pd.concat(dfs).sort_index())


class ComparisonStave(CycleStave):
    def __init__(self, stave1, stave2):
        self.title = stave1.title + ' vs ' + stave2.title


class AssessmentStave(CycleStave):
    """Class to run and plot assessments."""
    def __init__(self, score, title, *args, **kwargs):
        self.score = score
        super().__init__(title, *args, **kwargs)

    def init_stave(self):
        self._init_fig()
        self.update_time_range(self.start, self.end)
        self._init_gadgets()
        self._update_fig()
        self._update_gadgets()

    def _init_gadgets(self):
        self._assess = Button(label="Run Condition Assessment")
        self._assess.on_click(self.update_assessment)
        self._reset = Button(label="Reset Thresholds")
        self._reset.on_click(self.reset_thresholds)
        self.gadgets = [Gadget(self, 'ResetThresholds', tool=self._reset),
                        Gadget(self, 'ConditionAssessment', tool=self._assess)]

    def _update_fig(self):
        self.update_assessment()

    def update_assessment(self, *args, **kwargs):
        dev = env.Device[self.mac]
        specs = {}
        for feat in self.score.features:
            feat_dict = ADict()
            stave = self.score.staves[feat]
            for i, lev in enumerate(['high', 'med', 'low']):
                slider = stave.tools.children[i + 1]
                feat_dict[lev] = slider.value
            specs[feat] = feat_dict
        dev.specs['thresholds'].update(specs)
        assess = cnd.VibrationsConditionAssessment(dev, self.start,
                                                   self.end)
        self.data = assess()
        self._plot_fig()

    def reset_thresholds(self, *args, **kwargs):
        for feat in self.score.features:
            stave = self.score.staves[feat]
            thresholds = self.score.thresholds[feat]
            for i, lev in enumerate(['high', 'med', 'low']):
                slider = stave.tools.children[i + 1]
                slider.value = thresholds[i]


class PressProdStave(FeatureStave):
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)

    def _init_gadgets(self):
        threshold = env.Device[self.mac].specs['thresholds'][self.feature].high
        self.gadgets = [hLine(self, 'threshold', threshold)]


class FeatureSummaryStave(FeatureStave):
    def __init__(self, title, *args, **kwargs):
        self.data = kwargs.setdefault('data', None)
        self.data_feat = kwargs.setdefault('data_feat', None)
        self.score = kwargs.setdefault('score', None)
        super().__init__(title, *args, **kwargs)

    def _init_fig(self):
        self.fig.plot_height = 150
        self.source = ColumnDataSource({'timestamp': [],
                                        self.feature + '_max': [],
                                        self.feature + '_mean': [],
                                        self.feature + '_min': []})
        for legend, color in zip(['max', 'mean', 'min'],
                                 ['green', 'black', 'red']):
            self.fig.line('timestamp', self.feature + '_' + legend,
                          source=self.source, legend=legend, color=color)
        self.fig.legend.location = "top_right"
        self.fig.legend.click_policy = "hide"

        # If the range is small, we allow to fetch the whole data.
        # Otherwise, we plot a summary with a higher frequency.
        if self.score.summary_range.value == 'summary_10s':
            self.source_feat = ColumnDataSource({'timestamp': [],
                                                 self.feature: []})
            self.fig.line('timestamp', self.feature, source=self.source_feat)
        else:
            self.source_feat = ColumnDataSource({'timestamp': [],
                                                 self.feature + '_max': [],
                                                 self.feature + '_mean': [],
                                                 self.feature + '_min': []})
            for legend, color in zip(['max', 'mean', 'min'],
                                     ['green', 'black', 'red']):
                self.fig.line('timestamp', self.feature + '_' + legend,
                              source=self.source_feat)

    def _update_fig(self):
        assert self.data is not None and self.score is not None
        df = self.data.data[[self.feature + l
                             for l in ['_max', '_mean', '_min']]]
        self.source.data = self.source.from_df(df)

        if self.score.summary_range.value == 'summary_10s':
            self.data_feat = sequence(self.score._mac.value, self.feature,
                                      start=self.start, end=self.end)
            df_feat = self.data_feat.data[[self.feature]]
            self.source_feat.data = self.source_feat.from_df(df_feat)
        elif self.data_feat is not None:
            assert self.score is not None
            df_feat = self.data_feat.data[[self.feature + l
                                           for l in ['_max', '_mean', '_min']]]
            self.source_feat.data = self.source.from_df(df_feat)


class ConditionStave(FeatureStave):
    def __init__(self, title, thresh_source, *args, **kwargs):
        self.thresh_source = thresh_source
        super().__init__(title, *args, **kwargs)

    def _init_fig(self):
        self.fig.plot_height = 180
        self.source = ColumnDataSource({'timestamp': [], self.feature: []})
        self.fig.line('timestamp', self.feature, source=self.source)

    def _init_gadgets(self):
        self.df = self.data.data[self.title]
        slider = Slider(start=int(self.df.min()), end=int(self.df.max()),
                        value=self.df.max() - 2, step=0.1, title="Hull",
                        name=self.title)
        self.gadgets = [pFunction(self, 'Hull', slider)]
        for i, lev in enumerate(self.thresh_source.data['index']):
            color = {'high': 'red', 'med': 'orange', 'low': 'black'}[lev]
            val = self.thresh_source.data[self.title][i]
            name = "{} ({})".format(lev, val)
            slider = Slider(title=name, start=max(0, val / 2 - 5),
                            end=max(val * 1.2, 5), value=val, step=0.1,
                            name=self.title)
            gadget = hSlider(self, self.title, slider, color=color)
            line = hLine(self, self.title, val, color=color, dash='dashed')
            self.gadgets.extend([gadget, line])


class StackedPercentageStave(CycleStave):
    def __init__(self, title, cc, *args, **kwargs):
        self.data = kwargs.setdefault('data', None)
        self.score = kwargs.setdefault('score', None)
        self.cc = cc
        super().__init__(title, *args, **kwargs)

    def _init_fig(self):
        self.fig.plot_height = 220
        self.source = ColumnDataSource(data=dict(bottom=[], top=[],
                                                 left=[], right=[],
                                                 color=[], legend=[],
                                                 percent=[]))

        self.fig.quad(bottom='bottom', top='top',
                      left='left', right='right',
                      color='color', legend='legend',
                      source=self.source, line_color='white')

        hoover_tool = HoverTool(tooltips=[("state", "@legend"),
                                          ("start", "@left{%Hh%M}"),
                                          ("end", "@right{%Hh%M}"),
                                          ("percent", "@percent{0.00}%")],
                                formatters={"left": "datetime",
                                            "right": "datetime"})
        self.fig.add_tools(hoover_tool)

    def _update_fig(self):
        assert self.data is not None and self.score is not None
        self._plot_fig()

    def _plot_fig(self):
        df = self.data.data[[k for k, v in self.cc.items()]]
        left = df.index
        right = df.index[1:]
        right = right.insert(len(right), left[-1] + (left[-1] - left[-2]))
        df['total'] = df.sum(axis=1)
        for col in df:
            df[col] = df.apply(lambda r: 100 * r[col] / r['total'], axis=1)
        df = df.cumsum(axis=1)

        dfs = []
        bottom = [0 for el in left]
        for column, color in self.cc.items():
            top = df[column]
            res = pd.DataFrame({'left': left, 'right': right,
                                'bottom': bottom, 'top': top})
            res['color'] = color
            res['legend'] = column.split('_')[-1]
            res['percent'] = res['top'] - res['bottom']
            bottom = top
            dfs.append(res)
        self.source.data = self.source.from_df(pd.concat(dfs).sort_index())


class HeatMapStave(CycleStave):
    def __init__(self, title, *args, **kwargs):
        self.data = kwargs.setdefault('data', None)
        self.score = kwargs.setdefault('score', None)
        super().__init__(title, *args, **kwargs)

    def _init_fig(self):
        self.fig.plot_height = 150
        self.source = ColumnDataSource(data=dict(bottom=[], top=[], y=[],
                                                 left=[], right=[], x=[],
                                                 color=[], count=[], text=[]))

        self.fig.quad(bottom='bottom', top='top',
                      left='left', right='right',
                      color='color',
                      source=self.source, line_color='white')
        self.fig.text(x='x', y='y', text='text', source=self.source)

        hoover_tool = HoverTool(tooltips=[("start", "@left{%Hh%M}"),
                                          ("end", "@right{%Hh%M}"),
                                          ("Count", "@count")],
                                formatters={"left": "datetime",
                                            "right": "datetime"})
        self.fig.add_tools(hoover_tool)

    def _update_fig(self):
        assert self.data is not None and self.score is not None
        self._plot_fig()

    def _plot_fig(self):
        df = self.data.data[[self.title]]
        df.columns = ['count']
        df['percent'] = 100 * df / ((1 + df.max()) * len(PALETTE))
        df = df.astype(int)
        df['color'] = df['percent'].map(lambda x: PALETTE[x])
        df['left'] = df.index
        df['right'] = df['left'].shift(-1)
        df['right'].fillna(df.index[-1] + (df.index[-1] - df.index[-2]),
                           inplace=True)
        df['bottom'] = 0
        df['top'] = 1
        df['x'] = df['left'] + (df['right'] - df['left']) / 2
        df['y'] = 0.5
        df['text'] = df['count'].map(str)
        df.loc[df.text == '0', 'text'] = ''
        self.source.data = self.source.from_df(df)
