#!/usr/bin/env python
#-------------------------------------------------------------------
# Filename: trigger.py
#  Purpose: Python trigger routines for seismology.
#   Author: Moritz Beyreuther
#    Email: moritz.beyreuther@geophysik.uni-muenchen.de
#
# Copyright (C) 2008-2012 Moritz Beyreuther
#-------------------------------------------------------------------
"""
Python trigger routines for seismology.

Module implementing the Recursive STA/LTA. Two versions, a fast ctypes one and
a bit slower python one. Further the classic and delayed STA/LTA, the
carlSTATrig and the zDetect are implemented.

.. seealso:: [Withers1998]_, p. 98

:copyright:
    The ObsPy Development Team (devs@obspy.org)
:license:
    GNU Lesser General Public License, Version 3
    (http://www.gnu.org/copyleft/lesser.html)
"""

import ctypes as C
import numpy as np
from obspy.signal.headers import clibsignal


def recSTALTA(a, nsta, nlta):
    """
    Recursive STA/LTA.

    Fast version written in C.

    :note: This version directly uses a C version via CTypes
    :type a: numpy.ndarray dtype float64
    :param a: Seismic Trace, numpy.ndarray dtype float64
    :type nsta: Int
    :param nsta: Length of short time average window in samples
    :type nlta: Int
    :param nlta: Length of long time average window in samples
    :rtype: numpy.ndarray dtype float64
    :return: Characteristic function of recursive STA/LTA

    .. seealso:: [Withers1998]_, p. 98
    """
    # be nice and adapt type if necessary
    a = np.require(a, 'float64', ['C_CONTIGUOUS'])
    ndat = len(a)
    charfct = np.empty(ndat, dtype='float64')
    # do not use pointer here:
    clibsignal.recstalta(a, charfct, ndat, nsta, nlta)
    return charfct


def recSTALTAPy(a, nsta, nlta):
    """
    Recursive STA/LTA written in Python.

    .. note::

        There exists a faster version of this trigger wrapped in C
        called :func:`~obspy.signal.trigger.recSTALTA` in this module!

    :type a: NumPy ndarray
    :param a: Seismic Trace
    :type nsta: Int
    :param nsta: Length of short time average window in samples
    :type nlta: Int
    :param nlta: Length of long time average window in samples
    :rtype: NumPy ndarray
    :return: Characteristic function of recursive STA/LTA

    .. seealso:: [Withers1998]_, p. 98
    """
    try:
        a = a.tolist()
    except:
        pass
    ndat = len(a)
    # compute the short time average (STA) and long time average (LTA)
    # given by Evans and Allen
    csta = 1. / nsta
    clta = 1. / nlta
    sta = 0.
    lta = 1e-99  # avoid zero devision
    charfct = [0.0] * len(a)
    icsta = 1 - csta
    iclta = 1 - clta
    for i in xrange(1, ndat):
        sq = a[i] ** 2
        sta = csta * sq + icsta * sta
        lta = clta * sq + iclta * lta
        charfct[i] = sta / lta
        if i < nlta:
            charfct[i] = 0.
    return np.array(charfct)


def carlSTATrig(a, nsta, nlta, ratio, quiet):
    """
    Computes the carlSTATrig characteristic function.

    eta = star - (ratio * ltar) - abs(sta - lta) - quiet

    :type a: NumPy ndarray
    :param a: Seismic Trace
    :type nsta: Int
    :param nsta: Length of short time average window in samples
    :type nlta: Int
    :param nlta: Length of long time average window in samples
    :type ration: Float
    :param ratio: as ratio gets smaller, carlSTATrig gets more sensitive
    :type quiet: Float
    :param quiet: as quiet gets smaller, carlSTATrig gets more sensitive
    :rtype: NumPy ndarray
    :return: Characteristic function of CarlStaTrig
    """
    m = len(a)
    #
    sta = np.zeros(len(a), dtype='float64')
    lta = np.zeros(len(a), dtype='float64')
    star = np.zeros(len(a), dtype='float64')
    ltar = np.zeros(len(a), dtype='float64')
    pad_sta = np.zeros(nsta)
    pad_lta = np.zeros(nlta)  # avoid for 0 division 0/1=0
    #
    # compute the short time average (STA)
    for i in xrange(nsta):  # window size to smooth over
        sta += np.concatenate((pad_sta, a[i:m - nsta + i]))
    sta /= nsta
    #
    # compute the long time average (LTA), 8 sec average over sta
    for i in xrange(nlta):  # window size to smooth over
        lta += np.concatenate((pad_lta, sta[i:m - nlta + i]))
    lta /= nlta
    lta = np.concatenate((np.zeros(1), lta))[:m]  # XXX ???
    #
    # compute star, average of abs diff between trace and lta
    for i in xrange(nsta):  # window size to smooth over
        star += np.concatenate((pad_sta,
                               abs(a[i:m - nsta + i] - lta[i:m - nsta + i])))
    star /= nsta
    #
    # compute ltar, 8 sec average over star
    for i in xrange(nlta):  # window size to smooth over
        ltar += np.concatenate((pad_lta, star[i:m - nlta + i]))
    ltar /= nlta
    #
    eta = star - (ratio * ltar) - abs(sta - lta) - quiet
    eta[:nlta] = -1.0
    return eta


