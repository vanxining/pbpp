newoption {
    trigger = "targetname",
    description = "The target name of the .pyd output binary."
}

newoption {
    trigger = "pyroot",
    description = "The installation path of Python under Windows."
}

workspace(_OPTIONS["targetname"])
   configurations { "Release", }

    project(_OPTIONS["targetname"])
        kind "SharedLib"
        targetdir(_OPTIONS["targetname"])
        targetname(_OPTIONS["targetname"])

        files { "*.cxx", "*.cpp" }

        if os.get() == "windows" then
            targetextension ".pyd"

            local pyroot = _OPTIONS["pyroot"]

            includedirs { pyroot .. "/include" }
            libdirs { pyroot .. "/libs" }
            links { "python27" }
        end

        if os.get() == "linux" then
            targetprefix ""

            buildoptions { "`pkg-config python-2.7 --cflags`" }
            links { "python2.7" }
        end

        defines { "NDEBUG" }
        optimize "On"

		filter { "action:gmake" }
            buildoptions { "-std=c++11" }
