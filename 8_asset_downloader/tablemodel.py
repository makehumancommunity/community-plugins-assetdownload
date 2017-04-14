#!/usr/bin/python
# -*- coding: utf-8 -*-

""" 
**Project Name:**      MakeHuman community assets

**Product Home Page:** http://www.makehumancommunity.org

**Code Home Page:**    https://github.com/makehumancommunity/community-plugins

**Authors:**           Joel Palmius

**Copyright(c):**      Joel Palmius 2016

**Licensing:**         MIT

Abstract
--------

This plugin manages community assets

"""

import gui3d
import mh
import gui
import json
import os
import re
import platform
import calendar
import datetime

from progress import Progress

from core import G

mhapi = gui3d.app.mhapi

if mhapi.utility.isPySideAvailable():
    from PySide import QtGui
    from PySide import QtCore
    from PySide.QtGui import *
else:
    from PyQt4 import QtGui
    from PyQt4 import QtCore
    from PyQt4.QtGui import *


class AssetTableModel(QtCore.QAbstractTableModel):

    def __init__(self, data, headers, parent=None):
        QtCore.QAbstractTableModel.__init__(self,parent)
        self.log = mhapi.utility.getLogChannel("assetdownload", 4, False)

        self.__data=data     # Initial Data
        self.__headers=headers

    def rowCount( self, parent ):
        self.log.debug("rowCount")
        return len(self.__data)

    def columnCount( self , parent ):
        self.log.debug("columnCount")
        return len(self.__headers)

    def data ( self , index , role ):
        if role == QtCore.Qt.DisplayRole:
            row = index.row()
            column = index.column()
            value = self.__data[row][column]
            return QtCore.QString(value)

    def headerData(self, section, orientation = QtCore.Qt.Horizontal, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and self.__headers is not None:
            if orientation == QtCore.Qt.Horizontal:
                return QtCore.QString(self.__headers[section])
            else:
                return QtCore.QString(str(section + 1))