def classicSTALTA(a, nsta, nlta):
    """
    Computes the standard STA/LTA from a given input array a. The length of
    the STA is given by nsta in samples, respectively is the length of the
    LTA given by nlta in samples.

    :type a: NumPy ndarray
    :param a: Seismic Trace
    :type nsta: Int
    :param nsta: Length of short time average window in samples
    :type nlta: Int
    :param nlta: Length of long time average window in samples
    :rtype: NumPy ndarray
    :return: Characteristic function of classic STA/LTA
    """
    #XXX From numpy 1.3 use numpy.lib.stride_tricks.as_strided
    #    This should be faster then the for loops in this fct
    #    Currently debian lenny ships 1.1.1
    m = len(a)
    #
    # compute the short time average (STA)
    sta = np.zeros(len(a), dtype='float64')
    pad_sta = np.zeros(nsta)
    # Tricky: Construct a big window of length len(a)-nsta. Now move this
    # window nsta points, i.e. the window "sees" every point in a at least
    # once.
    for i in xrange(nsta):  # window size to smooth over
        sta = sta + np.concatenate((pad_sta, a[i:m - nsta + i] ** 2))
    sta = sta / nsta
    #
    # compute the long time average (LTA)
    lta = np.zeros(len(a), dtype='float64')
    pad_lta = np.ones(nlta)  # avoid for 0 division 0/1=0
    for i in xrange(nlta):  # window size to smooth over
        lta = lta + np.concatenate((pad_lta, a[i:m - nlta + i] ** 2))
    lta = lta / nlta
    #
    # pad zeros of length nlta to avoid overfit and
    # return STA/LTA ratio
    sta[0:nlta] = 0
    return sta / lta


def delayedSTALTA(a, nsta, nlta):
    """
    Delayed STA/LTA.

    :type a: NumPy ndarray
    :param a: Seismic Trace
    :type nsta: Int
    :param nsta: Length of short time average window in samples
    :type nlta: Int
    :param nlta: Length of long time average window in samples
    :rtype: NumPy ndarray
    :return: Characteristic function of delayed STA/LTA

    .. seealso:: [Withers1998]_, p. 97
    """
    m = len(a)
    #
    # compute the short time average (STA) and long time average (LTA)
    # don't start for STA at nsta because it's muted later anyway
    sta = np.zeros(m, dtype='float64')
    lta = np.zeros(m, dtype='float64')
    for i in xrange(m):
        sta[i] = (a[i] ** 2 + a[i - nsta] ** 2) / nsta + sta[i - 1]
        lta[i] = (a[i - nsta - 1] ** 2 + a[i - nsta - nlta - 1] ** 2) / \
                 nlta + lta[i - 1]
    sta[0:nlta + nsta + 50] = 0
    return sta / lta


def zDetect(a, nsta):
    """
    Z-detector.

    :param nsta: Window length in Samples.

    .. seealso:: [Withers1998]_, p. 99
    """
    m = len(a)
    #
    # Z-detector given by Swindell and Snell (1977)
    sta = np.zeros(len(a), dtype='float64')
    # Standard Sta
    pad_sta = np.zeros(nsta)
    for i in xrange(nsta):  # window size to smooth over
        sta = sta + np.concatenate((pad_sta, a[i:m - nsta + i] ** 2))
    a_mean = np.mean(sta)
    a_std = np.std(sta)
    Z = (sta - a_mean) / a_std
    return Z


