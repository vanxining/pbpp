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
        targetdir(".")
        targetname(_OPTIONS["targetname"])

        files { "*.cxx", "*.cpp" }

        if os.target() == "windows" then
            targetextension ".pyd"

            defines { "_hypot=hypot" } -- Satisfy MinGW-w64

            includedirs { _OPTIONS["pyroot"] .. "/include" }
            libdirs { _OPTIONS["pyroot"] .. "/libs" }
            links { "python27" }
        end

        if os.target() == "linux" then
            targetprefix ""

            buildoptions { "`pkg-config python-2.7 --cflags`" }
            links { "python2.7" }
        end

        defines { "NDEBUG" }
        optimize "Off"

        buildoptions { "-std=c++11" }
