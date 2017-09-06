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
import shutil

from progress import Progress

from core import G

from .remoteasset import RemoteAsset
from .downloadtask import DownloadTask

mhapi = gui3d.app.mhapi

class AssetDB():

    def __init__(self, parent):

        self.knownClothesCategories = []
        self.knownAuthors = []

        self.isSynchronized = False
        self.parent = parent
        self.root = mhapi.locations.getUserDataPath("community-assets")
        self.remotecache = os.path.join(self.root,"remotecache")
        self.remotedb = os.path.join(self.root,"remote.json")
        self.localdb = os.path.join(self.root,"local.json")
        self.log = mhapi.utility.getLogChannel("assetdownload")

        self.localJson = None

        self.localAssets = {}

        self._loadRemoteDB()

        if os.path.exists(self.localdb):
            self._loadLocalDB()
        else:
            if self.isSynchronized:
                self._rebuildLocalDB()
                self._loadLocalDB()

    def _loadRemoteDB(self):
        self.log.trace("Enter")

        self.remoteAssets = {}
        for key in mhapi.assets.getAssetTypes():
            if key != "node_setups_and_blender_specific":
                self.remoteAssets[key] = {}

        self.log.debug("Remote json local path", self.remotedb)

        if not os.path.exists(self.remotedb):
            self.log.warn("Remote json does not exist locally")
            return

        with open(self.remotedb,"r") as f:
            if mhapi.utility.isPython3():
                self.remoteJson = json.load(f)
            else:
                self.remoteJson = json.load(f,"UTF-8")

        self.log.spam("remoteJson",self.remoteJson);

        for assetId in self.remoteJson.keys():
            rawAsset = self.remoteJson[assetId]
            asset = RemoteAsset(self,rawAsset)
            assetType = asset.getType()

            self.log.trace("assetId",assetId);
            self.log.trace("assetType", assetType);

            self.log.spam("rawAsset",rawAsset)
            if assetType == "clothes":
                cat = asset.getCategory()
                if cat not in self.knownClothesCategories:
                    self.knownClothesCategories.append(cat)

            self.knownClothesCategories.sort()

            if assetType not in self.remoteAssets and assetType != "node_setups_and_blender_specific":
                self.log.error("Asset type not known:",assetType)
                raise ValueError("Asset type not known: " + assetType)
            else:
                if assetType != "node_setups_and_blender_specific":
                    assetId = asset.getId()
                    self.remoteAssets[assetType][assetId] = asset

        for assetType in self.remoteAssets:
            for assetId in self.remoteAssets[assetType]:
                author = self.remoteAssets[assetType][assetId].getAuthor()
                if author not in self.knownAuthors:
                    self.knownAuthors.append(author)

        self.knownAuthors.sort()

        self.isSynchronized = True

    def _loadLocalDB(self):
        self.log.trace("Enter")

        self.log.debug("About to load local json from", self.localdb)

        if not os.path.exists(self.localdb):
            self.log.warn("Local json does not exist")

            self.localAssets = {}
            for key in mhapi.assets.getAssetTypes():
                self.localAssets[key] = {}

            return

        with open(self.localdb, "r") as f:
            if mhapi.utility.isPython3():
                self.localAssets = json.load(f)
            else:
                self.localAssets = json.load(f, "UTF-8")

        self.log.spam("localAssets",self.localAssets)

    def _rebuildLocalDB(self):
        self.log.trace("Enter")

        self.log.debug("About to rebuild local DB")
        self.localAssets = {}
        for key in mhapi.assets.getAssetTypes():
            if key != "node_setups_and_blender_specific":
                self.localAssets[key] = {}

        for assetType in self.remoteAssets.keys():
            for assetId in self.remoteAssets[assetType].keys():
                asset = self.remoteAssets[assetType][assetId]
                self.log.spam("asset",asset)
                location = asset.getInstallPath()
                self.log.trace("asset location", location)
                if os.path.exists(location):
                    fn = asset.getPertinentFileName()
                    self.log.trace("Pertinent file name", fn)
                    if fn is not None:
                        fn = os.path.join(location,fn)
                        if os.path.exists(fn):
                            self.log.trace("Installed asset location", location)
                            self.localAssets[assetType][assetId] = {}
                            self.localAssets[assetType][assetId]["file"] = fn
                            mod = os.path.getmtime(fn)
                            dt = datetime.datetime.fromtimestamp(mod)
                            self.localAssets[assetType][assetId]["modified"] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            self.log.trace("NOT installed asset", location)
                else:
                    self.log.trace("NOT installed asset", location)

        self.log.spam("Local assets", self.localAssets)

        self._writeLocalDB()

        self.log.debug("Finished rebuilding local DB")

    def _writeLocalDB(self):
        with open(self.localdb,"wt") as f:
            json.dump(self.localAssets, f, indent=2)

    def getFilteredAssets(self, assetType, author=None, subtype=None, hasScreenshot=None, hasThumb=None, isDownloaded=None, title=None, desc=None, changed=None):

        outData = []

        self.log.debug("Requesting filter with limits", { "assetType": assetType, "author": author, "subtype": subtype})

        if assetType in self.remoteAssets:
            allData = self.remoteAssets[assetType]
            for assetId in allData.keys():

                asset = allData[assetId]
                exclude = False

                if assetType == "clothes" and subtype is not None:
                    if subtype != asset.getCategory():
                        exclude = True

                if author is not None:
                    if author != asset.getAuthor():
                        exclude = True

                if title is not None:
                    lt = title.lower()
                    if not lt in asset.getTitle().lower():
                        exclude = True

                if desc is not None:
                    lt = desc.lower()
                    if not lt in asset.getDescription().lower():
                        exclude = True

                if isDownloaded is not None:
                    self.log.trace("isDownloaded",isDownloaded)
                    if isDownloaded == "yes":
                        self.log.trace("assetId",assetId)
                        self.log.trace("assetType",assetType)
                        if str(assetId) not in self.localAssets[assetType]:
                            exclude = True
                    else:
                        if str(assetId) in self.localAssets[assetType]:
                            exclude = True

                if not exclude:
                    outData.append(asset)

        return outData

    def getDownloadTuples(self, ignoreExisting=True, onlyMeta=False, excludeThumb=False, excludeScreenshot=False):
        allData = []
        for assetType in self.remoteAssets.keys():
            for assetId in self.remoteAssets[assetType].keys():
                asset = self.remoteAssets[assetType][assetId]
                tuples = asset.getDownloadTuples(ignoreExisting, onlyMeta, excludeThumb, excludeScreenshot)
                allData.extend(tuples)

        return allData

    def getKnownAuthors(self):
        return list(self.knownAuthors)

    def getKnownClothesCategories(self):
        return list(self.knownClothesCategories)

    def synchronizeRemote(self, parentWidget, onFinished=None, onProgress=None, downloadScreenshots=True, downloadThumbnails=True):
        self.log.trace("Enter")
        filesToDownload = [["http://www.makehumancommunity.org/sites/default/files/assets.json",self.remotedb]]

        self._syncParentWidget = parentWidget
        self._synconFinished = onFinished
        self._synconProgress = onProgress

        self._downloadTask = DownloadTask(parentWidget,filesToDownload,self._syncRemote1Finished,self._syncRemote1Progress)

    def _syncRemote1Progress(self,prog = 0.0):
        self.log.trace("Enter")

    def _syncRemote1Finished(self):
        self.log.trace("Enter")
        self._loadRemoteDB()

        filesToDownload = []

        for assetType in self.remoteAssets.keys():
            for assetId in self.remoteAssets[assetType].keys():
                remoteAsset = self.remoteAssets[assetType][assetId]
                tuples = remoteAsset.getDownloadTuples(ignoreExisting=True,onlyMeta=True,excludeScreenshot=False,excludeThumb=False)
                self.log.spam("Tuples",tuples)

                filesToDownload.extend(tuples)

        self.log.spam("filesToDownload",filesToDownload)
        self._downloadTask = DownloadTask(self._syncParentWidget,filesToDownload,self._syncRemote2Finished,self._syncRemote2Progress)

    def _syncRemote2Progress(self,prog = 0.0):
        self.log.trace("Enter")

    def _syncRemote2Finished(self):
        self.log.trace("Enter")
        self._rebuildLocalDB()
        self._loadLocalDB()

        if self._synconFinished is not None:
            self._synconFinished()

    def downloadItem(self, parentWidget, remoteAsset, onFinished=None, onProgress=None):
        self.log.trace("Enter")

        filesToDownload = remoteAsset.getDownloadTuples(ignoreExisting=False,onlyMeta=False,excludeScreenshot=True,excludeThumb=False)

        self._downloadAsset = remoteAsset
        self._downloadParentWidget = parentWidget
        self._downloadonFinished = onFinished
        self._downloadonProgress = onProgress

        self.log.spam("filesToDownload",filesToDownload)

        self._downloadTask = DownloadTask(parentWidget, filesToDownload, self._downloadFinished, self._downloadProgress)

    def _downloadFinished(self):

        remoteAsset = self._downloadAsset

        fn = remoteAsset.getPertinentFileName()
        srcThumb = remoteAsset.getThumbPath()

        bn = os.path.basename(fn)
        dn = remoteAsset.getInstallPath()

        (name,ext) = os.path.splitext(bn)

        self.log.debug("srcThumb",srcThumb)
        self.log.debug("destThumb", os.path.join(dn,name + ".thumb"))

        destThumb = os.path.join(dn,name + ".thumb")
        shutil.copyfile(srcThumb,destThumb)

        assetType = remoteAsset.getType()
        assetId = remoteAsset.getId()

        file = os.path.join(dn,fn)

        self.log.debug("Downloaded file should be",file)
        self.log.debug("assetId",assetId)

        mod = os.path.getmtime(file)
        dt = datetime.datetime.fromtimestamp(mod)
        modified = dt.strftime('%Y-%m-%d %H:%M:%S')

        self.localAssets[assetType][assetId] = { "file": file, "modified": modified }

        self._writeLocalDB()

        if self._downloadonFinished is not None:
            self._downloadonFinished()

    def _downloadProgress(self, prog):
        if self._downloadonProgress is not None:
            self._downloadonProgress(prog)
