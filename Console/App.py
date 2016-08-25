# -*- coding: utf-8 -*-


import os
import sys


cd = os.path.dirname(os.path.realpath(__file__))
pos = cd.rfind(os.path.sep)
sys.path.append(cd[:pos])
sys.path = [r"D:\Work\pywx\Premake", os.environ["PYWX"],] + sys.path


import wx
import MainWindow


class App(wx.PyApp):
    def __init__(self):
        super(App, self).__init__()
        self._BootstrapApp()

    def OnInit(self):
        try:
            win = MainWindow.MainWindow(parent=None)
            win.Show()
        except Exception as e:
            print("App::OnInit() -- Exception occurred!")
            print(e)

        return True


app = App()
app.MainLoop()
