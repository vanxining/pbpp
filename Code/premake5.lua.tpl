workspace "%(PRJ)s"
    configurations { "Debug", "Release" }

    project "%(PRJ)s"
        kind "SharedLib"
        targetdir "."

        includedirs { "%(LIB)s" }

        headers = { "%(GEN)s/*.hxx" }
        sources = { "%(GEN)s/*.cxx" }

        files { headers, sources }

        if os.get() == "windows" then
            targetextension ".pyd"

            sysdrive = os.getenv("SystemDrive")
            if sysdrive == nil then sysdrive = "C:" end
            pyroot = sysdrive .. "/Python27"

            includedirs { pyroot .. "/include" }
            libdirs { pyroot .. "/libs" }
            links { "python27" }
        end

        if os.get() == "linux" then
            targetprefix ""

            buildoptions { "`pkg-config python-2.7 --cflags`" }
            links { "python2.7" }
        end

        filter "action:gmake"
            buildoptions { "-std=c++14" }

        filter "configurations:Debug"
            targetsuffix "_d"

            defines { "DEBUG", "_DEBUG" }
            symbols "On"

        filter "configurations:Release"
            defines { "NDEBUG" }
            optimize "On"
