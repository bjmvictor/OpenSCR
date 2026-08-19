cmake_minimum_required(VERSION 3.24)

project(
    OpenSCRNativeRuntime
    VERSION 0.1.0
    LANGUAGES CXX
)

add_executable(
    OpenSCRNativeRuntime
    WIN32
    src/main.cpp
)

target_compile_features(
    OpenSCRNativeRuntime
    PRIVATE
    cxx_std_20
)

target_compile_definitions(
    OpenSCRNativeRuntime
    PRIVATE

    UNICODE
    _UNICODE

    WIN32_LEAN_AND_MEAN
    NOMINMAX
)

if(MSVC)

    target_compile_options(
        OpenSCRNativeRuntime
        PRIVATE

        /W4
        /O2
        /EHsc
    )

    # Runtime C/C++ estático.
    #
    # Evita depender do Visual C++ Redistributable
    # instalado na máquina destino.

    set_property(
        TARGET OpenSCRNativeRuntime
        PROPERTY
        MSVC_RUNTIME_LIBRARY
        "MultiThreaded$<$<CONFIG:Debug>:Debug>"
    )

endif()

target_link_libraries(
    OpenSCRNativeRuntime
    PRIVATE

    d2d1
    dwrite
    windowscodecs
    ole32
    shell32
    user32
    gdi32
    advapi32
)