def triggerOnset(charfct, thres1, thres2, max_len=9e99, max_len_delete=False):
    """
    Calculate trigger on and off times.

    Given thres1 and thres2 calculate trigger on and off times from
    characteristic function.

    This method is written in pure Python and gets slow as soon as there
    are more then 1e6 triggerings ("on" AND "of") in charfct --- normally
    this does not happen.

    :type charfct: NumPy ndarray
    :param charfct: Characteristic function of e.g. STA/LTA trigger
    :type thres1: Float
    :param thres1: Value above which trigger (of characteristic function)
                   is activated (higher threshold)
    :type thres2: Float
    :param thres2: Value below which trigger (of characteristic function)
        is deactivated (lower threshold)
    :type max_len: Int
    :param max_len: Maximum length of triggered event in samples. A new
                    event will be triggered as soon as the signal reaches
                    again above thres1.
    :type max_len_delete: Bool
    :param max_len_delete: Do not write events longer than max_len into
                           report file.
    :rtype: List
    :return: Nested List of trigger on and of times in samples
    """
    # 1) find indices of samples greater than threshold
    # 2) calculate trigger "of" times by the gap in trigger indices
    #    above the threshold i.e. the difference of two following indices
    #    in ind is greater than 1
    # 3) in principle the same as for "of" just add one to the index to get
    #    start times, this operation is not supported on the compact
    #    syntax
    # 4) as long as there is a on time greater than the actual of time find
    #    trigger on states which are greater than last of state an the
    #    corresponding of state which is greater than current on state
    # 5) if the signal stays above thres2 longer than max_len an event
    #    is triggered and following a new event can be triggered as soon as
    #    the signal is above thres1
    ind1 = np.where(charfct > thres1)[0]
    if len(ind1) == 0:
        return []
    ind2 = np.where(charfct > thres2)[0]
    #
    on = [ind1[0]]
    of = [-1]
    of.extend(ind2[np.diff(ind2) > 1].tolist())
    on.extend(ind1[np.where(np.diff(ind1) > 1)[0] + 1].tolist())
    # include last pick if trigger is on or drop it
    if max_len_delete:
        # drop it
        of.extend([1e99])
        on.extend([on[-1]])
    else:
        # include it
        of.extend([ind2[-1]])
    #
    pick = []
    while on[-1] > of[0]:
        while on[0] <= of[0]:
            on.pop(0)
        while of[0] < on[0]:
            of.pop(0)
        if of[0] - on[0] > max_len:
            if max_len_delete:
                on.pop(0)
                continue
            of.insert(0, on[0] + max_len)
        pick.append([on[0], of[0]])
    return np.array(pick)


def pkBaer(reltrc, samp_int, tdownmax, tupevent, thr1, thr2, preset_len,
           p_dur):
    """
    Wrapper for P-picker routine by M. Baer, Schweizer. Erdbebendienst.

    :param reltrc: timeseries as numpy.ndarray float32 data, possibly filtered
    :param samp_int: number of samples per second
    :param tdownmax: if dtime exceeds tdownmax, the trigger is examined
                     for validity
    :param tupevent: min nr of samples for itrm to be accepted as a pick
    :param thr1: threshold to trigger for pick (c.f. paper)
    :param thr2: threshold for updating sigma  (c.f. paper)
    :param preset_len: no of points taken for the estimation of variance
                       of SF(t) on preset()
    :param p_dur: p_dur defines the time interval for which the
                  maximum amplitude is evaluated Originally set to 6 secs
    :return: (pptime, pfm) pptime sample number of parrival; pfm direction
             of first motion (U or D)

    .. note:: currently the first sample is not take into account

    .. seealso:: [Baer1987]_
    """
    pptime = C.c_int()
    # c_chcar_p strings are immutable, use string_buffer for pointers
    pfm = C.create_string_buffer("     ", 5)
    # be nice and adapt type if necessary
    reltrc = np.require(reltrc, 'float32', ['C_CONTIGUOUS'])
    # intex in pk_mbaer.c starts with 1, 0 index is lost, length must be
    # one shorter
    args = (len(reltrc) - 1, C.byref(pptime), pfm, samp_int,
            tdownmax, tupevent, thr1, thr2, preset_len, p_dur)
    errcode = clibsignal.ppick(reltrc, *args)
    if errcode != 0:
        raise Exception("Error in function ppick of mk_mbaer.c")
    # add the sample to the time which is not taken into account
    # pfm has to be decoded from byte to string
    return pptime.value + 1, pfm.value.decode('utf-8')


