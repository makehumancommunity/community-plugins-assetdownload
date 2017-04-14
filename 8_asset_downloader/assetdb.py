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

from .remoteasset import RemoteAsset

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
        self.log = mhapi.utility.getLogChannel("assetdownload",4,False)

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

        for assetId in self.remoteJson.keys():
            rawAsset = self.remoteJson[assetId];
            asset = RemoteAsset(self,rawAsset)
            assetType = asset.getType()

            if assetType == "clothes":
                cat = asset.getCategory()
                if cat not in self.knownClothesCategories:
                    self.knownClothesCategories.append(cat)

            self.knownClothesCategories.sort()

            if assetType not in self.remoteAssets:
                self.log.error("Asset type not known:",assetType)
                raise ValueError("Asset type not known: " + assetType)
            else:
                assetId = asset.getId()
                self.remoteAssets[assetType][assetId] = asset

            self.log.trace("downloads",asset.getDownloadTuples())

        for assetType in self.remoteAssets:
            for assetId in self.remoteAssets[assetType]:
                author = self.remoteAssets[assetType][assetId].getAuthor()
                if author not in self.knownAuthors:
                    self.knownAuthors.append(author)

        self.knownAuthors.sort()

        self.isSynchronized = True

    def _loadLocalDB(self):
        self.log.trace("Enter")

        self.log.debug("Local json local path", self.localdb)

        if not os.path.exists(self.localdb):
            self.log.warn("Local json does not exist")

            self.localAssets = {}
            for key in mhapi.assets.getAssetTypes():
                self.localAssets[key] = {}

            return

        with open(self.localdb, "r") as f:
            if mhapi.utility.isPython3():
                self.localdb = json.load(f)
            else:
                self.localdb = json.load(f, "UTF-8")

    def _rebuildLocalDB(self):
        self.log.trace("Enter")

        self.localAssets = {}
        for key in mhapi.assets.getAssetTypes():
            self.localAssets[key] = {}

        for assetType in self.remoteAssets.keys():
            for assetId in self.remoteAssets[assetType].keys():
                asset = self.remoteAssets[assetType][assetId]
                location = asset.getInstallPath()
                self.log.trace("asset location", location)
                if os.path.exists(location):
                    fn = asset.getPertinentFileName()
                    self.log.trace("Pertinent file name", fn)
                    if fn is not None:
                        fn = os.path.join(location,fn)
                        if os.path.exists(fn):
                            self.log.debug("Installed asset", location)
                            self.localAssets[assetType][assetId] = {}
                            self.localAssets[assetType][assetId]["file"] = fn
                            mod = os.path.getmtime(fn)
                            dt = datetime.datetime.fromtimestamp(mod)
                            self.localAssets[assetType][assetId]["modified"] = dt.strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            self.log.trace("NOT installed asset", location)
                else:
                    self.log.trace("NOT installed asset", location)

        self.log.trace("Local assets", self.localAssets)

        self.log.debug("Json",json.dumps(self.localAssets))
        with open(self.localdb,"wt") as f:
            json.dump(self.localAssets, f, indent=2)

    def _downloadRemoteJson(self):
        self.log.trace("Enter")
        pass

    def getFilteredAssets(self, assetType, author=None, subtype=None, hasScreenshot=None, hasThumb=None, isDownloaded=None):

        outData = []

        if assetType in self.remoteAssets:
            allData = self.remoteAssets[assetType]
            for assetId in allData.keys():

                asset = allData[assetId]
                exclude = False

                if author is not None:
                    if author != asset.getAuthor():
                        exclude = True
                
                if not exclude:
                    outData.append(asset)

        return outData

    def getKnownAuthors(self):
        return list(self.knownAuthors)

    def getKnownClothesCategories(self):
        return list(self.knownClothesCategories)

    def synchronizeRemote(self, downloadScreenshots=True, downloadThumbnails=True):
        self.log.trace("Enter")
        filesToDownload = []

    def _synchronizeOneAsset(self, jsonHash, downloadScreenshots=True, downloadThumbnails=True):
        self.log.trace("Enter")
        filesToDownload = []

        assetId = str(jsonHash["nid"])
        assetDir = os.path.join(self.dbpath,assetId)

        if not os.path.exists(assetDir):
            os.makedirs(assetDir)

        if "files" in jsonHash.keys():
            files = jsonHash["files"]
            if "render" in files.keys():
                #fn = os.path.join(assetDir,"screenshot.png")
                fn = self.getScreenshotPath(jsonHash)
                if not os.path.exists(fn):                    
                    #log.debug("Downloading " + files["render"])
                    self.downloadUrl(files["render"],fn)
                else:
                    log.debug("Screenshot already existed")

            if "thumb" in files.keys():
                fn = os.path.join(assetDir,"thumb.png")
                if not os.path.exists(fn):                    
                    log.debug("Downloading " + files["thumb"])
                    self.downloadUrl(files["thumb"],fn)
                else:
                    log.debug("thumb already existed")


