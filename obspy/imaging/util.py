# -*- coding: utf-8 -*-
"""
Waveform plotting utilities.

:copyright:
    The ObsPy Development Team (devs@obspy.org)
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)
from future.builtins import *  # NOQA @UnusedWildImport
from future.utils import native_str

import re

from matplotlib.dates import AutoDateFormatter, DateFormatter, num2date
from matplotlib.ticker import FuncFormatter


def _seconds_to_days(sec):
    return sec / 3600.0 / 24.0


def decimal_seconds_format_x_decimals(decimals=None):
    """
    Function factory for format functions to format date ticklabels with
    given number of decimals to seconds (stripping trailing zeros).

    :type decimals: int
    :param decimals: Number of decimals for seconds after which to cut off
        format string. Decimals are left alone if not specified.
    """
    def func(x, pos=None):
        x = num2date(x)
        ret = x.strftime('%H:%M:%S.%f')
        ret = ret.rstrip("0")
        ret = ret.rstrip(".")
        _decimals = decimals
        # show more decimals in matplotlib info toolbar (for formatting of
        # mouse-over x coordinate, which is in-between picks and needs higher
        # accuracy)
        if pos is None and _decimals is not None:
            _decimals += 2
        if "." in ret and _decimals is not None:
            ret = ret[:ret.find(".") + _decimals + 1]
        return ret
    return func


def decimal_seconds_format_date_first_tick(x, pos=None):
    """
    This format function is used to format date ticklabels with decimal
    seconds but stripping trailing zeros.
    """
    x = num2date(x)
    if pos == 0:
        fmt = '%b %d %Y\n%H:%M:%S.%f'
    else:
        fmt = '%H:%M:%S.%f'
    ret = x.strftime(fmt)
    ret = ret.rstrip("0")
    ret = ret.rstrip(".")
    return ret


class ObsPyAutoDateFormatter(AutoDateFormatter):
    """
    Derived class to allow for more customized formatting with older matplotlib
    versions (see matplotlib/matplotlib#2507).
    """
    def __init__(self, *args, **kwargs):
        super(ObsPyAutoDateFormatter, self).__init__(*args, **kwargs)
        self.scaled[1. / 24.] = '%H:%M'
        self.scaled[1. / (24. * 60.)] = '%H:%M:%S'
        self.scaled[_seconds_to_days(10)] = \
            FuncFormatter(decimal_seconds_format_x_decimals(1))
        # for some reason matplotlib is not using the following intermediate
        # decimal levels (probably some precision issue..) and falls back to
        # the lowest level immediately.
        self.scaled[_seconds_to_days(2e-1)] = \
            FuncFormatter(decimal_seconds_format_x_decimals(2))
        self.scaled[_seconds_to_days(2e-2)] = \
            FuncFormatter(decimal_seconds_format_x_decimals(3))
        self.scaled[_seconds_to_days(2e-3)] = \
            FuncFormatter(decimal_seconds_format_x_decimals(4))
        self.scaled[_seconds_to_days(2e-4)] = \
            FuncFormatter(decimal_seconds_format_x_decimals(5))

    def __call__(self, x, pos=None):
        scale = float(self._locator._get_unit())
        fmt = self.defaultfmt

        for k in sorted(self.scaled):
            if k >= scale:
                fmt = self.scaled[k]
                break

        if isinstance(fmt, (str, native_str)):
            self._formatter = DateFormatter(fmt, self._tz)
            return self._formatter(x, pos)
        elif hasattr(fmt, '__call__'):
            return fmt(x, pos)
        else:
            raise NotImplementedError()


def _compare_IDs(id1, id2):
    """
    Compare two trace IDs by network/station/location single character
    component codes according to sane ZNE/ZRT/LQT order. Any other characters
    are sorted afterwards alphabetically.

    >>> networks = ["A", "B", "AB"]
    >>> stations = ["X", "Y", "XY"]
    >>> locations = ["00", "01"]
    >>> channels = ["EHZ", "EHN", "EHE", "Z"]
    >>> trace_ids = []
    >>> for net in networks:
    ...     for sta in stations:
    ...         for loc in locations:
    ...             for cha in channels:
    ...                 trace_ids.append(".".join([net, sta, loc, cha]))
    >>> from random import shuffle
    >>> shuffle(trace_ids)
    >>> trace_ids = sorted(trace_ids, key=_compare_IDs_keyfunc)
    >>> print(" ".join(trace_ids))  # doctest: +NORMALIZE_WHITESPACE
    A.X.00.Z A.X.00.EHZ A.X.00.EHN A.X.00.EHE A.X.01.Z A.X.01.EHZ A.X.01.EHN
    A.X.01.EHE A.XY.00.Z A.XY.00.EHZ A.XY.00.EHN A.XY.00.EHE A.XY.01.Z
    A.XY.01.EHZ A.XY.01.EHN A.XY.01.EHE A.Y.00.Z A.Y.00.EHZ A.Y.00.EHN
    A.Y.00.EHE A.Y.01.Z A.Y.01.EHZ A.Y.01.EHN A.Y.01.EHE AB.X.00.Z AB.X.00.EHZ
    AB.X.00.EHN AB.X.00.EHE AB.X.01.Z AB.X.01.EHZ AB.X.01.EHN AB.X.01.EHE
    AB.XY.00.Z AB.XY.00.EHZ AB.XY.00.EHN AB.XY.00.EHE AB.XY.01.Z AB.XY.01.EHZ
    AB.XY.01.EHN AB.XY.01.EHE AB.Y.00.Z AB.Y.00.EHZ AB.Y.00.EHN AB.Y.00.EHE
    AB.Y.01.Z AB.Y.01.EHZ AB.Y.01.EHN AB.Y.01.EHE B.X.00.Z B.X.00.EHZ
    B.X.00.EHN B.X.00.EHE B.X.01.Z B.X.01.EHZ B.X.01.EHN B.X.01.EHE B.XY.00.Z
    B.XY.00.EHZ B.XY.00.EHN B.XY.00.EHE B.XY.01.Z B.XY.01.EHZ B.XY.01.EHN
    B.XY.01.EHE B.Y.00.Z B.Y.00.EHZ B.Y.00.EHN B.Y.00.EHE B.Y.01.Z B.Y.01.EHZ
    B.Y.01.EHN B.Y.01.EHE
    """
    # remove processing info which was added previously
    id1 = re.sub(r'\[.*', '', id1)
    id2 = re.sub(r'\[.*', '', id2)
    netstaloc1, cha1 = id1.upper().rsplit(".", 1)
    netstaloc2, cha2 = id2.upper().rsplit(".", 1)
    netstaloc1 = netstaloc1.split()
    netstaloc2 = netstaloc2.split()
    # sort by network, station, location codes
    cmp_ = cmp(netstaloc1, netstaloc2)
    if cmp_ != 0:
        return cmp_
    # only channel is differing, sort by..
    #  - length of channel code
    #  - last letter of channel code
    cmp_ = cmp(len(cha1), len(cha2))
    if cmp_ != 0:
        return cmp_
    else:
        if len(cha1) == 0:
            return 0
    return _compare_component_code(cha1[-1], cha2[-1])


def _compare_component_code(comp1, comp2):
    """
    Compare two single character component codes according to sane ZNE/ZRT/LQT
    order. Any other characters are sorted afterwards alphabetically.

    >>> from random import shuffle
    >>> from string import ascii_lowercase, ascii_uppercase
    >>> lowercase = list(ascii_lowercase)
    >>> uppercase = list(ascii_uppercase)
    >>> shuffle(lowercase)
    >>> shuffle(uppercase)
    >>> component_codes = lowercase + uppercase
    >>> component_codes = sorted(component_codes,
    ...                          key=_compare_component_code_keyfunc)
    >>> print(component_codes)  # doctest: +NORMALIZE_WHITESPACE
    ['z', 'Z', 'n', 'N', 'e', 'E', 'r', 'R', 'l', 'L', 'q', 'Q', 't', 'T', 'a',
        'A', 'b', 'B', 'c', 'C', 'd', 'D', 'f', 'F', 'g', 'G', 'h', 'H', 'i',
        'I', 'j', 'J', 'k', 'K', 'm', 'M', 'o', 'O', 'p', 'P', 's', 'S', 'u',
        'U', 'v', 'V', 'w', 'W', 'x', 'X', 'y', 'Y']
    """
    order = "ZNERLQT"
    comp1 = comp1.upper()
    comp2 = comp2.upper()
    if comp1 in order:
        if comp2 in order:
            return order.index(comp1) - order.index(comp2)
        else:
            return -1
    else:
        if comp2 in order:
            return 1
        else:
            return cmp(comp1, comp2)


# Python 3 was stripped of cmp() builtin..
def cmp(a, b):
    return (a > b) - (a < b)


def cmp_to_key(mycmp):
    '''
    Convert a cmp= function into a key= function
    '''
    class K(object):
        def __init__(self, obj, *args):
            self.obj = obj

        def __lt__(self, other):
            return mycmp(self.obj, other.obj) < 0

        def __gt__(self, other):
            return mycmp(self.obj, other.obj) > 0

        def __eq__(self, other):
            return mycmp(self.obj, other.obj) == 0

        def __le__(self, other):
            return mycmp(self.obj, other.obj) <= 0

        def __ge__(self, other):
            return mycmp(self.obj, other.obj) >= 0

        def __ne__(self, other):
            return mycmp(self.obj, other.obj) != 0
    return K


# Python 3 doesn't have sorted(cmp=..) kwarg anymore. Python 2.6 does not have
# cmp_to_key, so use from https://wiki.python.org/moin/HowTo/
# Sorting#The_Old_Way_Using_the_cmp_Parameter
_compare_IDs_keyfunc = cmp_to_key(_compare_IDs)
_compare_component_code_keyfunc = cmp_to_key(_compare_component_code)


def _timestring(t):
    """
    Returns a full string representation of a
    :class:`~obspy.core.utcdatetime.UTCDateTime` object, stripping away
    trailing decimal-second zeros.

    >>> from obspy import UTCDateTime
    >>> print(_timestring(UTCDateTime("2012-04-05T12:12:12.123456Z")))
    2012-04-05T12:12:12.123456
    >>> print(_timestring(UTCDateTime("2012-04-05T12:12:12.120000Z")))
    2012-04-05T12:12:12.12
    >>> print(_timestring(UTCDateTime("2012-04-05T12:12:12.000000Z")))
    2012-04-05T12:12:12
    >>> print(_timestring(UTCDateTime("2012-04-05T12:12:00.000000Z")))
    2012-04-05T12:12:00
    >>> print(_timestring(UTCDateTime("2012-04-05T12:12:00.120000Z")))
    2012-04-05T12:12:00.12
    """
    return str(t).rstrip("Z0").rstrip(".")


if __name__ == '__main__':
    import doctest
    doctest.testmod(exclude_empty=True)
