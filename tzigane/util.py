# -*- coding: utf-8 -*-

import pandas as pd

from anaximander.utilities.nxtime import datetime, now
from anaximander.data import DataTract
from anaximander.utilities.nxrange import time_interval

import dataforge.environment as env
from dataforge.baseschemas import DeviceData, DeviceDiagnostics
from dataforge.activity import ActivityTransitionLogs
from dataforge.condition import ConditionTransitionLogs
from dataforge.connectivity import ConnectivityTransitionLogs
from dataforge.pressproduction import PressProdTransitionLogs, StrokeCountLogs
from dataforge.devicestatus import DeviceStatusIOError
import dataforge.summary as smr


TABLE = {'summary_10s': smr.FeatureSummary10s,
         'summary_1m': smr.FeatureSummary1m,
         'summary_5m': smr.FeatureSummary5m,
         'summary_30m': smr.FeatureSummary30m,
         'summary_6H': smr.FeatureSummary6H,
         'summary_1D': smr.FeatureSummary1D,
         'summary_7D': smr.FeatureSummary7D,
         'MetricSummary5m': smr.MetricSummary5m,
         'MetricSummary30m': smr.MetricSummary30m,
         'MetricSummaryS1': smr.MetricSummaryS1,
         'MetricSummaryS2': smr.MetricSummaryS2,
         'MetricSummaryS3': smr.MetricSummaryS3,
         'MetricSummary1D': smr.MetricSummary1D,
         'MetricSummary1M': smr.MetricSummary1M,
         'accel_energy_512': DeviceData,
         'accel_energy_128_0': DeviceData,
         'accel_energy_128_1': DeviceData,
         'accel_energy_128_2': DeviceData,
         'accel_energy_128_3': DeviceData,
         'audio': DeviceData,
         'temperature': DeviceData,
         'velocity_x': DeviceData,
         'velocity_y': DeviceData,
         'velocity_z': DeviceData,
         'latency': DeviceDiagnostics,
         'activity': ActivityTransitionLogs,
         'condition': ConditionTransitionLogs,
         'connectivity': ConnectivityTransitionLogs,
         'pressprod': PressProdTransitionLogs,
         'stroke': StrokeCountLogs}


def _qrange(start=None, end=None, duration=None, res="ts"):
    """Helper function to retrieve the timestamp (or string) for start/end."""
    try:
        end = pd.Timestamp(end, tz='utc')
        assert pd.notnull(end)
        if duration is not None:
            try:
                duration = pd.Timedelta(duration)
                assert pd.notnull(duration)
                start = end - duration
            except Exception as e:
                pass
    except AssertionError as e:
        end = pd.Timestamp("now", tz='utc')

    try:
        start = pd.Timestamp(start, tz='utc')
        assert pd.notnull(start)
        if duration is not None:
            try:
                duration = pd.Timedelta(duration)
                assert pd.notnull(duration)
                end = start + duration
            except Exception as e:
                pass
    except AssertionError as e:
        try:
            duration = pd.Timedelta(duration)
            assert pd.notnull(duration)
        except Exception as e:
            duration = pd.Timedelta('1h')
        start = end - duration

    if res == "ts":
        return (start, end)
    else:
        return (start.strftime('%Y-%m-%d %H:%M:%S'),
                end.strftime('%Y-%m-%d %H:%M:%S'))


def sequence(mac, label, start=None, end=None, duration=None, maxrows=None,
             maxraise=None, check_status=True):
    """Helper function that retrieves the data corresponding to the label.
    Input:
        - device: can be either the device object or the mac of the device,
        - label: cf. table above.
        - columns: to specify the columns wanted from the data.
    Output:
        the corresponding dataframe.
    """
    if not isinstance(mac, str):
        mac = mac.mac
    device = env.Device[mac]

    start, end = _qrange(start, end, duration)
    table = TABLE[label]
    table = table.bigtable if isinstance(table, DataTract) else table

    table_cols = [j for i in [el for el in table.columns.values()] for j in i]

    if label in table_cols:
        q = table.query(label, mac=mac, timestamp=(start, end))
        frame = q.sequence(context=device, maxrows=maxrows, maxraise=maxraise)
    elif 'states' in table.columns.keys():
        query = table.query(mac=mac, timestamp=(start, end))
        frame = query.sequence(context=device, maxrows=maxrows,
                               maxraise=maxraise)
        cutoff = None
        if check_status:
            try:
                status_type = type(device.get_status(label))
                assert status_type.logs.bigtable is not None
            except (KeyError, AttributeError, AssertionError):
                # This is ignored for convenience
                pass
            else:
                latest_status = status_type.recall(device, when=end)
                cutoff = latest_status.certificate.timestamp
        if cutoff is None:
            if end is None:
                cutoff = now()
            else:
                cutoff = datetime(end)

        if end > cutoff and start < cutoff:
            frame.keyrange['timestamp'] = time_interval(start, cutoff)
        elif start >= cutoff:
            msg = "Cannot provide state sequence from {0} to {1}, " + \
                "which is beyond the latest update {2}."
            raise DeviceStatusIOError(msg.format(start, end, cutoff))

        if not frame.empty:
            return frame

        q_prev = table.query(mac=mac, timestamp=(None, end))
        try:
            prev = q_prev.first()
        except Exception as e:
            print(e)
        else:
            frame.unique = prev.next_state
    else:
        q = table.query(mac=mac, timestamp=(start, end))
        frame = q.sequence(context=device, maxrows=maxrows, maxraise=maxraise)
    return frame
