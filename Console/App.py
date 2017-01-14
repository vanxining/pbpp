# -*- coding: utf-8 -*-

import os
import sys
import traceback


cd = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, cd[:cd.rindex(os.path.sep)])
sys.path = os.environ["PYWX"].split(';') + sys.path


# noinspection PyUnresolvedReferences
import wx


class App(wx.PyApp):
    def __init__(self):
        super(App, self).__init__()

        wx.SetProcessDPIAware()
        self._BootstrapApp()

    # noinspection PyMethodMayBeStatic,PyBroadException
    def OnInit(self):
        try:
            from MainWindow import MainWindow

            win = MainWindow()
            win.Show()
        except:
            traceback.print_exc()
            return False

        return True


app = App()
app.MainLoop()
