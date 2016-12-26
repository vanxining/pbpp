# -*- coding: utf-8 -*-

import ConfigParser
import importlib
import os
import sys
import thread
import traceback
import xml.etree.ElementTree as ET

# noinspection PyUnresolvedReferences
import newevent
# noinspection PyUnresolvedReferences
import wx

import ProjectBase
import Registry
import Session
import Xml


(ProgressEvent, EVT_PROGRESS) = newevent.NewEvent()
(WorkerFinishEvent, EVT_WORKER_FIN) = newevent.NewEvent()


class Worker(object):
    def __init__(self, main_window, runnable, done_listener=None):
        self.main_window = main_window
        self.runnable = runnable
        self.done_listener = done_listener

    def start(self):
        thread.start_new_thread(self.run, ())

    def run(self):
        self.runnable()

        event = WorkerFinishEvent()
        event.done_listener = self.done_listener
        wx.PostEvent(self.main_window, event)


class MyRedirector(object):
    def __init__(self, target):
        self.target = target

    def write(self, msg):
        if not isinstance(msg, unicode):
            msg = msg.decode()

        event = ProgressEvent(message=msg)
        wx.PostEvent(self.target, event)

    def flush(self):
        pass


class RedirectStdStreams(object):
    def __init__(self, stdout=None, stderr=None):
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush(); self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr

    def __exit__(self, exc_type, exc_value, tb):
        self._stdout.flush(); self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


def print_and_clear_ignored_symbols_registry():
    Session.print_ignored_symbols_registry()
    Session.clear_ignored_symbols_registry()


