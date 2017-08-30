#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      ..

**Product Home Page:** TBD

**Code Home Page:**    TBD

**Authors:**           Joel Palmius

**Copyright(c):**      Joel Palmius 2016

**Licensing:**         MIT

"""

import gui3d
import mh
import socket
import json
import os
import time

from progress import Progress

mhapi = gui3d.app.mhapi

if mhapi.utility.isPySideAvailable():
    from PySide import QtGui
    from PySide import QtCore
    from PySide.QtGui import *
    from PySide.QtCore import *
else:
    from PyQt4 import QtGui
    from PyQt4 import QtCore
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

class DownloadThread(QThread):

    def __init__(self, downloadTuples, parent = None):
        QThread.__init__(self, parent)
        self.log = mhapi.utility.getLogChannel("assetdownload")
        self.exiting = False
        self.downloadTuples = downloadTuples
        self.request = mhapi.utility.getCompatibleUrlFetcher()

    def run(self):
        self.log.trace("Enter")
        self.onProgress(0.0)

        total = len(self.downloadTuples)
        current = 0

        lastReport = time.time()

        for dt in self.downloadTuples:
            remote = dt[0]
            local = dt[1]
            dn = os.path.dirname(local)
            if not os.path.exists(dn):
                os.makedirs(dn)
            current = current + 1
            self.log.trace("About to download", remote)
            self.log.trace("Destination is", local)

            remote = remote.replace(" ", "%20")

            try:
                data = self.request.urlopen(remote).read()
                with open(local,"wb") as f:
                    f.write(data)
                    self.log.debug("Successfully downloaded",remote)
            except:
                self.log.warn("Could not download",remote)

            now = time.time()
            now = now - 0.5
            if now > lastReport:
                lastReport = now
                self.onProgress(float(current) / float(total))

        self.onFinished()
        self.exiting = True

    def onProgress(self, prog = 0.0):
        self.log.trace("Enter")
        self.emit(SIGNAL("onProgress(double)"), prog)

    def onFinished(self):
        self.log.trace("Enter")
        #self.onProgress(1.0)
        self.emit(SIGNAL("onFinished()"))

    def __del__(self):
        self.log.trace("Enter")
        self.exiting = True
        self.log = None
        self.downloadTuples = None
        self.request = None


class DownloadTask():

    def __init__(self, parentWidget, downloadTuples, onFinished=None, onProgress=None):
        self.log = mhapi.utility.getLogChannel("assetdownload")

        self.parentWidget = parentWidget
        self.onFinished = onFinished
        self.onProgress = onProgress

        self.downloadThread = DownloadThread(downloadTuples)

        parentWidget.connect(self.downloadThread, SIGNAL("onProgress(double)"), self._onProgress)
        parentWidget.connect(self.downloadThread, SIGNAL("onFinished()"), self._onFinished)

        self.progress = Progress()

        self.log.debug("About to start downloading")
        self.log.spam("downloadTuples",downloadTuples)

        self.downloadThread.start()

    def _onProgress(self, prog=0.0):
        self.log.trace("_onProgress",prog)
        self.progress(prog,"Downloading files...")

        if self.onProgress is not None:
            self.log.trace("onProgress callback is defined")
            self.onProgress(prog)
        else:
            self.log.trace("onProgress callback is not defined")

    def _onFinished(self):
        self.log.trace("Enter")
        self.progress(1.0)
        self.parentWidget.disconnect(self.downloadThread, SIGNAL("onProgress(double)"), self._onProgress)
        self.parentWidget.disconnect(self.downloadThread, SIGNAL("onFinished()"), self._onFinished)

        if self.onFinished is not None:
            self.log.trace("onFinished callback is defined")
            self.onFinished()
        else:
            self.log.trace("onFinished callback is not defined")

        self.downloadThread = None
