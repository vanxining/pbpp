# -*- coding: utf-8 -*-

import importlib
import logging
import os
import sys
import thread
import time
import traceback
import xml.etree.ElementTree as ET

# noinspection PyUnresolvedReferences
import newevent
# noinspection PyUnresolvedReferences
import wx

import Logger
import ProjectBase
import Registry
import Session
import Xml

import Settings


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
        self.cached = []

    def write(self, msg):
        if not isinstance(msg, unicode):
            msg = msg.decode()

        if msg:
            self.cached.append(msg)

    def flush(self):
        concated = "".join(self.cached)
        if concated:
            event = ProgressEvent(message=concated)
            wx.PostEvent(self.target, event)

        self.cached = []


def print_and_clear_ignored_symbols_registry():
    Session.print_ignored_symbols_registry()
    Session.clear_ignored_symbols_registry()


# noinspection PyBroadException,PyUnusedLocal,PyMethodMayBeStatic,PyAttributeOutsideInit
class MainWindow(wx.Frame):
    SELECT_ONE_HEADER = u"Please select one header first"
    TIME_CONSUMING = u"This may take minutes!"

    def __init__(self):
        wx.Frame.__init__(self)

        if not self.xrc_load_frame():
            raise RuntimeError("Cannot create main window from XRC file")

        self.SetIcon(wx.Icon(u"Icon.ico", wx.BITMAP_TYPE_ICO))

        if not os.path.isdir(Settings.proj):
            raise RuntimeError("Not a PyBridge++ project directory: `%s`" % Settings.proj)

        sys.path.append(os.path.abspath(Settings.proj))
        self.mod_proj = importlib.import_module("Project")

        self.current = self.mod_proj.Project()
        if os.path.exists(self.current_proj()):
            if not self.current.load(self.current_proj()):
                # Restore
                os.remove(self.current_proj())
                self.current = self.mod_proj.Project()

        self.process = None
        wx.PyBind(self, wx.EVT_END_PROCESS, self.on_castxml_done)

        self.batch_castxml_tasks = []
        self.hanging_header = ""
        self.hanging_xml = ""
        self.redirector = MyRedirector(self)

        self.DragAcceptFiles(accept=True)
        wx.PyBind(self, wx.EVT_DROP_FILES, self.on_files_dropped)

        self.fill_header_list()
        wx.PyBind(self, wx.EVT_LIST_ITEM_CHECKED, self.on_enable_header)
        wx.PyBind(self, wx.EVT_LIST_ITEM_UNCHECKED, self.on_enable_header)

        self.prepare_logger()

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

    def prepare_logger(self):
        self.logger = Logger.ListBoxLogger(self.logger)
        wx.PyBind(self.logger.logger_ctrl, wx.EVT_KEY_DOWN, self.on_logger_key_down)

        logging.basicConfig(level=Settings.logging_level,
                            format="[%(levelname)s] %(message)s",
                            stream=MyRedirector(self))

        if Settings.log_debug:
            file_handler = logging.FileHandler(filename=self.log_file_path(),
                                               mode='w',
                                               delay=True)

            file_handler.setLevel(logging.NOTSET)
            formatter = logging.Formatter(fmt="%(asctime)s [%(levelname)s] %(message)s",
                                          datefmt="%m-%d %H:%M")
            file_handler.setFormatter(formatter)

            logging.getLogger().addHandler(file_handler)

    def current_proj(self):
        return Settings.proj + "/Current.pbpp"

    def stable_proj(self):
        return Settings.proj + "/Stable.pbpp"

    def log_file_path(self):
        return Settings.proj + "/Logs.log"

    def xml_path(self, header_path):
        name = self.current.xml_file_canonical_name(header_path)
        return os.path.realpath("%s/Xml/%s.xml" % (Settings.proj, name))

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
        self.header_list.EnableCheckboxes()

        w = self.header_list.GetSize().GetX()
        w -= wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X, self)
        self.header_list.InsertColumn(0, u"Headers", width=w)

        index = 0
        for header in open(Settings.proj + "/Headers.lst"):
            header = header.strip()
            if header:
                disabled = False
                if header.startswith("// "):
                    header = header[3:]
                    disabled = True

                self.header_list.InsertItem(index, header.decode("utf-8"))
                if not disabled:
                    self.header_list.CheckItem(index, True)

                index += 1

    def serialize(self):
        with open(Settings.proj + "/Headers.lst", "w") as outf:
            for index in range(self.header_list.GetItemCount()):
                header = self.header_list.GetItemText(index).encode("utf-8")
                if not self.header_list.IsItemChecked(index):
                    header = "// " + header

                outf.write(header + "\n")

    def count_enabled(self):
        cnt = 0
        for index in range(self.header_list.GetItemCount()):
            if self.header_list.IsItemChecked(index):
                cnt += 1

        return cnt

    def enabled(self):
        for index in range(self.header_list.GetItemCount()):
            if self.header_list.IsItemChecked(index):
                header = self.header_list.GetItemText(index).encode("utf-8")
                yield header

    def on_timer(self, event):
        self.status.PopStatusText()

    def make_toast(self, msg):
        self.status.PushStatusText(msg)
        self.timer.Start(1500, wx.TIMER_ONE_SHOT)

    def on_restore_from_stable(self, event):
        ret = self.try_restore_from_stable()

        if ret == 1:
            self.make_toast(u"Restored")
        elif ret == 0:
            self.make_toast(u"Failed to restore")
        else:
            self.make_toast(u"No stable state snapshot file found")

    def try_restore_from_stable(self):
        if os.path.exists(self.stable_proj()):
            return 1 if self.current.load(self.stable_proj()) else 0

        return -1

    def on_exit(self, event):
        self.Close()

    def on_close(self, event):
        event.Skip(True)

    def on_about(self, event):
        wx.MessageBox(u"~~(*^_^*)~~", u"About",
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

    def set_selected_header(self, index, selected=True):
        state = wx.LIST_STATE_SELECTED if selected else 0
        self.header_list.SetItemState(index, state, wx.LIST_STATE_SELECTED)

    def get_selected_header_index(self):
        if self.header_list.GetSelectedItemCount() > 0:
            item = self.header_list.GetNextItem(-1, state=wx.LIST_STATE_SELECTED)
            return item
        else:
            return -1

    def get_selected_header(self):
        seleted = self.get_selected_header_index()
        if seleted != -1:
            return self.header_list.GetItemText(seleted)
        else:
            return None

    def is_header_list_empty(self):
        return self.header_list.GetItemCount() == 0

    def on_files_dropped(self, event):
        index = self.header_list.GetItemCount()

        for f in event.GetFiles():
            self.header_list.InsertItem(index, f)
            self.header_list.CheckItem(index, True)
            index += 1

        if index > 0:
            self.set_selected_header(index - 1)
            self.header_list.EnsureVisible(index - 1)

            self.serialize()

    def on_append_header(self, event):
        self.select_and_insert(self.header_list.GetItemCount())

    def select_and_insert(self, pos):
        path = self.select_file()
        if path:
            self.header_list.InsertItem(pos, path)
            self.header_list.CheckItem(pos, True)

            self.set_selected_header(pos)
            self.header_list.EnsureVisible(pos)

            self.serialize()

    def on_remove_header(self, event):
        selected = self.get_selected_header_index()
        if selected != -1:
            if self.ask(u"Delete from header list: `%s`" % self.get_selected_header()):
                self.header_list.DeleteItem(selected)
                self.header_list.SetFocus()

                self.serialize()
        else:
            self.make_toast(self.SELECT_ONE_HEADER)

    def on_enable_all_headers(self, event):
        self.do_enable_all_headers(True)

    def on_disable_all_headers(self, event):
        self.do_enable_all_headers(False)

    def do_enable_all_headers(self, enabled):
        if self.is_header_list_empty():
            return

        for i in range(self.header_list.GetItemCount()):
            self.header_list.CheckItem(i, enabled)

        self.serialize()

    def invoke_castxml(self, header_path):
        def is_path(binary):
            return '/' in binary or '\\' in binary

        if is_path(self.mod_proj.castxml_bin):
            if not os.path.exists(self.mod_proj.castxml_bin):
                fmt = u"Path to CastXML binary not valid:\n    %s\n"
                logging.error(fmt % self.mod_proj.castxml_bin)

                return False

        xml_path = self.xml_path(header_path)
        if os.path.exists(xml_path):
            os.remove(xml_path)

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
        if not self.ask(self.TIME_CONSUMING):
            return

        for header in self.enabled():
            self.batch_castxml_tasks.append(header)

        if self.do_batch_castxml_tasks():
            self.logger.clear()
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
            self.make_toast(self.SELECT_ONE_HEADER)
            return

        if self.invoke_castxml(path):
            self.logger.clear()
            self.enable_console(False)

    def on_castxml_done(self, event):
        if self.process.IsInputAvailable():
            logging.debug(self.process.GetInputStream().Read())

        if self.process.IsErrorAvailable():
            logging.error(self.process.GetErrorStream().Read())

        self.process = None

        assert self.hanging_header and self.hanging_xml

        # Eliminate the temporary header
        ProjectBase.remove_possible_temp_cpp_header(self.hanging_header)

        if os.path.exists(self.hanging_xml):
            worker = Worker(self, self.on_compress, self.on_compression_done)
            worker.start()
        else:
            logging.error(u"Failed to parse `%s`" % self.hanging_header)
            self.on_compression_done()

    def on_compress(self):
        headers = self.mod_proj.select_headers(self.hanging_header, self.hanging_xml)
        if len(headers) > 0:
            c = Xml.Compressor()
            c.compress(headers, self.hanging_xml, self.hanging_xml)

            logging.info(u"Written to `%s`.", self.hanging_xml)
        else:
            fmt = u"Failed to compress XML output for `%s`: No header(s) selected"
            logging.error(fmt, self.get_selected_header())

    def on_compression_done(self):
        self.hanging_header = ""
        self.hanging_xml = ""

        if len(self.batch_castxml_tasks) > 0:
            self.do_batch_castxml_tasks()
        else:
            self.enable_console(True)

    def ask(self, msg):
        answer = wx.MessageBox(u"Are you sure?\n" + msg, u"Confirm",
                               wx.YES_NO | wx.ICON_WARNING,
                               self)

        return answer == wx.YES

    def on_save_as_stable(self, event):
        if self.current.save(self.stable_proj()):
            self.make_toast(u"Saved as stable")
        else:
            self.make_toast(u"Failed to save as stable")

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
        xml_path = self.xml_path(header)
        if not os.path.isfile(xml_path):
            logging.error(u"No XML file found for `%s`", header)
            return

        xml_root = ET.parse(xml_path).getroot()

        for fnode in xml_root.findall("File"):
            self.current.root_mod.process_file(xml_root, fnode)
            self.current.mark_as_parsed(header)

    def on_reparse_all_headers(self, event):
        if not self.ask(self.TIME_CONSUMING):
            return

        self.logger.clear()
        self.enable_console(False)

        w = Worker(self, self.do_reparse_all_headers)
        w.start()

    def do_reparse_all_headers(self):
        self.current = self.mod_proj.Project()
        time_begin = time.time()

        for header in self.enabled():
            logging.info(u"Parsing `%s`...", header)
            try:
                self.parse_header(header)
            except:
                logging.exception(u"Failed to parse `%s`" % header)
                return

        self.finish_and_write_back()

        if Settings.print_ignored:
            print_and_clear_ignored_symbols_registry()

        logging.info(u"")
        logging.info(u"Time elapsed: %gs" % (time.time() - time_begin))

    def on_enable_header(self, event):
        self.serialize()

    def on_reparse_header(self, event):
        if self.get_selected_header_index() == -1:
            self.make_toast(self.SELECT_ONE_HEADER)
            return

        self.enable_console(False)
        self.logger.clear()

        w = Worker(self, self.do_reparse_header)
        w.start()

    def do_reparse_header(self):
        self.current.try_update()
        self.parse_header(self.get_selected_header())
        self.finish_and_write_back()

        if Settings.print_ignored:
            print_and_clear_ignored_symbols_registry()

    def on_rewrite_all_output_files(self, event):
        self.logger.clear()
        self.enable_console(False)

        w = Worker(self, self.do_rewrite_all_output_files)
        w.start()

    def do_rewrite_all_output_files(self):
        self.current.root_mod.mark_as_dirty()
        self.finish_and_write_back()

    def finish_and_write_back(self):
        try:
            self.current.root_mod.finish_processing()
            self.save()
        except RuntimeError:
            traceback.print_exc()
            return

        if not self.logger.is_empty():
            logging.info(u"")

        logging.info(u"Writing to disk...")
        self.current.root_mod.generate(
            self.mod_proj.output_cxx_dir, self.mod_proj.output_cxx_ext
        )

        logging.info(u"DONE.")

    def on_worker_finished(self, event):
        if event.done_listener:
            event.done_listener()
        else:
            self.enable_console(True)

    def on_progress(self, event):
        self.logger.append(event.message)
        self.logger.go_to_end()

    def on_logger_key_down(self, event):
        if event.ControlDown():
            if event.GetKeyCode() == ord('A'):
                self.logger.select_all()
            elif event.GetKeyCode() == ord('C'):
                logs = self.logger.get_selections()
                print(logs)

    def on_locate_xml(self, event):
        header_path = self.get_selected_header()
        if not header_path:
            self.make_toast(self.SELECT_ONE_HEADER)
            return

        xml_path = self.xml_path(header_path)

        if os.path.exists(xml_path):
            self.logger.set(xml_path)
        else:
            self.make_toast(u"XML not found")

    # noinspection PyProtectedMember
    def on_stats(self, event):
        self.logger.clear()

        for cls in sorted(Registry._registry.values()):
            self.logger.append(cls.full_name + u"\n")

        self.logger.append(u"\n# of classes: %d" % len(Registry._registry))
        self.logger.go_to_end()

    def on_open_debug_logs_file(self, event):
        if os.path.isfile(self.log_file_path()):
            wx.LaunchDefaultApplication(self.log_file_path().decode())
        else:
            self.make_toast(u"Debug logs file does not exist")

    def on_save(self, event):
        self.save()
        self.make_toast(u"Saved")

    def save(self):
        self.current.save(self.current_proj())

    def on_start(self, event):
        assert not self.is_header_list_empty()

        self.enable_console(False)
        self.logger.clear()

        w = Worker(self, self.do_start)
        w.start()

    def do_start(self):
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

        if Settings.print_ignored:
            print_and_clear_ignored_symbols_registry()
