#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: antoine
"""
# ===================================================================
# Imports
# ===================================================================

import tzigane.scores as tsc

# ===================================================================
# Pages
# ===================================================================


class PressProdBatchScore(tsc.PressProdScore, tsc.BatchScore):
    """ To study the Production of presses in batch mode."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)


class PressProdStreamingScore(tsc.PressProdScore, tsc.StreamingScore):
    """ To study the Production of presses in streaming mode."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)


class ConditionBatchScore(tsc.ConditionScore, tsc.BatchScore):
    """ To study the Production of presses in batch mode."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)


class FeatureSummaryBatchScore(tsc.FeatureSummaryScore, tsc.BatchScore):
    """ To have an overview of the features."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)


class MetricSummaryBatchScore(tsc.MetricSummaryScore, tsc.BatchScore):
    """ To have an overview of the metrics."""
    def __init__(self, title, *args, **kwargs):
        super().__init__(title, *args, **kwargs)
