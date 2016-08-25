# -*- coding: utf-8 -*-

import os
import sys
import xml.etree.ElementTree as ET
import ConfigParser
import importlib
import thread

import Registry
import Session
import Xml

import Modules.RedirectStdStreams
import MainWindowBase

from ProjectBase import make_temp_cpp_header, remove_possible_temp_cpp_header

import wx
import newevent


(ProgressEvent, EVT_PROGRESS) = newevent.NewEvent()
(WorkerFinishEvent, EVT_WORKER_FIN) = newevent.NewEvent()


class Worker:
    def __init__(self, main_window, runnable, done_listener=None):
        self.main_window = main_window
        self.runnable = runnable
        self.done_listener = done_listener

    def Start(self):
        thread.start_new_thread(self.Run, ())

    def Run(self):
        self.runnable()

        evt = WorkerFinishEvent()
        evt.done_listener = self.done_listener
        wx.PostEvent(self.main_window, evt)


class MyRedirector:
    def __init__(self, target):
        self.target = target

    def write(self, msg):
        if not isinstance(msg, unicode):
            msg = msg.decode()

        evt = ProgressEvent(message=msg)
        wx.PostEvent(self.target, evt)

    def flush(self):
        pass


def PrintAndClearIgnoredSymbolsRegistry():
    return
    Session.ignored_fields.clear()  # Too annoying
    Session.print_ignored_symbols_registry()
    Session.clear_ignored_symbols_registry()


