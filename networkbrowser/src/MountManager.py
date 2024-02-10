# -*- coding: utf-8 -*-
# for localized messages
from .__init__ import _
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.VirtualKeyBoard import VirtualKeyBoard
from Components.config import ConfigSubsection, configfile, config, getConfigListEntry, ConfigYesNo, ConfigSelection
from Components.ConfigList import ConfigListScreen
from Components.Sources.StaticText import StaticText
from Components.Pixmap import Pixmap
from Components.ActionMap import ActionMap
from Components.Network import iNetwork
from Components.Sources.Boolean import Boolean
from Components.Sources.List import List
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_PLUGINS, SCOPE_GUISKIN, fileExists
from os import path as os_path, fsync

from .MountView import AutoMountView
from .MountEdit import AutoMountEdit
from .AutoMount import iAutoMount, AutoMount
from .UserManager import UserManager


class AutoMountManager(Screen):
	skin = """
		<screen name="AutoMountManager" position="center,center" size="560,400" title="AutoMountManager">
			<ePixmap pixmap="buttons/red.png" position="0,0" size="140,40" alphaTest="on" />
			<widget source="key_red" render="Label" position="0,0" zPosition="1" size="140,40" font="Regular;20" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#9f1313" transparent="1" />
			<widget source="config" render="Listbox" position="5,50" size="540,300" scrollbarMode="showOnDemand" >
				<convert type="TemplatedMultiContent">
					{"template": [
							MultiContentEntryText(pos = (0, 3), size = (480, 25), font=0, flags = RT_HALIGN_LEFT, text = 0), # index 2 is the Menu Titel
							MultiContentEntryText(pos = (10, 29), size = (480, 17), font=1, flags = RT_HALIGN_LEFT, text = 2), # index 3 is the Description
							MultiContentEntryPixmapAlphaTest(pos = (500, 1), size = (48, 48), png = 3), # index 4 is the pixmap
						],
					"fonts": [gFont("Regular", 20),gFont("Regular", 14)],
					"itemHeight": 50
					}
				</convert>
			</widget>
			<ePixmap pixmap="div-h.png" position="0,360" zPosition="1" size="560,2" />
			<widget source="introduction" render="Label" position="10,370" size="540,21" zPosition="10" font="Regular;21" horizontalAlignment="center" verticalAlignment="center" backgroundColor="#25062748" transparent="1"/>
		</screen>"""

	def __init__(self, session, iface, plugin_path):
		self.skin_path = plugin_path
		self.session = session
		self.hostname = None
		self.restartLanRef = None
		Screen.__init__(self, session)
		self.onChangedEntry = []
		self["shortcuts"] = ActionMap(["ShortcutActions", "WizardActions"],
		{
			"ok": self.keyOK,
			"back": self.exit,
			"cancel": self.exit,
			"red": self.exit,
		})
		self["key_red"] = StaticText(_("Close"))
		self["introduction"] = StaticText(_("Press OK to select."))

		self.list = []
		self["config"] = List(self.list)
		self.updateList()
		self.onClose.append(self.cleanup)
		self.onShown.append(self.setWindowTitle)

		if not self.selectionChanged in self["config"].onSelectionChanged:
			self["config"].onSelectionChanged.append(self.selectionChanged)
		self.selectionChanged()

	def createSummary(self):
		from Screens.PluginBrowser import PluginBrowserSummary
		return PluginBrowserSummary

	def selectionChanged(self):
		item = self["config"].getCurrent()
		if item:
			name = str(self["config"].getCurrent()[0])
			desc = str(self["config"].getCurrent()[2])
		else:
			name = ""
			desc = ""
		for cb in self.onChangedEntry:
			cb(name, desc)

	def setWindowTitle(self):
		self.setTitle(_("Mount Manager"))

	def cleanup(self):
		iNetwork.stopRestartConsole()
		iNetwork.stopGetInterfacesConsole()

	def updateList(self):
		self.list = []
		if fileExists(resolveFilename(SCOPE_GUISKIN, "networkbrowser/ok.png")):
			okpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_GUISKIN, "networkbrowser/ok.png"))
		else:
			okpng = LoadPixmap(cached=True, path=resolveFilename(SCOPE_PLUGINS, "SystemPlugins/NetworkBrowser/icons/ok.png"))
		self.list.append((_("Add new network mount point"), "add", _("Add a new NFS or CIFS mount point to your Receiver."), okpng))
		self.list.append((_("Mountpoints management"), "view", _("View, edit or delete mountpoints on your Receiver."), okpng))
		self.list.append((_("User management"), "user", _("View, edit or delete usernames and passwords for your network."), okpng))
		self.list.append((_("Change hostname"), "hostname", _("Change the hostname of your Receiver."), okpng))
		self.list.append((_("Setup Mount Again"), "mountagain", _("Schedule a auto remount of your network shares."), okpng))
		self["config"].setList(self.list)
		if config.usage.sort_settings.value:
			self["config"].list.sort()

	def exit(self):
		self.close()

	def keyOK(self, returnValue=None):
		if returnValue == None:
			returnValue = self["config"].getCurrent()[1]
			if returnValue == "add":
				self.addMount()
			elif returnValue == "view":
				self.viewMounts()
			elif returnValue == "user":
				self.userEdit()
			elif returnValue == "hostname":
				self.hostEdit()
			elif returnValue == "mountagain":
				self.createSetup()

	def addMount(self):
		self.session.open(AutoMountEdit, self.skin_path)

	def viewMounts(self):
		self.session.open(AutoMountView, self.skin_path)

	def userEdit(self):
		self.session.open(UserManager, self.skin_path)

	def hostEdit(self):
		if os_path.exists("/etc/hostname"):
			fp = open('/etc/hostname', 'r')
			self.hostname = fp.readline().rstrip('\n')
			fp.close()
			self.session.openWithCallback(self.hostnameCallback, VirtualKeyBoard, title=(_("Enter new hostname for your Receiver")), text=self.hostname)

	def hostnameCallback(self, callback=None):
		if callback is not None and len(callback):
			fp = open('/etc/hostname', 'w+')
			fp.write(callback + '\n')
			fp.flush()
			fsync(fp.fileno())
			fp.close()
			self.restartLan()

	def restartLan(self):
		iNetwork.restartNetwork(self.restartLanDataAvail)
		self.restartLanRef = self.session.openWithCallback(self.restartfinishedCB, MessageBox, _("Please wait while your network is restarting..."), type=MessageBox.TYPE_INFO, enable_input=False)

	def restartLanDataAvail(self, data):
		if data is True:
			iNetwork.getInterfaces(self.getInterfacesDataAvail)

	def getInterfacesDataAvail(self, data):
		if data is True:
			if self.restartLanRef.execing:
				self.restartLanRef.close(True)

	def restartfinishedCB(self, data):
		if data is True:
			self.session.open(MessageBox, _("Finished restarting your network"), type=MessageBox.TYPE_INFO, timeout=10, default=False)

	def createSetup(self):
		self.session.open(MountManagerMenu)


