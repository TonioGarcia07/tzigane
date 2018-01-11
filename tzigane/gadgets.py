#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The basic classes are defined in this file.
"""
# ===================================================================
# Imports
# ===================================================================

from bokeh.models import Line, ColumnDataSource
from bokeh.layouts import layout
from bokeh.application import Application
from bokeh.application.handlers import FunctionHandler

ACCEL = 'accel_energy_512'

# ===================================================================
# Helper function
# ===================================================================


def remove_fig(name, fig):
    fig.renderers = list(filter(lambda x: x.name != name, fig.renderers))


# ===================================================================
# Class definitions
# ===================================================================


class Base:
    def __init__(self):
        """Base class to allow callbacks & interactions with the bokeh client.
        See difference between 'bokeh server' and 'bokeh client'."""
        self.layout = layout()

        # Application and callback enabler
        def add_doc(doc):
            doc.add_root(self.layout)
        self.app = Application(FunctionHandler(add_doc))


class Gadget(Base):
    """Base class for the gadgets. Every gadget is linked with a stave."""
    def __init__(self, stave, name, *args, **kwargs):
        super().__init__()
        self.stave, self.name = stave, name
        self.tool = kwargs.setdefault('tool', None)

    def _update(self, *args, **kwargs):
        self._show()

    def _show(self, *args, **kwargs):
        """Plot the gadget in the stave.fig and add the tool to stave.tools."""
        if self.tool is not None:
            self.stave.tools.children.append(self.tool)


class hLine(Gadget):
    def __init__(self, stave, name, value, *args, **kwargs):
        super().__init__(stave, name)
        self.value = value
        self.color = kwargs.setdefault('color', 'green')
        self.width = kwargs.setdefault('width', 1)
        self.dash = kwargs.setdefault('dash', 'solid')
        self.kw_ = {'name': self.name,
                    'line_color': self.color,
                    'line_width': self.width,
                    'line_dash': self.dash}
        self.line = Line(x='x', y='y', **self.kw_)
        self.line_source = ColumnDataSource(data=dict(x=[], y=[]))

    def _update(self, *args, **kwargs):
        self.start = kwargs.setdefault('start', self.stave.start)
        self.end = kwargs.setdefault('end', self.stave.end)
        self.value = kwargs.setdefault('value', self.value)
        self._show()

    def _show(self):
        remove_fig(self.name, self.stave.fig)
        self.line_source.data['x'] = [self.start, self.end]
        self.line_source.data['y'] = [self.value, self.value]
        self.stave.fig.add_glyph(self.line_source, self.line)


class hSlider(hLine):
    def __init__(self, stave, name, slider, *args, **kwargs):
        super().__init__(stave, name, slider.value, *args, **kwargs)
        self.slider = slider

    def _show(self):
        remove_fig(self.name, self.stave.fig)
        self.x = [self.start, self.end]
        self.y = [self.slider.value, self.slider.value]
        self.line_source.data.update({'x': self.x, 'y': self.y})
        self.stave.fig.add_glyph(self.line_source, self.line)

        def update(attr, old, new):
            self.x = [self.start, self.end]
            self.y = [self.slider.value, self.slider.value]
            self.line_source.data.update({'x': self.x, 'y': self.y})

        self.slider.on_change('value', update)
        self.stave.tools.children.append(self.slider)


class pFunction(hLine):
    def __init__(self, stave, name, slider, *args, **kwargs):
        super().__init__(stave, name, slider.value, *args, **kwargs)
        self.slider = slider
        self.df = stave.df
        self.source = ColumnDataSource(data=dict(x=self.df.index, y=self.df))

    def _show(self):
        remove_fig(self.name, self.stave.fig)
        self.y = self.df[self.df > self.slider.value]
        self.x = self.y.index
        self.line_source.data.update({'x': self.x, 'y': self.y})
        self.stave.fig.add_glyph(self.line_source, self.line)

        def update(attr, old, new):
            self.data = self.stave.data.data[self.stave.feature]
            self.y = self.data[self.data > self.slider.value]
            self.x = self.y.index
            self.line_source.data.update({'x': self.x, 'y': self.y})

        self.slider.on_change('value', update)
        self.stave.tools.children.append(self.slider)
