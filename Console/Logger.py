# noinspection PyUnresolvedReferences
import wx


class Logger(object):
    def __init__(self, logger_ctrl):
        self.logger_ctrl = logger_ctrl

    def append(self, msg):
        raise NotImplementedError()

    def set(self, msg):
        self.clear()
        self.append(msg)

    def clear(self):
        raise NotImplementedError()

    def is_empty(self):
        raise NotImplementedError()

    def go_to_end(self):
        raise NotImplementedError()

    def select_all(self):
        raise NotImplementedError()

    def get_selections(self):
        raise NotImplementedError()


# noinspection PyAbstractClass
class TextCtrlLogger(Logger):
    def __init__(self, logger_ctrl):
        Logger.__init__(self, logger_ctrl)

    def append(self, msg):
        self.logger_ctrl.AppendText(msg)

    def set(self, msg):
        self.logger_ctrl.SetValue(msg)

    def clear(self):
        self.logger_ctrl.Clear()

    def is_empty(self):
        return self.logger_ctrl.IsEmpty()

    def go_to_end(self):
        self.logger_ctrl.SetInsertionPointEnd()


# noinspection PyAbstractClass
class ListBoxLogger(Logger):
    def __init__(self, logger_ctrl):
        Logger.__init__(self, logger_ctrl)

    def _count(self):
        return self.logger_ctrl.GetCount()

    def append(self, msg):
        lines = []
        for line in msg.split(u'\n'):
            if line:
                lines.append(line)

        if lines:
            self.logger_ctrl.InsertItems(lines, self._count())

    def clear(self):
        self.logger_ctrl.Clear()

    def is_empty(self):
        return self.logger_ctrl.IsEmpty()

    def go_to_end(self):
        if not self.is_empty():
            self.logger_ctrl.EnsureVisible(self._count() - 1)

    def select_all(self):
        for index in xrange(self._count()):
            self.logger_ctrl.Select(index)

    def get_selections(self):
        selections = []
        self.logger_ctrl.GetSelections(selections)

        logs = ""
        for index in selections:
            logs += self.logger_ctrl.GetString(index) + '\n'

        return logs[:-1] if logs else logs


# noinspection PyAbstractClass
class ListCtrlLogger(Logger):
    def __init__(self, logger_ctrl):
        Logger.__init__(self, logger_ctrl)

        w = self.logger_ctrl.GetSize().GetX()
        w -= wx.SystemSettings.GetMetric(wx.SYS_VSCROLL_X, self.logger_ctrl)
        self.logger_ctrl.InsertColumn(0, u"Logs", width=w)

    def _count(self):
        return self.logger_ctrl.GetItemCount()

    def append(self, msg):
        index = self._count()

        for line in msg.split(u"\n"):
            if line:
                self.logger_ctrl.InsertItem(index, line)
                index += 1

    def clear(self):
        self.logger_ctrl.DeleteAllItems()

    def is_empty(self):
        return self._count() == 0

    def go_to_end(self):
        if not self.is_empty():
            self.logger_ctrl.EnsureVisible(self._count() - 1)

    def select_all(self):
        raise NotImplementedError()

    def get_selections(self):
        selections = []
        item = -1

        while True:
            item = self.logger_ctrl.GetNextItem(
                item=item,
                geometry=wx.LIST_NEXT_ALL,
                state=wx.LIST_STATE_SELECTED,
            )

            if item == -1:
                break

            selections.append(self.logger_ctrl.GetString(item))

        return '\n'.join(selections)


# noinspection PyMethodMayBeStatic
class MyXmlSubclassFactory(wx.XmlSubclassFactory):
    def Create(self, cls):
        if cls == u"MyListCtrl":
            return MyListCtrl()


# noinspection PyMethodMayBeStatic
class MyListCtrl(wx.ListCtrl):
    def __init__(self, *args, **kwargs):
        wx.ListCtrl.__init__(self, *args, **kwargs)
        self.lines = []

    def OnGetItemText(self, item, col):
        return self.lines[item]


# noinspection PyAbstractClass
class MyListCtrlLogger(ListCtrlLogger):
    def __init__(self, logger_ctrl):
        ListCtrlLogger.__init__(self, logger_ctrl)
        self.logger_ctrl.SetItemCount(0)

    def _update(self):
        self.logger_ctrl.SetItemCount(self._count())

    def _count(self):
        return len(self.logger_ctrl.lines)

    def append(self, msg):
        for line in msg.split('\n'):
            if line:
                self.logger_ctrl.lines.append(line)

        self._update()

    def clear(self):
        self.logger_ctrl.lines = []
        self._update()

    def get_selections(self):
        return '\n'.join(self.logger_ctrl.lines)
