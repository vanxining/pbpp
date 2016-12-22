import os


castxml_bin = "castxml"
castxml_args = "--castxml-output=1 -w -x c++ -std=c++14 -D__PBPP__"
premake_bin = "premake5"

if os.name == "nt":
    castxml_args += " -fms-compatibility-version=19"
    pyroot = r"C:\Python27"
    make = "mingw32-make"
else:  # posix
    pyroot = ""
    make = "make"