# noinspection PyBroadException,PyUnusedLocal,PyMethodMayBeStatic
class MainWindow(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self)

        if not self.xrc_load_frame():
            raise RuntimeError("Cannot create main window from XRC file")

        self.SetIcon(wx.Icon(u"Icon.ico", wx.BITMAP_TYPE_ICO))

        self.config = ConfigParser.RawConfigParser()
        self.config.read("Settings.ini")
        self.proj_dir = self.config.get("Default", "proj")
        self.print_ignored = self.config.getboolean("Default", "print_ignored")

        if not os.path.isdir(self.proj_dir):
            raise RuntimeError("Not a PyBridge++ project directory: `%s`" % self.proj_dir)

        sys.path.append(os.path.abspath(self.proj_dir))
        self.mod_proj = importlib.import_module("Project")

        self.current = self.mod_proj.Project()
        if os.path.exists(self.current_proj()):
            try:
                self.current.load(self.current_proj())
            except:
                print("Current state snapshot file corrupted")
                raise

        self.process = None
        wx.PyBind(self, wx.EVT_END_PROCESS, self.on_castxml_done)

        self.batch_castxml_tasks = []
        self.hanging_header = ""
        self.hanging_xml = ""
        self.redirector = MyRedirector(self)

        self.DragAcceptFiles(accept=True)
        wx.PyBind(self, wx.EVT_DROP_FILES, self.on_files_dropped)

        self.fill_header_list()
        wx.PyBind(self, wx.EVT_CHECKLISTBOX, self.on_enable_header)

        wx.PyBind(self, EVT_PROGRESS, self.on_progress)
        wx.PyBind(self, EVT_WORKER_FIN, self.on_worker_finished)

        self.timer = wx.Timer(self)
        wx.PyBind(self, wx.EVT_TIMER, self.on_timer, self.timer.GetId())

        wx.PyBind(self, wx.EVT_CLOSE_WINDOW, self.on_close)

    def __del__(self):
        if self.process is not None:
            self.process.Detach()
            self.process.CloseOutput()
            self.process = None

    def xrc_load_frame(self):
        res = wx.XmlResource.Get()
        res.InitAllHandlers()

        if res.Load(u"MainWindow.xrc"):
            if res.LoadFrame(self, None, u"main_window"):
                self.xrc_bind()
                return True

        return False

    def xrc_bind(self):
        res = wx.XmlResource.Get()

        raw = open("MainWindow.xrc").read()
        raw = raw.replace("xmlns", "_xmlns", 1)

        from StringIO import StringIO
        root = ET.parse(StringIO(raw)).getroot()

        for node in root.iter("object"):
            if "name" not in node.attrib:
                continue

            cls = node.attrib["class"]
            name = node.attrib["name"].decode()
            xid = res.GetXRCID(name)

            if cls.startswith("wxMenu"):
                if cls == "wxMenuItem":
                    target = self
                    name = name[:-3]
                else:
                    continue
            else:
                win = self.FindWindow(xid)

                cvt = getattr(wx.XRC, "To_" + cls)
                target = cvt(win)
                setattr(self, name, target)

            event_type = wx.XRC.GetDefaultEventType(cls)
            if event_type != 0:
                handler = getattr(self, "on_" + name, None)
                if handler is not None:
                    wx.PyBind(target, event_type, handler, xid)

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

        return ProjectBase.make_temp_cpp_header(path)

    def fill_header_list(self):
        items = []
        disabled = set()

        for header in open(self.proj_dir + "/Headers.lst"):
            header = header.strip()
            if header:
                if header.startswith("// "):
                    header = header[3:]
                    disabled.add(len(items))

                items.append(header.decode())

        self.header_list.InsertItems(items, 0)

        for i in range(len(items)):
            if i not in disabled:
                self.header_list.Check(i, True)

    def serialize(self):
        with open(self.proj_dir + "/Headers.lst", "w") as outf:
            for i, header in enumerate(self.header_list.GetStrings()):
                header = header.encode("utf-8")
                if not self.header_list.IsChecked(i):
                    header = "// " + header

                outf.write(header + "\n")

    def count_enabled(self):
        cnt = 0
        for _ in self.enabled():
            cnt += 1

        return cnt

    def enabled(self):
        for i, header in enumerate(self.header_list.GetStrings()):
            if self.header_list.IsChecked(i):
                header = header.encode("utf-8")
                yield header

    def on_timer(self, event):
        self.status.PopStatusText()

    def make_toast(self, msg):
        self.status.PushStatusText(msg)
        self.timer.Start(1500, wx.TIMER_ONE_SHOT)

    def on_restore_from_stable(self, event):
        self.try_restore_from_stable()
        self.make_toast(u"Restored")

    def try_restore_from_stable(self):
        if os.path.exists(self.stable_proj()):
            self.current.load(self.stable_proj())

    def on_exit(self, event):
        self.Close()

    def on_close(self, event):
        event.Skip(True)

    def on_about(self, event):
        wx.MessageBox(u"~~(*∩_∩*)~~", u"About",
                      wx.OK | wx.ICON_INFORMATION,
                      self)

    def on_save_as(self, event):
        dlg = wx.FileDialog(self, u"Save as", u"", u"",
                            u"PyBridge++ Project (*.pbpp)|*.pbpp",
                            wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_CANCEL:
            return

        path = dlg.GetPath()
        if not path.endswith(u".pbpp"):
            path += u".pbpp"

        self.current.save(path)

    def on_open(self, event):
        dlg = wx.FileDialog(self, u"Open", u"", u"",
                            u"PyBridge++ Project (*.pbpp)|*.pbpp",
                            wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)

        if dlg.ShowModal() == wx.ID_CANCEL:
            return

        self.current.load(dlg.GetPath())

    def select_file(self):
        fdlg = wx.FileDialog(self, u"Select header", u"", u"", u"All file types (*.*)|*.*")
        if fdlg.ShowModal() == wx.ID_CANCEL:
            return None

        return fdlg.GetPath()

    def get_selected_header(self):
        if self.header_list.GetSelection() != wx.NOT_FOUND:
            return self.header_list.GetStringSelection()
        else:
            return None

    def on_files_dropped(self, event):
        index = self.header_list.GetCount()

        for f in event.GetFiles():
            self.header_list.Append(f)
            self.header_list.Check(index)
            index += 1

        if index > 0:
            self.header_list.SetSelection(index - 1)
            self.serialize()

    def on_append_header(self, event):
        self.select_and_insert(self.header_list.GetCount())

    def select_and_insert(self, pos):
        path = self.select_file()
        if path:
            self.header_list.Insert(path, pos)
            self.header_list.SetSelection(pos)
            self.header_list.Check(pos)

            self.serialize()

    def on_remove_header(self, event):
        selected = self.header_list.GetSelection()
        if selected != wx.NOT_FOUND:
            if self.ask():
                self.header_list.Delete(selected)
                self.header_list.SetFocus()

                self.serialize()

    def on_enable_all_headers(self, event):
        self.do_enable_all_headers(True)

    def on_disable_all_headers(self, event):
        self.do_enable_all_headers(False)

    def do_enable_all_headers(self, enabled):
        if self.header_list.IsEmpty():
            return

        for i in range(self.header_list.GetCount()):
            self.header_list.Check(i, enabled)

        self.serialize()

    def invoke_castxml(self, header_path):
        def is_path(binary):
            return '/' in binary or '\\' in binary

        if is_path(self.mod_proj.castxml_bin):
            if not os.path.exists(self.mod_proj.castxml_bin):
                fmt = u"Path to CastXML not valid:\n    %s\n"
                self.logger.AppendText(fmt % self.mod_proj.castxml_bin)

                return False

        xml_path = self.xml_path(header_path)
        cmd = u'"%s" %s -o "%s" "%s"' % (
            self.mod_proj.castxml_bin,
            self.mod_proj.castxml_args(header_path), xml_path,
            self.redirect_header(header_path),
        )

        print(cmd)

        self.hanging_header = header_path
        self.hanging_xml = xml_path

        self.process = wx.Process(self)
        self.process.Redirect()

        wx.Execute(cmd, wx.EXEC_ASYNC, self.process)

        return True

    def on_castxml_all(self, event):
        if not self.ask():
            return

        for header in self.enabled():
            self.batch_castxml_tasks.append(header)

        if self.do_batch_castxml_tasks():
            self.logger.Clear()
            self.enable_console(False)

    def do_batch_castxml_tasks(self):
        if self.invoke_castxml(self.batch_castxml_tasks[-1]):
            self.batch_castxml_tasks = self.batch_castxml_tasks[:-1]
            return True
        else:
            return False

    def on_castxml(self, event):
        path = self.get_selected_header()
        if not path:
            self.logger.SetValue(u"Please select one header first.")
            return

        if self.invoke_castxml(path):
            self.logger.Clear()
            self.enable_console(False)

    def on_castxml_done(self, event):
        if self.process.IsInputAvailable():
            self.logger.AppendText(self.process.GetInputStream().Read())

        if self.process.IsErrorAvailable():
            self.logger.AppendText(self.process.GetErrorStream().Read())

        self.process = None

        assert self.hanging_header and self.hanging_xml

        # Eliminate the temporary header
        ProjectBase.remove_possible_temp_cpp_header(self.hanging_header)

        if os.path.exists(self.hanging_xml):
            worker = Worker(self, self.on_compress, self.on_compression_done)
            worker.start()
        else:
            self.logger.AppendText(u"Error parsing `%s`.\n" % self.hanging_header)
            self.on_compression_done()

    def on_compress(self):
        with RedirectStdStreams(self.redirector, self.redirector):
            headers = self.mod_proj.select_headers(self.hanging_header, self.hanging_xml)
            if len(headers) > 0:
                c = Xml.Compressor()
                c.compress(headers, self.hanging_xml, self.hanging_xml)

                print(u"Written to `%s`." % self.hanging_xml)
            else:
                print(u"Error compressing XML output for `%s`: No headers selected." %
                      self.get_selected_header())

    def on_compression_done(self):
        self.hanging_header = ""
        self.hanging_xml = ""

        if len(self.batch_castxml_tasks) > 0:
            self.do_batch_castxml_tasks()
        else:
            self.enable_console(True)
            self.save()

            self.logger.AppendText(u"\nDone.")

    def ask(self):
        answer = wx.MessageBox(u"Are you sure?\nThis may take minutes!",
                               u"Confirm",
                               wx.YES_NO | wx.ICON_WARNING,
                               self)

        return answer == wx.YES

    def on_save_as_stable(self, event):
        self.current.save(self.stable_proj())
        self.make_toast(u"Saved as stable")

    def on_clean_output_dir(self, event):
        folder = self.mod_proj.output_cxx_dir
        for f in os.listdir(folder):
            file_path = os.path.join(folder, f)
            try:
                if os.path.isfile(file_path):
                    if f.endswith(self.mod_proj.output_cxx_ext):
                        os.unlink(file_path)
            except:
                traceback.print_exc()

        self.make_toast(u"All output files deleted")

    def enable_console(self, enabled):
        for child in self.GetChildren():
            child.Enable(enabled)

        menu_bar = self.GetMenuBar()
        for i in range(menu_bar.GetMenuCount()):
            menu_bar.EnableTop(i, enabled)

    def parse_header(self, header):
        xml_root = ET.parse(self.xml_path(header)).getroot()

        for fnode in xml_root.findall("File"):
            self.current.root_mod.process_file(xml_root, fnode)
            self.current.mark_as_parsed(header)

    def on_reparse_all_headers(self, event):
        if not self.ask():
            return

        self.logger.Clear()
        self.enable_console(False)

        w = Worker(self, self.do_reparse_all_headers)
        w.start()

    def do_reparse_all_headers(self):
        self.current = self.mod_proj.Project()

        with RedirectStdStreams(self.redirector, self.redirector):
            for header in self.enabled():
                print(header)
                try:
                    self.parse_header(header)
                except:
                    traceback.print_exc()
                    return

            self.finish_and_write_back()
            self.save()

            if self.print_ignored:
                print_and_clear_ignored_symbols_registry()

    def on_enable_header(self, event):
        self.serialize()

    def on_reparse_header(self, event):
        if self.header_list.GetSelection() == wx.NOT_FOUND:
            self.logger.SetValue(u"Please select one header first.\n\n")
            return

        self.enable_console(False)
        self.logger.Clear()

        w = Worker(self, self.do_reparse_header)
        w.start()

    def do_reparse_header(self):
        with RedirectStdStreams(self.redirector, self.redirector):
            self.current.try_update()
            self.parse_header(self.get_selected_header())
            self.finish_and_write_back()
            self.save()

            if self.print_ignored:
                print_and_clear_ignored_symbols_registry()

    def on_rewrite_all_output_files(self, event):
        self.logger.Clear()
        self.enable_console(False)

        w = Worker(self, self.do_rewrite_all_output_files)
        w.start()

    def do_rewrite_all_output_files(self):
        with RedirectStdStreams(self.redirector, self.redirector):
            self.current.root_mod.mark_as_dirty()
            self.finish_and_write_back()

    def finish_and_write_back(self):
        try:
            self.current.root_mod.finish_processing()
            self.save()
        except RuntimeError:
            traceback.print_exc()
            return

        if not self.logger.IsEmpty():
            print(u"")

        print(u"Writing to disk...")
        self.current.root_mod.generate(
            self.mod_proj.output_cxx_dir, self.mod_proj.output_cxx_ext
        )

        print(u"\nDONE.")

    def on_progress(self, event):
        self.logger.AppendText(event.message)
        self.logger.SetInsertionPointEnd()

    def on_worker_finished(self, event):
        if event.done_listener:
            event.done_listener()
        else:
            self.enable_console(True)

    def on_locate_xml(self, event):
        header_path = self.get_selected_header()
        if not header_path:
            self.logger.SetValue(u"Please select one header first.\n\n")
            return

        xml_path = self.xml_path(header_path)

        if os.path.exists(xml_path):
            self.logger.SetValue(xml_path)
        else:
            self.logger.SetValue(u"Not found.")

    # noinspection PyProtectedMember
    def on_stats(self, event):
        for cls in sorted(Registry._registry.values()):
            self.logger.AppendText(cls.full_name + u"\n")

        self.logger.AppendText(u"\n# of classes: %d" % len(Registry._registry))

    def on_save(self, event):
        self.save()
        self.make_toast(u"Saved")

    def save(self):
        self.current.save(self.current_proj())

    def on_start(self, event):
        assert self.header_list.GetCount() > 0

        self.enable_console(False)
        self.logger.Clear()

        w = Worker(self, self.do_start)
        w.start()

    def do_start(self):
        with RedirectStdStreams(self.redirector, self.redirector):
            if self.count_enabled() == len(self.current.parsed):
                self.try_restore_from_stable()

            # No newly added headers -- a rough trick
            if self.count_enabled() == len(self.current.parsed):
                self.finish_and_write_back()
                return

            self.current.try_update()

            for header in self.enabled():
                if header not in self.current.parsed:
                    self.parse_header(header)

            self.finish_and_write_back()
            self.save()  # Save current project

            if self.print_ignored:
                print_and_clear_ignored_symbols_registry()