config.networkbrowser = ConfigSubsection()
config.networkbrowser.automountpoll = ConfigYesNo(default=False)
config.networkbrowser.automountpolltimer = ConfigSelection(default="1", choices=[
	("1", "1"), ("2", "2"), ("3", "3"), ("4", "4"), ("5", "5"), ("6", "6"), ("7", "7"), ("8", "8"), ("9", "9"), ("10", "10"),
	("11", "11"), ("12", "12"), ("13", "13"), ("14", "14"), ("15", "15"), ("16", "16"), ("17", "17"), ("18", "18"), ("19", "19"), ("20", "20"),
	("21", "21"), ("22", "22"), ("23", "23"), ("24", "24")])


class MountManagerMenu(Screen, ConfigListScreen):
	def __init__(self, session):
		from Components.Sources.StaticText import StaticText
		Screen.__init__(self, session)
		self.skinName = "Setup"
		self.setup_title = _("Setup Mount Again")
		self.setTitle(_(self.setup_title))
		self["HelpWindow"] = Pixmap()
		self["HelpWindow"].hide()
		self["VKeyIcon"] = Boolean(False)
		self["footnote"] = StaticText()
		self["description"] = StaticText()

		self["key_red"] = StaticText(_("Cancel"))
		self["key_green"] = StaticText(_("Save"))

		self.onChangedEntry = []
		self.list = []
		ConfigListScreen.__init__(self, self.list, session=self.session, on_change=self.changedEntry)
		self.createSetup()

		self["setupActions"] = ActionMap(["SetupActions", "ColorActions"],
		{
		    "green": self.keySave,
		    "red": self.keyCancel,
		    "cancel": self.keyCancel,
		    "ok": self.keySave,
		}, -2)

	def createSetup(self):
		self.list = []
		self.list.append(getConfigListEntry(_("Schedule MountAgain"), config.networkbrowser.automountpoll))
		if config.networkbrowser.automountpoll.value:
			self.list.append(getConfigListEntry(_("Re-mount network shares every (in hours)"), config.networkbrowser.automountpolltimer))
		self["config"].list = self.list
		self["config"].l.setList(self.list)

	# for summary:
	def changedEntry(self):
		if self["config"].getCurrent()[0] == _("Schedule MountAgain"):
			self.createSetup()
		for x in self.onChangedEntry:
			x()

	def getCurrentEntry(self):
		return self["config"].getCurrent()[0]

	def getCurrentValue(self):
		return str(self["config"].getCurrent()[1].getText())

	def saveAll(self):
		for x in self["config"].list:
			x[1].save()
		configfile.save()

	# keySave and keyCancel are just provided in case you need them.
	# you have to call them by yourself.
	def keySave(self):
		self.saveAll()
		self.close()

	def cancelConfirm(self, result):
		if not result:
			return
		for x in self["config"].list:
			x[1].cancel()
		self.close()

	def keyCancel(self):
		if self["config"].isChanged():
			self.session.openWithCallback(self.cancelConfirm, MessageBox, _("Really close without saving settings?"))
		else:
			self.close()

	def createSummary(self):
		from Screens.Setup import SetupSummary
		return SetupSummary