def arPick(a, b, c, samp_rate, f1, f2, lta_p, sta_p, lta_s, sta_s, m_p, m_s,
           l_p, l_s, s_pick=True):
    """
    Return corresponding picks of the AR picker

    :param a: Z signal of numpy.ndarray float32 point data
    :param b: N signal of numpy.ndarray float32 point data
    :param c: E signal of numpy.ndarray float32 point data
    :param samp_rate: no of samples per second
    :param f1: frequency of lower Bandpass window
    :param f2: frequency of upper Bandpass window
    :param lta_p: length of LTA for parrival in seconds
    :param sta_p: length of STA for parrival in seconds
    :param lta_s: length of LTA for sarrival in seconds
    :param sta_s: length of STA for sarrival in seconds
    :param m_p: number of AR coefficients for parrival
    :param m_s: number of AR coefficients for sarrival
    :param l_p: length of variance window for parrival in seconds
    :param l_s: length of variance window for sarrival in seconds
    :param s_pick: if true pick also S phase, elso only P
    :return: (ptime, stime) parrival and sarrival
    """
    # be nice and adapt type if necessary
    a = np.require(a, 'float32', ['C_CONTIGUOUS'])
    b = np.require(b, 'float32', ['C_CONTIGUOUS'])
    c = np.require(c, 'float32', ['C_CONTIGUOUS'])
    s_pick = C.c_int(s_pick)  # pick S phase also
    ptime = C.c_float()
    stime = C.c_float()
    args = (len(a), samp_rate, f1, f2,
            lta_p, sta_p, lta_s, sta_s, m_p, m_s, C.byref(ptime),
            C.byref(stime), l_p, l_s, s_pick)
    errcode = clibsignal.ar_picker(a, b, c, *args)
    if errcode != 0:
        raise Exception("Error in function ar_picker of arpicker.c")
    return ptime.value, stime.value


def plotTrigger(trace, cft, thr_on, thr_off, show=True):
    """
    Plot characteristic function of trigger along with waveform data and
    trigger On/Off from given thresholds.

    :type trace: :class:`~obspy.core.trace.Trace`
    :param trace: waveform data
    :type cft: :class:`numpy.ndarray`
    :param cft: characteristic function as returned by a trigger in
        :mod:`obspy.signal.trigger`
    :type thr_on: float
    :param thr_on: threshold for switching trigger on
    :type thr_off: float
    :param thr_off: threshold for switching trigger off
    :type show: bool
    :param show: Do not call `plt.show()` at end of routine. That way,
        further modifications can be done to the figure before showing it.
    """
    import matplotlib.pyplot as plt
    df = trace.stats.sampling_rate
    npts = trace.stats.npts
    t = np.arange(npts, dtype='float32') / df
    fig = plt.figure()
    ax1 = fig.add_subplot(211)
    ax1.plot(t, trace.data, 'k')
    ax2 = fig.add_subplot(212, sharex=ax1)
    ax2.plot(t, cft, 'k')
    onOff = np.array(triggerOnset(cft, thr_on, thr_off))
    i, j = ax1.get_ylim()
    try:
        ax1.vlines(onOff[:, 0] / df, i, j, color='r', lw=2, label="Trigger On")
        ax1.vlines(onOff[:, 1] / df, i, j, color='b', lw=2,
                   label="Trigger Off")
        ax1.legend()
    except IndexError:
        pass
    ax2.axhline(thr_on, color='red', lw=1, ls='--')
    ax2.axhline(thr_off, color='blue', lw=1, ls='--')
    ax2.set_xlabel("Time after %s [s]" % trace.stats.starttime.isoformat())
    fig.suptitle(trace.id)
    fig.canvas.draw()
    if show:
        plt.show()


if __name__ == '__main__':
    import doctest
    doctest.testmod(exclude_empty=True)
