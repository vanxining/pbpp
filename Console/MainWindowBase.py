# -*- coding: utf-8 -*-

###########################################################################
## Python code generated with wxFormBuilder(version Apr 28 2015)
## http://www.wxformbuilder.org/
##
## PLEASE DO u"NOT" EDIT THIS FILE!
###########################################################################

import wx

###########################################################################
## Class MainWindowBase
###########################################################################

class MainWindowBase(wx.Frame):

    def __init__(self, parent):
        wx.Frame.__init__(self, parent, id = wx.ID_ANY, title = u"绑定控制台", pos = wx.DefaultPosition, size = wx.Size(-1,-1), style = wx.DEFAULT_FRAME_STYLE|wx.FULL_REPAINT_ON_RESIZE|wx.TAB_TRAVERSAL)

        self.SetSizeHints(wx.Size(-1,-1), wx.DefaultSize)
        self.SetFont(wx.Font(9, 70, 90, 90, False, u"Segoe UI"))
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BTNFACE))

        mainSizer = wx.BoxSizer(wx.VERTICAL)

        topSizer = wx.BoxSizer(wx.VERTICAL)

        listSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.list = wx.CheckListBox(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, [], 0)
        listSizer.Add(self.list, 4, wx.ALL|wx.EXPAND, 5)

        listControlSizer = wx.BoxSizer(wx.VERTICAL)

        self.append_file = wx.Button(self, wx.ID_ANY, u"添加(&A)", wx.DefaultPosition, wx.DefaultSize, 0)
        listControlSizer.Add(self.append_file, 0, wx.ALL|wx.EXPAND, 5)

        self.delete_file = wx.Button(self, wx.ID_ANY, u"删除(&D)", wx.DefaultPosition, wx.DefaultSize, 0)
        listControlSizer.Add(self.delete_file, 0, wx.ALL|wx.EXPAND, 5)

        self.reparse = wx.Button(self, wx.ID_ANY, u"重新解析(&P)", wx.DefaultPosition, wx.DefaultSize, 0)
        listControlSizer.Add(self.reparse, 0, wx.ALL, 5)

        self.locate_xml = wx.Button(self, wx.ID_ANY, u"定位 XM&L", wx.DefaultPosition, wx.DefaultSize, 0)
        listControlSizer.Add(self.locate_xml, 0, wx.ALL|wx.EXPAND, 5)


        listSizer.Add(listControlSizer, 0, wx.EXPAND, 5)


        topSizer.Add(listSizer, 1, wx.EXPAND, 5)

        editorSizer = wx.BoxSizer(wx.HORIZONTAL)


        topSizer.Add(editorSizer, 0, wx.EXPAND, 5)


        mainSizer.Add(topSizer, 1, wx.EXPAND, 5)

        self.logger = wx.TextCtrl(self, wx.ID_ANY, u"", wx.DefaultPosition, wx.DefaultSize, wx.TE_MULTILINE|wx.TE_READONLY)
        mainSizer.Add(self.logger, 1, wx.ALL|wx.EXPAND, 5)

        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)

        miscSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.reparse_all = wx.Button(self, wx.ID_ANY, u"重新解析所有头文件(&R)", wx.DefaultPosition, wx.DefaultSize, 0)
        miscSizer.Add(self.reparse_all, 0, wx.ALL, 5)

        self.save_as_stable = wx.Button(self, wx.ID_ANY, u"保存为稳定快照(&B)", wx.DefaultPosition, wx.DefaultSize, 0)
        miscSizer.Add(self.save_as_stable, 0, wx.ALL, 5)

        self.restore_from_stable = wx.Button(self, wx.ID_ANY, u"恢复为稳定快照(&T)", wx.DefaultPosition, wx.DefaultSize, 0)
        miscSizer.Add(self.restore_from_stable, 0, wx.ALL, 5)


        bottomSizer.Add(miscSizer, 1, wx.EXPAND, 5)

        btnSizer = wx.BoxSizer(wx.HORIZONTAL)

        self.gccxml = wx.Button(self, wx.ID_ANY, u"&GCC_XML", wx.DefaultPosition, wx.DefaultSize, 0)
        btnSizer.Add(self.gccxml, 0, wx.ALL, 5)

        self.start = wx.Button(self, wx.ID_ANY, u"开始处理(&S)", wx.DefaultPosition, wx.DefaultSize, 0)
        self.start.SetToolTip(u"开始分析列表中所有新加入但尚未解析过的头文件。\n若当前快照文件比稳定快照文件要新，那么当前快照会被替换为稳定的版本。")

        btnSizer.Add(self.start, 0, wx.ALL, 5)


        bottomSizer.Add(btnSizer, 0, wx.EXPAND, 5)


        mainSizer.Add(bottomSizer, 0, wx.EXPAND, 5)


        self.SetSizer(mainSizer)
        self.Layout()
        mainSizer.Fit(self)
        self.status = self.CreateStatusBar(1, wx.ST_SIZEGRIP, wx.ID_ANY)
        self.menu_bar = wx.MenuBar(0)
        self.file_menu = wx.Menu()
        self.open_mi = wx.MenuItem(self.file_menu, wx.ID_ANY, u"打开(&O)...", u"", wx.ITEM_NORMAL)
        self.file_menu.Append(self.open_mi)

        self.save_mi = wx.MenuItem(self.file_menu, wx.ID_ANY, u"保存(&S)", u"", wx.ITEM_NORMAL)
        self.file_menu.Append(self.save_mi)

        self.save_as_mi = wx.MenuItem(self.file_menu, wx.ID_ANY, u"另存为(&A)...", u"", wx.ITEM_NORMAL)
        self.file_menu.Append(self.save_as_mi)

        self.file_menu.AppendSeparator()

        self.save_as_stable_mi = wx.MenuItem(self.file_menu, wx.ID_ANY, u"保存为稳定状态(&B)", u"", wx.ITEM_NORMAL)
        self.file_menu.Append(self.save_as_stable_mi)

        self.restore_from_stable_mi = wx.MenuItem(self.file_menu, wx.ID_ANY, u"从稳定状态恢复(&R)", u"", wx.ITEM_NORMAL)
        self.file_menu.Append(self.restore_from_stable_mi)

        self.file_menu.AppendSeparator()

        self.exit_mi = wx.MenuItem(self.file_menu, wx.ID_ANY, u"退出(&E)", u"", wx.ITEM_NORMAL)
        self.file_menu.Append(self.exit_mi)

        self.menu_bar.Append(self.file_menu, u"文件(&F)")

        self.tools_menu = wx.Menu()
        self.stats_mi = wx.MenuItem(self.tools_menu, wx.ID_ANY, u"统计信息(&S)", u"", wx.ITEM_NORMAL)
        self.tools_menu.Append(self.stats_mi)

        self.tools_menu.AppendSeparator()

        self.regenerate_all_xml_mi = wx.MenuItem(self.tools_menu, wx.ID_ANY, u"重新生成所有&XML文件", u"", wx.ITEM_NORMAL)
        self.tools_menu.Append(self.regenerate_all_xml_mi)

        self.reparse_all_mi = wx.MenuItem(self.tools_menu, wx.ID_ANY, u"重新解析所有头文件(&R)", u"", wx.ITEM_NORMAL)
        self.tools_menu.Append(self.reparse_all_mi)

        self.tools_menu.AppendSeparator()

        self.clean_mi = wx.MenuItem(self.tools_menu, wx.ID_ANY, u"清理输出目录(&C)", u"", wx.ITEM_NORMAL)
        self.tools_menu.Append(self.clean_mi)

        self.rewrite_all_mi = wx.MenuItem(self.tools_menu, wx.ID_ANY, u"重新生成所有输出文件(&W)", u"", wx.ITEM_NORMAL)
        self.tools_menu.Append(self.rewrite_all_mi)

        self.menu_bar.Append(self.tools_menu, u"工具(&T)")

        self.help_menu = wx.Menu()
        self.about_mi = wx.MenuItem(self.help_menu, wx.ID_ANY, u"关于(&A)", u"", wx.ITEM_NORMAL)
        self.help_menu.Append(self.about_mi)

        self.menu_bar.Append(self.help_menu, u"帮助(&H)")

        self.SetMenuBar(self.menu_bar)


        self.Centre(wx.BOTH)

        # Connect Events
        wx.PyBind(self, wx.EVT_CLOSE_WINDOW, self.OnClose)
        wx.PyBind(self.append_file, wx.EVT_BUTTON, self.OnAppend)
        wx.PyBind(self.delete_file, wx.EVT_BUTTON, self.OnDel)
        wx.PyBind(self.reparse, wx.EVT_BUTTON, self.OnReparse)
        wx.PyBind(self.locate_xml, wx.EVT_BUTTON, self.OnLocateXml)
        wx.PyBind(self.reparse_all, wx.EVT_BUTTON, self.OnReparseAll)
        wx.PyBind(self.save_as_stable, wx.EVT_BUTTON, self.OnSaveAsStable)
        wx.PyBind(self.restore_from_stable, wx.EVT_BUTTON, self.OnRestoreFromStable)
        wx.PyBind(self.gccxml, wx.EVT_BUTTON, self.OnGCC_XML)
        wx.PyBind(self.start, wx.EVT_BUTTON, self.OnStart)
        wx.PyBind(self, wx.EVT_MENU, self.OnOpen, id = self.open_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnSave, id = self.save_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnSaveAs, id = self.save_as_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnSaveAsStable, id = self.save_as_stable_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnRestoreFromStable, id = self.restore_from_stable_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnExit, id = self.exit_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnStats, id = self.stats_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnGCC_XML_All, id = self.regenerate_all_xml_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnReparseAll, id = self.reparse_all_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnClean, id = self.clean_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnRewriteAll, id = self.rewrite_all_mi.GetId())
        wx.PyBind(self, wx.EVT_MENU, self.OnAbout, id = self.about_mi.GetId())

    def __del__(self):
        pass


    # Virtual event handlers, overide them in your derived class
    def OnClose(self, event):
        event.Skip()

    def OnAppend(self, event):
        event.Skip()

    def OnDel(self, event):
        event.Skip()

    def OnReparse(self, event):
        event.Skip()

    def OnLocateXml(self, event):
        event.Skip()

    def OnReparseAll(self, event):
        event.Skip()

    def OnSaveAsStable(self, event):
        event.Skip()

    def OnRestoreFromStable(self, event):
        event.Skip()

    def OnGCC_XML(self, event):
        event.Skip()

    def OnStart(self, event):
        event.Skip()

    def OnOpen(self, event):
        event.Skip()

    def OnSave(self, event):
        event.Skip()

    def OnSaveAs(self, event):
        event.Skip()



    def OnExit(self, event):
        event.Skip()

    def OnStats(self, event):
        event.Skip()

    def OnGCC_XML_All(self, event):
        event.Skip()


    def OnClean(self, event):
        event.Skip()

    def OnRewriteAll(self, event):
        event.Skip()

    def OnAbout(self, event):
        event.Skip()


