# -*- coding: utf-8 -*-


import os
import sys
import traceback


cd = os.path.dirname(os.path.realpath(__file__))
sys.path.append(cd[:cd.rindex(os.path.sep)])
sys.path = os.environ["PYWX"].split(';') + sys.path


# noinspection PyUnresolvedReferences
import wx
import MainWindow


class App(wx.PyApp):
    def __init__(self):
        super(App, self).__init__()
        self._BootstrapApp()

    # noinspection PyMethodMayBeStatic,PyBroadException
    def OnInit(self):
        try:
            win = MainWindow.MainWindow(parent=None)
            win.Show()
        except:
            traceback.print_exc()
            return False

        return True


app = App()
app.MainLoop()