class MainWindow(MainWindowBase.MainWindowBase):
    def __init__(self, parent):
        MainWindowBase.MainWindowBase.__init__(self, parent)
        self.SetIcon(wx.Icon(u"Icon.ico", wx.BITMAP_TYPE_ICO))

        usable = wx.GetClientDisplayRect()
        w = int(usable.width * 0.5)
        h = int(usable.height * 0.75)
        self.SetSize(w, h)
        self.Centre(wx.BOTH)

        self.config = ConfigParser.RawConfigParser()
        self.config.read("Settings.ini")
        self.proj_dir = self.config.get("Default", "proj")

        sys.path.append(os.path.abspath(self.proj_dir))
        self.mod_proj = importlib.import_module("Project")

        self.current = self.mod_proj.Project()
        if os.path.exists(self.current_proj()):
            try:
                self.current.load(self.current_proj())
            except:
                print("Current state snapshot file corrupted!")
                raise

        self.process = None
        wx.PyBind(self, wx.EVT_END_PROCESS, self.OnGCC_XML_Done)

        self.batch_gccxml_tasks = []
        self.hanging_header = ""
        self.hanging_xml = ""
        self.redirector = MyRedirector(self)

        self.PrepareList()
        wx.PyBind(self, wx.EVT_CHECKLISTBOX, self.OnEnableHeader, self.list.GetId())

        wx.PyBind(self, EVT_PROGRESS, self.OnProgress)
        wx.PyBind(self, EVT_WORKER_FIN, self.OnWorkerFinished)

        self.timer = wx.Timer(self)
        wx.PyBind(self, wx.EVT_TIMER, self.OnTimer, self.timer.GetId())

    def __del__(self):
        if self.process is not None:
            self.process.Detach()
            self.process.CloseOutput()
            self.process = None

    def current_proj(self):
        return self.proj_dir + "/Current.pbpp"

    def stable_proj(self):
        return self.proj_dir + "/Stable.pbpp"

    def xml_path(self, header_path):
        name = self.current.xml_file_canonical_name(header_path)
        return os.path.realpath("%s/Xml/%s.xml" % (self.proj_dir, name))

    def redirect_header(self, header_path):
        path = header_path

        if self.mod_proj.header_wrappers_dir:
            canonical = os.path.splitext(os.path.split(header_path)[1])[0]
            wrapper = (self.mod_proj.header_wrappers_dir + canonical.upper() +
                       self.mod_proj.header_wrappers_ext)

            if os.path.exists(wrapper):
                path = wrapper

        return make_temp_cpp_header(path)

    def PrepareList(self):
        items = []
        disabled = set()

        for header in open(self.proj_dir + "/Headers.lst"):
            header = header.strip()
            if header:
                if header.startswith("// "):
                    header = header[3:]
                    disabled.add(len(items))

                items.append(header.decode())

        self.list.InsertItems(items, 0)

        for i in range(len(items)):
            if i not in disabled:
                self.list.Check(i, True)

    def Serialize(self):
        with open(self.proj_dir + "/Headers.lst", "w") as outf:
            for i, header in enumerate(self.list.GetStrings()):
                header = header.encode("utf-8")
                if not self.list.IsChecked(i):
                    header = "// " + header

                outf.write(header + "\n")

    def CountEnabled(self):
        cnt = 0
        for _ in self.Enabled():
            cnt += 1

        return cnt

    def Enabled(self):
        for i, header in enumerate(self.list.GetStrings()):
            if self.list.IsChecked(i):
                header = header.encode("utf-8")
                yield header

    def OnTimer(self, event):
        self.status.PopStatusText()

    def MakeToast(self, msg):
        self.status.PushStatusText(msg)
        self.timer.Start(1500, wx.TIMER_ONE_SHOT)

    def OnRestoreFromStable(self, event):
        self.TryRestoreFromStable()
        self.MakeToast(u"Restored")

    def TryRestoreFromStable(self):
        if os.path.exists(self.stable_proj()):
            self.current.load(self.stable_proj())

    def OnExit(self, event):
        self.Close()

    def OnClose(self, event):
        event.Skip(True)

    def OnAbout(self, event):
        wx.MessageBox(u"~~(*∩_∩*)~~", u"About",
                      wx.OK | wx.ICON_INFORMATION,
                      self)

    def OnSaveAs(self, event):
        dlg = wx.FileDialog(self, u"Save as", u"", u"",
                            u"PyBridge++ Project (*.pbpp)|*.pbpp",
                            wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_CANCEL:
            return

        path = dlg.GetPath()
        if not path.endswith(u".pbpp"):
            path += u".pbpp"

        self.current.save(path)

    def OnOpen(self, event):
        dlg = wx.FileDialog(self, u"Open", u"", u"",
                            u"PyBridge++ Project (*.pbpp)|*.pbpp",
                            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_CANCEL:
            return

        self.current.load(dlg.GetPath())

    def SelectFile(self):
        fdlg = wx.FileDialog(self, u"Select header", u"", u"", u"All file types (*.*)|*.*")
        if fdlg.ShowModal() == wx.ID_CANCEL:
            return None

        return fdlg.GetPath()

    def GetSelectedHeader(self):
        if self.list.GetSelection() != wx.NOT_FOUND:
            return self.list.GetStringSelection()
        else:
            return None

    def OnInsert(self, event):
        selected = self.list.GetSelection()
        if selected != wx.NOT_FOUND:
            self.SelectAndInsert(selected)
        else:
            self.OnAppend(event)

    def OnAppend(self, event):
        self.SelectAndInsert(self.list.GetCount())

    def SelectAndInsert(self, pos):
        path = self.SelectFile()
        if path:
            self.list.Insert(path, pos)
            self.list.SetSelection(pos)
            self.list.Check(pos)

            self.Serialize()

    def OnDel(self, event):
        selected = self.list.GetSelection()
        if selected != wx.NOT_FOUND:
            if self.Ask():
                self.list.Delete(selected)
                self.list.SetFocus()

                self.Serialize()

    def InvokeGCC_XML(self, header_path):
        xml_path = self.xml_path(header_path)
        cmd = u'"%s" %s -o "%s" "%s"' % (
            self.mod_proj.gccxml_bin,
            self.mod_proj.gccxml_args(header_path), xml_path,
            self.redirect_header(header_path),
        )

        print(cmd)

        self.hanging_header = header_path
        self.hanging_xml = xml_path

        self.process = wx.Process(self)
        self.process.Redirect()

        wx.Execute(cmd, wx.EXEC_ASYNC, self.process)

    def OnGCC_XML_All(self, event):
        if not self.Ask():
            return

        Xml.clear()

        for header in self.Enabled():
            self.batch_gccxml_tasks.append(header)

        self.DoBatchGCC_XML_Tasks()

        self.logger.Clear()
        self.EnableConsole(False)

    def DoBatchGCC_XML_Tasks(self):
        self.InvokeGCC_XML(self.batch_gccxml_tasks[-1])
        self.batch_gccxml_tasks = self.batch_gccxml_tasks[:-1]

    def OnGCC_XML(self, event):
        path = self.GetSelectedHeader()
        if not path:
            self.logger.SetValue(u"Please select one header first.")
            return

        self.InvokeGCC_XML(path)

        self.logger.Clear()
        self.EnableConsole(False)

    def OnGCC_XML_Done(self, event):
        if self.process.IsInputAvailable():
            self.logger.AppendText(self.process.GetInputStream().Read().decode("utf-8"))  # TODO:

        if self.process.IsErrorAvailable():
            self.logger.AppendText(self.process.GetErrorStream().Read().decode("utf-8"))

        self.process = None

        assert self.hanging_header and self.hanging_xml

        # Eliminate the temporary header
        remove_possible_temp_cpp_header(self.hanging_header)

        if os.path.exists(self.hanging_xml):
            worker = Worker(self, self.DoCompress, self.OnCompressDone)
            worker.Start()
        else:
            self.logger.AppendText(u"Error parsing `%s`.\n" % self.hanging_header)
            self.OnCompressDone()

    def DoCompress(self):
        with Modules.RedirectStdStreams.RedirectStdStreams(self.redirector, self.redirector):
            headers = self.mod_proj.select_headers(self.hanging_header, self.hanging_xml)
            if len(headers) > 0:
                Xml.Compressor(headers, self.hanging_xml, self.hanging_xml)
                print(u"Written to `%s`." % self.hanging_xml)
            else:
                print(u"Error compressing XML output for `%s`: No headers selected." %
                      self.GetSelectedHeader())

    def OnCompressDone(self):
        self.hanging_header = ""
        self.hanging_xml = ""

        if len(self.batch_gccxml_tasks) > 0:
            self.DoBatchGCC_XML_Tasks()
        else:
            self.EnableConsole(True)
            self.Save()  # Save the Xml module cross-session data

            self.logger.AppendText(u"\nDone.")

    def Ask(self):
        answer = wx.MessageBox(u"Are you sure?\nThis may take minutes!",
                               u"Confirm",
                               wx.YES_NO | wx.ICON_WARNING,
                               self)

        return answer == wx.YES

    def OnSaveAsStable(self, event):
        self.current.save(self.stable_proj())
        self.MakeToast(u"Saved as stable")

    def OnClean(self, event):
        folder = self.mod_proj.output_cxx_dir
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            try:
                if os.path.isfile(file_path):
                    if f.endswith(self.mod_proj.output_cxx_ext):
                        os.unlink(file_path)
            except Exception, e:
                print(e)

        self.MakeToast(u"All output files deleted")

    def EnableConsole(self, enabled):
        self.append_file.Enable(enabled)
        self.delete_file.Enable(enabled)
        self.locate_xml.Enable(enabled)
        self.reparse.Enable(enabled)
        self.restore_from_stable.Enable(enabled)
        self.save_as_stable.Enable(enabled)
        self.reparse_all.Enable(enabled)
        self.gccxml.Enable(enabled)
        self.start.Enable(enabled)

        self.open_mi.Enable(enabled)
        self.save_mi.Enable(enabled)
        self.save_as_mi.Enable(enabled)
        self.restore_from_stable_mi.Enable(enabled)
        self.save_as_stable_mi.Enable(enabled)
        self.stats_mi.Enable(enabled)
        self.clean_mi.Enable(enabled)
        self.regenerate_all_xml_mi.Enable(enabled)
        self.reparse_all_mi.Enable(enabled)
        self.rewrite_all_mi.Enable(enabled)

    def Parse(self, header):
        xml_root = ET.parse(self.xml_path(header)).getroot()

        for fnode in xml_root.findall("File"):
            self.current.root_mod.process_file(xml_root, fnode)
            self.current.mark_as_parsed(header)

    def OnReparseAll(self, event):
        if not self.Ask():
            return

        self.logger.Clear()
        self.EnableConsole(False)

        w = Worker(self, self.DoReparseAll)
        w.Start()

    def DoReparseAll(self):
        self.current = self.mod_proj.Project()

        with Modules.RedirectStdStreams.RedirectStdStreams(self.redirector, self.redirector):
            for header in self.Enabled():
                print header
                self.Parse(header)

            self.FinishAndWriteBack()
            self.Save()

            PrintAndClearIgnoredSymbolsRegistry()

    def OnEnableHeader(self, event):
        self.Serialize()

    def OnReparse(self, event):
        if self.list.GetSelection() == wx.NOT_FOUND:
            self.logger.SetValue(u"Please select one header first.\n\n")
            return

        self.EnableConsole(False)
        self.logger.Clear()

        w = Worker(self, self.DoReparse)
        w.Start()

    def DoReparse(self):
        with Modules.RedirectStdStreams.RedirectStdStreams(self.redirector, self.redirector):
            self.current.try_update()
            self.Parse(self.GetSelectedHeader())
            self.FinishAndWriteBack()
            self.Save()

            PrintAndClearIgnoredSymbolsRegistry()

    def OnRewriteAll(self, event):
        self.logger.Clear()
        self.EnableConsole(False)

        w = Worker(self, self.RewriteProxy)
        w.Start()

    def RewriteProxy(self):
        with Modules.RedirectStdStreams.RedirectStdStreams(self.redirector, self.redirector):
            self.current.root_mod.mark_as_dirty()
            self.FinishAndWriteBack()

    def FinishAndWriteBack(self):
        try:
            self.current.root_mod.finish_processing()
            self.Save()
        except RuntimeError, e:
            print(e)
            return

        if not self.logger.IsEmpty():
            print(u"")

        print(u"Writing to disk...")
        self.current.root_mod.generate(
            self.mod_proj.output_cxx_dir, self.mod_proj.output_cxx_ext
        )

        print(u"\nDONE.")

    def OnProgress(self, event):
        self.logger.AppendText(event.message)
        self.logger.SetInsertionPointEnd()

    def OnWorkerFinished(self, event):
        if event.done_listener:
            event.done_listener()
        else:
            self.EnableConsole(True)

    def OnLocateXml(self, event):
        header_path = self.GetSelectedHeader()
        if not header_path:
            self.logger.SetValue(u"Please select one header first.\n\n")
            return

        xml_path = self.xml_path(header_path)

        if os.path.exists(xml_path):
            self.logger.SetValue(xml_path)
        else:
            self.logger.SetValue(u"Not found.")

    def OnStats(self, event):
        for cls in sorted(Registry._registry.values()):
            self.logger.AppendText(cls.full_name + u"\n")

        self.logger.AppendText(u"\n# of classes: %d" % len(Registry._registry))

    def OnSave(self, event):
        self.Save()
        self.MakeToast(u"Saved")

    def Save(self):
        self.current.save(self.current_proj())

    def OnStart(self, event):
        assert self.list.GetCount() > 0

        self.EnableConsole(False)
        self.logger.Clear()

        w = Worker(self, self.DoStart)
        w.Start()

    def DoStart(self):
        with Modules.RedirectStdStreams.RedirectStdStreams(self.redirector, self.redirector):
            if self.CountEnabled() == len(self.current.parsed):
                self.TryRestoreFromStable()

            # No newly added headers -- a rough trick
            if self.CountEnabled() == len(self.current.parsed):
                self.FinishAndWriteBack()
                return

            self.current.try_update()

            for header in self.Enabled():
                if header not in self.current.parsed:
                    self.Parse(header)

            self.FinishAndWriteBack()
            self.Save()  # Save current project

            PrintAndClearIgnoredSymbolsRegistry()
