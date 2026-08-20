#include <windows.h>
#include <shellapi.h>
#include <numeric>

#include <d2d1.h>
#include <dwrite.h>
#include <wincodec.h>
#include <wrl/client.h>
#include <random>

#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cwctype>
#include <string>
#include <vector>


using Microsoft::WRL::ComPtr;


// ============================================================
// Constants
// ============================================================

constexpr UINT_PTR INPUT_TIMER_ID = 1;
constexpr UINT_PTR FRAME_TIMER_ID = 2;
constexpr UINT_PTR TEXT_TIMER_ID = 3;

constexpr DWORD INPUT_DELAY_MS = 1000;

constexpr int MOUSE_EXIT_THRESHOLD = 15;

constexpr int RESOURCE_CONFIG = 900;
constexpr int RESOURCE_TEXT = 901;
constexpr int RESOURCE_TEXT_CONFIG = 902;
constexpr int RESOURCE_IMAGE_START = 1000;

constexpr std::uint32_t CONFIG_MAGIC = 0x5243534F;
constexpr std::uint32_t CONFIG_VERSION = 3;

struct RuntimeConfig
{
    std::uint32_t magic = CONFIG_MAGIC;
    std::uint32_t version = CONFIG_VERSION;
    std::uint32_t imageCount = 1;
    std::uint32_t displayMs = 8000;
    std::uint32_t transitionMs = 1500;
    std::uint32_t transitionMode = 0;
    std::uint32_t fitMode = 0;
    std::uint32_t orderMode = 0;
    std::uint32_t transitionMask = 0x1F;
    std::uint32_t backgroundColor = 0xFF000000;
};

static_assert(sizeof(RuntimeConfig) == 40);

struct TextConfig
{
    std::uint32_t enabled = 0;
    std::uint32_t fontSize = 32;
    std::uint32_t color = 0xFFFFFFFF;
    std::uint32_t position = 6;
    std::uint32_t marginTop = 50;
    std::uint32_t marginRight = 50;
    std::uint32_t marginBottom = 50;
    std::uint32_t marginLeft = 50;
    std::uint32_t shadowEnabled = 1;
    std::uint32_t shadowColor = 0xFF000000;
    std::int32_t shadowOffsetX = 2;
    std::int32_t shadowOffsetY = 2;
    std::uint32_t shadowOpacity = 180;
};

static_assert(sizeof(TextConfig) == 52);

// ============================================================
// Globals
// ============================================================

RuntimeConfig g_config{};

TextConfig g_textConfig{};

std::wstring g_textTemplate;

ComPtr<ID2D1Factory>
    g_d2dFactory;

ComPtr<ID2D1HwndRenderTarget>
    g_renderTarget;

ComPtr<IWICImagingFactory>
    g_wicFactory;

ComPtr<IDWriteFactory>
    g_writeFactory;

ComPtr<IDWriteTextFormat>
    g_textFormat;

ComPtr<ID2D1SolidColorBrush>
    g_textBrush;

ComPtr<ID2D1SolidColorBrush>
    g_shadowBrush;

std::vector<
    ComPtr<ID2D1Bitmap>
> g_bitmaps;


std::vector<RECT>
    g_monitors;


std::vector<std::size_t>
    g_imageOrder;

std::vector<std::vector<std::size_t>>
    g_monitorImageOrders;

struct MonitorState
{
    std::size_t sequencePosition = 0;
    bool transitioning = false;
    std::uint32_t activeTransitionMode = 0;
    ULONGLONG slideStartedAt = 0;
    ULONGLONG transitionStartedAt = 0;
};

std::vector<MonitorState> g_monitorStates;


POINT g_initialCursor{};

ULONGLONG g_startedAt = 0;

bool g_inputEnabled = false;


int g_virtualX = 0;
int g_virtualY = 0;

int g_virtualWidth = 0;
int g_virtualHeight = 0;


// ============================================================
// Forward declarations
// ============================================================

LRESULT CALLBACK WindowProc(
    HWND,
    UINT,
    WPARAM,
    LPARAM
);


HRESULT CreateDeviceResources(
    HWND
);


HRESULT LoadBitmapFromResource(
    int,
    ComPtr<ID2D1Bitmap>&
);


void LoadAllBitmaps();


void Render(
    HWND
);

void ReleaseDeviceResources();

void BuildImageOrder()
{
    g_imageOrder.resize(
        g_bitmaps.size()
    );


    std::iota(
        g_imageOrder.begin(),
        g_imageOrder.end(),
        0
    );


    // Reverse
    if (
        g_config.orderMode
        ==
        1
    )
    {
        std::reverse(
            g_imageOrder.begin(),
            g_imageOrder.end()
        );
    }


    // Random
    else if (
        g_config.orderMode
        ==
        2
    )
    {
        static std::mt19937 generator(
            static_cast<std::uint32_t>(
                GetTickCount64()
            )
        );


        std::shuffle(
            g_imageOrder.begin(),
            g_imageOrder.end(),
            generator
        );
    }


    g_monitorImageOrders.assign(
        g_monitors.size(),
        g_imageOrder
    );

    if (g_config.orderMode == 2)
    {
        static std::mt19937 generator(
            static_cast<std::uint32_t>(GetTickCount64())
        );
        for (std::vector<std::size_t>& order : g_monitorImageOrders)
        {
            std::shuffle(order.begin(), order.end(), generator);
        }
    }

    g_monitorStates.assign(
        g_monitors.size(),
        MonitorState{}
    );
}


// ============================================================
// Command-line mode
// ============================================================

bool IsMode(
    const std::wstring& argument,
    wchar_t mode
)
{
    if (
        argument.size()
        <
        2
    )
    {
        return false;
    }

    if (
        argument[0] != L'/'
        &&
        argument[0] != L'-'
    )
    {
        return false;
    }

    return (
        std::towlower(
            argument[1]
        )
        ==
        std::towlower(
            mode
        )
    );
}


// ============================================================
// Resource helpers
// ============================================================

bool GetResourceData(
    int resourceId,
    const BYTE*& data,
    DWORD& size
)
{
    HRSRC resource =
        FindResourceW(
            nullptr,

            MAKEINTRESOURCEW(
                resourceId
            ),

            RT_RCDATA
        );


    if (!resource)
    {
        return false;
    }


    size =
        SizeofResource(
            nullptr,
            resource
        );


    if (size == 0)
    {
        return false;
    }


    HGLOBAL handle =
        LoadResource(
            nullptr,
            resource
        );


    if (!handle)
    {
        return false;
    }


    data =
        reinterpret_cast<const BYTE*>(
            LockResource(
                handle
            )
        );


    return (
        data
        !=
        nullptr
    );
}


// ============================================================
// Config resource
// ============================================================

void LoadRuntimeConfig()
{
    const BYTE* data = nullptr;

    DWORD size = 0;


    if (
        !GetResourceData(
            RESOURCE_CONFIG,
            data,
            size
        )
    )
    {
        return;
    }


    if (
        size
        <
        sizeof(RuntimeConfig)
    )
    {
        return;
    }


    RuntimeConfig embedded{};


    CopyMemory(
        &embedded,
        data,
        sizeof(RuntimeConfig)
    );


    if (
        embedded.magic
        !=
        CONFIG_MAGIC
    )
    {
        return;
    }


    if (
        embedded.version
        !=
        CONFIG_VERSION
    )
    {
        return;
    }


    g_config =
        embedded;


    // Segurança contra valores inválidos.

    g_config.imageCount =
        std::clamp(
            g_config.imageCount,
            1u,
            1000u
        );


    g_config.displayMs =
        std::clamp(
            g_config.displayMs,
            500u,
            3600000u
        );


    g_config.transitionMs =
        std::clamp(
            g_config.transitionMs,
            50u,
            60000u
        );

    g_config.orderMode =
    std::clamp(
        g_config.orderMode,
        0u,
        2u
    );

    g_config.transitionMode = std::clamp(
        g_config.transitionMode,
        0u,
        7u
    );

    g_config.transitionMask &= 0x7Fu;
}

// ============================================================
// Text resources
// ============================================================

void LoadTextResources()
{
    // --------------------------------------------------------
    // Text config
    // --------------------------------------------------------

    const BYTE* configData = nullptr;

    DWORD configSize = 0;


    if (
        GetResourceData(
            RESOURCE_TEXT_CONFIG,
            configData,
            configSize
        )
        &&
        configSize
            >=
            sizeof(TextConfig)
    )
    {
        CopyMemory(
            &g_textConfig,
            configData,
            sizeof(TextConfig)
        );


        g_textConfig.fontSize =
            std::clamp(
                g_textConfig.fontSize,
                8u,
                300u
            );


        g_textConfig.position =
            std::clamp(
                g_textConfig.position,
                0u,
                6u
            );


        g_textConfig.marginTop =
            std::clamp(
                g_textConfig.marginTop,
                0u,
                500u
            );

        g_textConfig.marginRight =
            std::clamp(g_textConfig.marginRight, 0u, 500u);

        g_textConfig.marginBottom =
            std::clamp(g_textConfig.marginBottom, 0u, 500u);

        g_textConfig.marginLeft =
            std::clamp(g_textConfig.marginLeft, 0u, 500u);

        g_textConfig.shadowEnabled =
            g_textConfig.shadowEnabled
            ?
            1u
            :
            0u;


        g_textConfig.shadowOpacity =
            std::clamp(
                g_textConfig.shadowOpacity,
                0u,
                255u
            );


        g_textConfig.shadowOffsetX =
            std::clamp(
                g_textConfig.shadowOffsetX,
                -100,
                100
            );


        g_textConfig.shadowOffsetY =
            std::clamp(
                g_textConfig.shadowOffsetY,
                -100,
                100
            );
    }


    // --------------------------------------------------------
    // Text UTF-16
    // --------------------------------------------------------

    const BYTE* textData = nullptr;

    DWORD textSize = 0;


    if (
        !GetResourceData(
            RESOURCE_TEXT,
            textData,
            textSize
        )
    )
    {
        return;
    }


    if (
        textSize == 0
        ||
        textSize % sizeof(wchar_t)
            !=
            0
    )
    {
        return;
    }


    const std::size_t charCount =
        textSize
        /
        sizeof(wchar_t);


    g_textTemplate.resize(
        charCount
    );


    CopyMemory(
        g_textTemplate.data(),
        textData,
        textSize
    );
}

// ============================================================
// Dynamic variables
// ============================================================

std::wstring ReplaceAll(
    std::wstring text,
    const std::wstring& search,
    const std::wstring& replacement
)
{
    if (search.empty())
    {
        return text;
    }

    std::size_t position = 0;

    while (
        (
            position =
                text.find(
                    search,
                    position
                )
        )
        !=
        std::wstring::npos
    )
    {
        text.replace(
            position,
            search.length(),
            replacement
        );

        position +=
            replacement.length();
    }

    return text;
}


std::wstring FormatTwoDigits(
    int value
)
{
    wchar_t buffer[16]{};

    swprintf_s(
        buffer,
        L"%02d",
        value
    );

    return buffer;
}


std::wstring RenderVariables(
    std::wstring text
)
{
    SYSTEMTIME now{};

    GetLocalTime(
        &now
    );


    static const wchar_t*
        weekdays[] =
    {
        L"Domingo",
        L"Segunda-feira",
        L"Terça-feira",
        L"Quarta-feira",
        L"Quinta-feira",
        L"Sexta-feira",
        L"Sábado"
    };


    static const wchar_t*
        months[] =
    {
        L"",
        L"Janeiro",
        L"Fevereiro",
        L"Março",
        L"Abril",
        L"Maio",
        L"Junho",
        L"Julho",
        L"Agosto",
        L"Setembro",
        L"Outubro",
        L"Novembro",
        L"Dezembro"
    };


    const std::wstring day =
        FormatTwoDigits(
            now.wDay
        );

    const std::wstring month =
        FormatTwoDigits(
            now.wMonth
        );

    const std::wstring year =
        std::to_wstring(
            now.wYear
        );

    const std::wstring hour =
        FormatTwoDigits(
            now.wHour
        );

    const std::wstring minute =
        FormatTwoDigits(
            now.wMinute
        );

    const std::wstring second =
        FormatTwoDigits(
            now.wSecond
        );


    const std::wstring date =
        day
        + L"/"
        + month
        + L"/"
        + year;


    const std::wstring time =
        hour
        + L":"
        + minute;


    const std::wstring timeSeconds =
        time
        + L":"
        + second;


    text =
        ReplaceAll(
            text,
            L"{date}",
            date
        );

    text =
        ReplaceAll(
            text,
            L"{time}",
            time
        );

    text =
        ReplaceAll(
            text,
            L"{time_seconds}",
            timeSeconds
        );

    text =
        ReplaceAll(
            text,
            L"{date_time}",
            date + L" " + time
        );

    text =
        ReplaceAll(
            text,
            L"{day}",
            day
        );

    text =
        ReplaceAll(
            text,
            L"{weekday}",
            weekdays[
                now.wDayOfWeek
            ]
        );

    text =
        ReplaceAll(
            text,
            L"{month}",
            month
        );

    text =
        ReplaceAll(
            text,
            L"{month_name}",
            months[
                now.wMonth
            ]
        );

    text =
        ReplaceAll(
            text,
            L"{year}",
            year
        );


    // --------------------------------------------------------
    // Computer name
    // --------------------------------------------------------

    wchar_t computerName[
        MAX_COMPUTERNAME_LENGTH + 1
    ]{};

    DWORD computerSize =
        MAX_COMPUTERNAME_LENGTH + 1;


    if (
        GetComputerNameW(
            computerName,
            &computerSize
        )
    )
    {
        text =
            ReplaceAll(
                text,
                L"{computer}",
                computerName
            );
    }


    // --------------------------------------------------------
    // Windows user
    // --------------------------------------------------------

    wchar_t userName[256]{};

    DWORD userSize = 256;


    if (
        GetUserNameW(
            userName,
            &userSize
        )
    )
    {
        text =
            ReplaceAll(
                text,
                L"{user}",
                userName
            );
    }


    return text;
}

// ============================================================
// DirectWrite
// ============================================================

D2D1_COLOR_F ColorFromArgb(
    std::uint32_t argb
)
{
    const float alpha =
        static_cast<float>(
            (argb >> 24)
            &
            0xFF
        )
        /
        255.0f;


    const float red =
        static_cast<float>(
            (argb >> 16)
            &
            0xFF
        )
        /
        255.0f;


    const float green =
        static_cast<float>(
            (argb >> 8)
            &
            0xFF
        )
        /
        255.0f;


    const float blue =
        static_cast<float>(
            argb
            &
            0xFF
        )
        /
        255.0f;


    return D2D1::ColorF(
        red,
        green,
        blue,
        alpha
    );
}


HRESULT CreateTextResources()
{
    if (
        !g_textConfig.enabled
        ||
        g_textTemplate.empty()
    )
    {
        return S_OK;
    }


    HRESULT hr = S_OK;


    // --------------------------------------------------------
    // DirectWrite factory
    // --------------------------------------------------------

    if (!g_writeFactory)
    {
        hr =
            DWriteCreateFactory(
                DWRITE_FACTORY_TYPE_SHARED,

                __uuidof(
                    IDWriteFactory
                ),

                reinterpret_cast<IUnknown**>(
                    g_writeFactory
                        .GetAddressOf()
                )
            );


        if (FAILED(hr))
        {
            return hr;
        }
    }


    // --------------------------------------------------------
    // Font
    // --------------------------------------------------------

    if (!g_textFormat)
    {
        hr =
            g_writeFactory
            ->CreateTextFormat(

                L"Segoe UI",

                nullptr,

                DWRITE_FONT_WEIGHT_NORMAL,

                DWRITE_FONT_STYLE_NORMAL,

                DWRITE_FONT_STRETCH_NORMAL,

                static_cast<float>(
                    g_textConfig.fontSize
                ),

                L"pt-BR",

                g_textFormat
                    .GetAddressOf()
            );


        if (FAILED(hr))
        {
            return hr;
        }


        g_textFormat
            ->SetWordWrapping(
                DWRITE_WORD_WRAPPING_WRAP
            );
    }


    // --------------------------------------------------------
    // Text color
    // --------------------------------------------------------

    if (!g_textBrush)
    {
        hr =
            g_renderTarget
            ->CreateSolidColorBrush(

                ColorFromArgb(
                    g_textConfig.color
                ),

                g_textBrush
                    .GetAddressOf()
            );


        if (FAILED(hr))
        {
            return hr;
        }
    }


    // --------------------------------------------------------
    // Shadow
    // --------------------------------------------------------

    if (
        g_textConfig.shadowEnabled
        &&
        !g_shadowBrush
    )
    {
        D2D1_COLOR_F shadowColor =
            ColorFromArgb(
                g_textConfig.shadowColor
            );


        shadowColor.a *=
            static_cast<float>(
                g_textConfig.shadowOpacity
            )
            /
            255.0f;


        hr =
            g_renderTarget
            ->CreateSolidColorBrush(
                shadowColor,
                g_shadowBrush.GetAddressOf()
            );


        if (FAILED(hr))
        {
            return hr;
        }
    }


    return S_OK;
}

// ============================================================
// Monitor enumeration
// ============================================================

BOOL CALLBACK MonitorEnumProc(
    HMONITOR,
    HDC,
    LPRECT monitorRect,
    LPARAM
)
{
    if (!monitorRect)
    {
        return TRUE;
    }


    RECT rect =
        *monitorRect;


    // Converte coordenadas do desktop virtual
    // para coordenadas do nosso HWND.

    OffsetRect(
        &rect,
        -g_virtualX,
        -g_virtualY
    );


    g_monitors.push_back(
        rect
    );


    return TRUE;
}


void LoadMonitors()
{
    g_monitors.clear();


    EnumDisplayMonitors(
        nullptr,
        nullptr,
        MonitorEnumProc,
        0
    );


    if (
        g_monitors.empty()
    )
    {
        RECT fallback{
            0,
            0,
            g_virtualWidth,
            g_virtualHeight
        };


        g_monitors.push_back(
            fallback
        );
    }
}


// ============================================================
// Device resources
// ============================================================

HRESULT CreateDeviceResources(
    HWND hwnd
)
{
    HRESULT hr = S_OK;


    if (!g_d2dFactory)
    {
        hr =
            D2D1CreateFactory(
                D2D1_FACTORY_TYPE_SINGLE_THREADED,
                g_d2dFactory.GetAddressOf()
            );


        if (FAILED(hr))
        {
            return hr;
        }
    }


    if (!g_wicFactory)
    {
        hr =
            CoCreateInstance(
                CLSID_WICImagingFactory,
                nullptr,
                CLSCTX_INPROC_SERVER,
                IID_PPV_ARGS(
                    g_wicFactory.GetAddressOf()
                )
            );


        if (FAILED(hr))
        {
            return hr;
        }
    }


    if (!g_renderTarget)
    {
        RECT rect{};


        GetClientRect(
            hwnd,
            &rect
        );


        const D2D1_SIZE_U size =
            D2D1::SizeU(
                rect.right - rect.left,
                rect.bottom - rect.top
            );


        hr =
            g_d2dFactory
            ->CreateHwndRenderTarget(

                D2D1::RenderTargetProperties(),

                D2D1::HwndRenderTargetProperties(
                    hwnd,
                    size
                ),

                g_renderTarget.GetAddressOf()
            );


        if (FAILED(hr))
        {
            return hr;
        }


        LoadAllBitmaps();
        hr =
            CreateTextResources();


        if (FAILED(hr))
        {
            return hr;
        }

    }


    return hr;
}


// ============================================================
// Image decoding
// ============================================================

HRESULT LoadBitmapFromResource(
    int resourceId,
    ComPtr<ID2D1Bitmap>& bitmap
)
{
    const BYTE* data = nullptr;

    DWORD size = 0;


    if (
        !GetResourceData(
            resourceId,
            data,
            size
        )
    )
    {
        return E_FAIL;
    }


    ComPtr<IWICStream> stream;


    HRESULT hr =
        g_wicFactory
        ->CreateStream(
            stream.GetAddressOf()
        );


    if (FAILED(hr))
    {
        return hr;
    }


    hr =
        stream
        ->InitializeFromMemory(
            const_cast<BYTE*>(
                data
            ),
            size
        );


    if (FAILED(hr))
    {
        return hr;
    }


    ComPtr<IWICBitmapDecoder>
        decoder;


    hr =
        g_wicFactory
        ->CreateDecoderFromStream(
            stream.Get(),

            nullptr,

            WICDecodeMetadataCacheOnLoad,

            decoder.GetAddressOf()
        );


    if (FAILED(hr))
    {
        return hr;
    }


    ComPtr<IWICBitmapFrameDecode>
        frame;


    hr =
        decoder
        ->GetFrame(
            0,
            frame.GetAddressOf()
        );


    if (FAILED(hr))
    {
        return hr;
    }


    ComPtr<IWICFormatConverter>
        converter;


    hr =
        g_wicFactory
        ->CreateFormatConverter(
            converter.GetAddressOf()
        );


    if (FAILED(hr))
    {
        return hr;
    }


    hr =
        converter
        ->Initialize(

            frame.Get(),

            GUID_WICPixelFormat32bppPBGRA,

            WICBitmapDitherTypeNone,

            nullptr,

            0.0,

            WICBitmapPaletteTypeMedianCut
        );


    if (FAILED(hr))
    {
        return hr;
    }


    hr =
        g_renderTarget
        ->CreateBitmapFromWicBitmap(

            converter.Get(),

            nullptr,

            bitmap.GetAddressOf()
        );


    return hr;
}

// ============================================================
// Text rendering
// ============================================================

void ConfigureTextAlignment()
{
    switch (
        g_textConfig.position
    )
    {
        case 0:
        case 4:
        {
            g_textFormat
                ->SetTextAlignment(
                    DWRITE_TEXT_ALIGNMENT_LEADING
                );

            break;
        }


        case 1:
        case 3:
        case 5:
        {
            g_textFormat
                ->SetTextAlignment(
                    DWRITE_TEXT_ALIGNMENT_CENTER
                );

            break;
        }


        case 2:
        case 6:
        {
            g_textFormat
                ->SetTextAlignment(
                    DWRITE_TEXT_ALIGNMENT_TRAILING
                );

            break;
        }
    }


    switch (
        g_textConfig.position
    )
    {
        case 0:
        case 1:
        case 2:
        {
            g_textFormat
                ->SetParagraphAlignment(
                    DWRITE_PARAGRAPH_ALIGNMENT_NEAR
                );

            break;
        }


        case 3:
        {
            g_textFormat
                ->SetParagraphAlignment(
                    DWRITE_PARAGRAPH_ALIGNMENT_CENTER
                );

            break;
        }


        case 4:
        case 5:
        case 6:
        {
            g_textFormat
                ->SetParagraphAlignment(
                    DWRITE_PARAGRAPH_ALIGNMENT_FAR
                );

            break;
        }
    }
}


void DrawTextInMonitor(
    const RECT& monitor
)
{
    if (
        !g_textConfig.enabled
        ||
        g_textTemplate.empty()
        ||
        !g_textFormat
        ||
        !g_textBrush
        ||
        (
            g_textConfig.shadowEnabled
            &&
            !g_shadowBrush
        )
    )
    {
        return;
    }


    const std::wstring text =
        RenderVariables(
            g_textTemplate
        );


    if (text.empty())
    {
        return;
    }


    ConfigureTextAlignment();


    const D2D1_RECT_F textRect =
        D2D1::RectF(

            static_cast<float>(
                monitor.left
            )
            + static_cast<float>(g_textConfig.marginLeft),

            static_cast<float>(
                monitor.top
            )
            + static_cast<float>(g_textConfig.marginTop),

            static_cast<float>(
                monitor.right
            )
            - static_cast<float>(g_textConfig.marginRight),

            static_cast<float>(
                monitor.bottom
            )
            - static_cast<float>(g_textConfig.marginBottom)
        );


    auto drawText = [&](ID2D1SolidColorBrush* brush, float offsetX, float offsetY)
    {
        std::wstring plain;
        struct FormatRange
        {
            std::size_t start;
            std::size_t length;
            bool bold;
            bool italic;
            float size;
        };
        std::vector<FormatRange> ranges;
        bool bold = false;
        bool italic = false;
        float size = static_cast<float>(g_textConfig.fontSize);
        std::size_t rangeStart = 0;
        bool rangeBold = bold;
        bool rangeItalic = italic;
        float rangeSize = size;

        auto flush = [&]()
        {
            if (rangeStart < plain.size())
            {
                ranges.push_back({
                    rangeStart,
                    plain.size() - rangeStart,
                    rangeBold,
                    rangeItalic,
                    rangeSize,
                });
            }
            rangeStart = plain.size();
            rangeBold = bold;
            rangeItalic = italic;
            rangeSize = size;
        };

        auto startFormattedRange = [&]()
        {
            rangeStart = plain.size();
            rangeBold = bold;
            rangeItalic = italic;
            rangeSize = size;
        };

        for (std::size_t index = 0; index < text.size();)
        {
            if (text[index] == L'[')
            {
                const std::size_t end = text.find(L']', index);
                if (end != std::wstring::npos)
                {
                    const std::wstring tag = text.substr(index, end - index + 1);
                    bool recognized = true;
                    if (tag == L"[b]") bold = true;
                    else if (tag == L"[/b]") bold = false;
                    else if (tag == L"[i]") italic = true;
                    else if (tag == L"[/i]") italic = false;
                    else if (tag.rfind(L"[size=", 0) == 0 && tag.back() == L']')
                    {
                        try { size = std::stof(tag.substr(6, tag.size() - 7)); }
                        catch (...) { recognized = false; }
                    }
                    else if (tag == L"[/size]") size = static_cast<float>(g_textConfig.fontSize);
                    else recognized = false;
                    if (recognized)
                    {
                        flush();
                        startFormattedRange();
                        index = end + 1;
                        continue;
                    }
                }
            }
            plain.push_back(text[index++]);
        }
        flush();

        ComPtr<IDWriteTextLayout> layout;
        const float width = textRect.right - textRect.left;
        const float height = textRect.bottom - textRect.top;
        if (FAILED(g_writeFactory->CreateTextLayout(
            plain.c_str(), static_cast<UINT32>(plain.size()), g_textFormat.Get(),
            width, height, layout.GetAddressOf())) )
        {
            return;
        }

        for (const FormatRange& range : ranges)
        {
            const DWRITE_TEXT_RANGE textRange{
                static_cast<UINT32>(range.start),
                static_cast<UINT32>(range.length),
            };
            layout->SetFontWeight(
                range.bold ? DWRITE_FONT_WEIGHT_BOLD : DWRITE_FONT_WEIGHT_NORMAL,
                textRange
            );
            layout->SetFontStyle(
                range.italic ? DWRITE_FONT_STYLE_ITALIC : DWRITE_FONT_STYLE_NORMAL,
                textRange
            );
            layout->SetFontSize(range.size, textRange);
        }

        g_renderTarget->DrawTextLayout(
            D2D1::Point2F(textRect.left + offsetX, textRect.top + offsetY),
            layout.Get(),
            brush,
            D2D1_DRAW_TEXT_OPTIONS_CLIP
        );
    };

    if (g_textConfig.shadowEnabled && g_shadowBrush)
    {
        drawText(
            g_shadowBrush.Get(),
            static_cast<float>(g_textConfig.shadowOffsetX),
            static_cast<float>(g_textConfig.shadowOffsetY)
        );
    }
    drawText(g_textBrush.Get(), 0.0f, 0.0f);
}


// ============================================================
// Load images
// ============================================================

void LoadAllBitmaps()
{
    g_bitmaps.clear();


    for (
        std::uint32_t index = 0;
        index < g_config.imageCount;
        ++index
    )
    {
        ComPtr<ID2D1Bitmap>
            bitmap;


        const int resourceId =
            RESOURCE_IMAGE_START
            +
            static_cast<int>(
                index
            );


        const HRESULT hr =
            LoadBitmapFromResource(
                resourceId,
                bitmap
            );


        if (
            SUCCEEDED(hr)
            &&
            bitmap
        )
        {
            g_bitmaps.push_back(
                bitmap
            );
        }
    }


    BuildImageOrder();

    const ULONGLONG now = GetTickCount64();
    for (MonitorState& state : g_monitorStates)
    {
        state = MonitorState{};
        state.slideStartedAt = now;
    }
}

std::size_t ImageIndexForMonitor(
    std::size_t monitorIndex,
    std::size_t offset
)
{
    if (
        g_imageOrder.empty()
    )
    {
        return 0;
    }


    const std::size_t sequencePosition =
        monitorIndex < g_monitorStates.size()
        ? g_monitorStates[monitorIndex].sequencePosition
        : 0;

    const std::vector<std::size_t>& monitorOrder =
        monitorIndex < g_monitorImageOrders.size()
        ? g_monitorImageOrders[monitorIndex]
        : g_imageOrder;

    const std::size_t monitorOffset =
        g_config.orderMode == 2 ? 0 : monitorIndex;

    const std::size_t position =
        (sequencePosition + monitorOffset + offset)
        %
        monitorOrder.size();


    return monitorOrder[
        position
    ];
}


// ============================================================
// Drawing helper
// ============================================================

void DrawBitmapInMonitor(
    ID2D1Bitmap* bitmap,
    const RECT& monitor,
    float opacity,
    float offsetX = 0.0f,
    float offsetY = 0.0f,
    float scaleMultiplier = 1.0f
)
{
    if (
        !bitmap
        ||
        !g_renderTarget
    )
    {
        return;
    }


    const float monitorWidth =
        static_cast<float>(
            monitor.right
            -
            monitor.left
        );


    const float monitorHeight =
        static_cast<float>(
            monitor.bottom
            -
            monitor.top
        );


    const D2D1_SIZE_F imageSize =
        bitmap->GetSize();


    if (
        imageSize.width <= 0
        ||
        imageSize.height <= 0
    )
    {
        return;
    }


    const float scaleX =
        monitorWidth
        /
        imageSize.width;


    const float scaleY =
        monitorHeight
        /
        imageSize.height;


    float scale;


    if (
        g_config.fitMode
        ==
        1
    )
    {
        scale =
            std::min(
                scaleX,
                scaleY
            );
    }
    else
    {
        scale =
            std::max(
                scaleX,
                scaleY
            );
    }


    scale *=
        scaleMultiplier;


    const float width =
        imageSize.width
        *
        scale;


    const float height =
        imageSize.height
        *
        scale;


    const float left =
        static_cast<float>(
            monitor.left
        )
        +
        (
            monitorWidth
            -
            width
        )
        /
        2.0f
        +
        offsetX;


    const float top =
        static_cast<float>(
            monitor.top
        )
        +
        (
            monitorHeight
            -
            height
        )
        /
        2.0f
        +
        offsetY;


    const D2D1_RECT_F destination =
        D2D1::RectF(
            left,
            top,
            left + width,
            top + height
        );


    const D2D1_RECT_F clip =
        D2D1::RectF(
            static_cast<float>(
                monitor.left
            ),

            static_cast<float>(
                monitor.top
            ),

            static_cast<float>(
                monitor.right
            ),

            static_cast<float>(
                monitor.bottom
            )
        );


    g_renderTarget
        ->PushAxisAlignedClip(
            clip,
            D2D1_ANTIALIAS_MODE_ALIASED
        );


    g_renderTarget
        ->DrawBitmap(
            bitmap,
            destination,
            std::clamp(
                opacity,
                0.0f,
                1.0f
            ),
            D2D1_BITMAP_INTERPOLATION_MODE_LINEAR
        );


    g_renderTarget
        ->PopAxisAlignedClip();
}

std::uint32_t ResolveTransitionMode()
{
    if (
        g_config.transitionMode
        !=
        7
    )
    {
        return g_config.transitionMode;
    }


    static std::mt19937 generator(
        static_cast<std::uint32_t>(
            GetTickCount64()
        )
    );


    std::vector<std::uint32_t> available;
    for (std::uint32_t mode = 0; mode < 7; ++mode)
    {
        if (g_config.transitionMask & (1u << mode))
        {
            available.push_back(mode);
        }
    }

    if (available.empty())
    {
        return 6;
    }

    std::uniform_int_distribution<std::size_t> distribution(
        0,
        available.size() - 1
    );

    return available[distribution(generator)];
}


void DrawGradientTransition(
    ID2D1Bitmap* current,
    ID2D1Bitmap* next,
    const RECT& monitor,
    float progress
)
{
    DrawBitmapInMonitor(
        current,
        monitor,
        1.0f
    );


    constexpr int stripCount =
        64;


    const float monitorWidth =
        static_cast<float>(
            monitor.right
            -
            monitor.left
        );


    const float edge =
        progress * 1.2f
        -
        0.1f;


    constexpr float softness =
        0.18f;


    for (
        int index = 0;
        index < stripCount;
        ++index
    )
    {
        const float normalized =
            (
                static_cast<float>(
                    index
                )
                +
                0.5f
            )
            /
            static_cast<float>(
                stripCount
            );


        const float opacity =
            std::clamp(
                (
                    edge
                    -
                    normalized
                    +
                    softness
                )
                /
                softness,
                0.0f,
                1.0f
            );


        if (
            opacity
            <=
            0.0f
        )
        {
            continue;
        }


        const float left =
            static_cast<float>(
                monitor.left
            )
            +
            monitorWidth
            *
            (
                static_cast<float>(
                    index
                )
                /
                stripCount
            );


        const float right =
            static_cast<float>(
                monitor.left
            )
            +
            monitorWidth
            *
            (
                static_cast<float>(
                    index + 1
                )
                /
                stripCount
            );


        const D2D1_RECT_F strip =
            D2D1::RectF(
                left,

                static_cast<float>(
                    monitor.top
                ),

                right,

                static_cast<float>(
                    monitor.bottom
                )
            );


        g_renderTarget
            ->PushAxisAlignedClip(
                strip,
                D2D1_ANTIALIAS_MODE_ALIASED
            );


        DrawBitmapInMonitor(
            next,
            monitor,
            opacity
        );


        g_renderTarget
            ->PopAxisAlignedClip();
    }
}


void DrawTransitionInMonitor(
    const RECT& monitor,
    float progress,
    std::size_t monitorIndex,
    std::uint32_t transitionMode
)
{
    const std::size_t currentIndex =
        ImageIndexForMonitor(
            monitorIndex,
            0
        );


    const std::size_t nextIndex =
        ImageIndexForMonitor(
            monitorIndex,
            1
        );


    ID2D1Bitmap* current =
        g_bitmaps[
            currentIndex
        ].Get();


    ID2D1Bitmap* next =
        g_bitmaps[
            nextIndex
        ].Get();


    const float width =
        static_cast<float>(
            monitor.right
            -
            monitor.left
        );


    switch (transitionMode)
    {
        // Fade
        case 0:
        {
            DrawBitmapInMonitor(
                current,
                monitor,
                1.0f
                -
                progress
            );


            DrawBitmapInMonitor(
                next,
                monitor,
                progress
            );

            break;
        }


        // Slide left
        case 1:
        {
            DrawBitmapInMonitor(
                current,
                monitor,
                1.0f,
                -width
                *
                progress
            );


            DrawBitmapInMonitor(
                next,
                monitor,
                1.0f,
                width
                *
                (
                    1.0f
                    -
                    progress
                )
            );

            break;
        }


        // Slide right
        case 2:
        {
            DrawBitmapInMonitor(
                current,
                monitor,
                1.0f,
                width
                *
                progress
            );


            DrawBitmapInMonitor(
                next,
                monitor,
                1.0f,
                -width
                *
                (
                    1.0f
                    -
                    progress
                )
            );

            break;
        }


        // Zoom
        case 3:
        {
            DrawBitmapInMonitor(
                current,
                monitor,
                1.0f
                -
                (
                    progress
                    *
                    0.35f
                )
            );


            const float scale =
                1.12f
                -
                (
                    progress
                    *
                    0.12f
                );


            DrawBitmapInMonitor(
                next,
                monitor,
                progress,
                0.0f,
                0.0f,
                scale
            );

            break;
        }


        // Gradient
        case 4:
        {
            DrawGradientTransition(
                current,
                next,
                monitor,
                progress
            );

            break;
        }

        // Slide up
        case 5:
        {
            const float height = static_cast<float>(
                monitor.bottom - monitor.top
            );
            DrawBitmapInMonitor(current, monitor, 1.0f, 0.0f, -height * progress);
            DrawBitmapInMonitor(next, monitor, 1.0f, 0.0f, height * (1.0f - progress));
            break;
        }

        // Slide down
        case 6:
        {
            const float height = static_cast<float>(
                monitor.bottom - monitor.top
            );
            DrawBitmapInMonitor(current, monitor, 1.0f, 0.0f, height * progress);
            DrawBitmapInMonitor(next, monitor, 1.0f, 0.0f, -height * (1.0f - progress));
            break;
        }


        default:
        {
            DrawBitmapInMonitor(
                next,
                monitor,
                progress
            );

            break;
        }
    }
}


// ============================================================
// Render
// ============================================================

void Render(
    HWND hwnd
)
{
    if (
        FAILED(
            CreateDeviceResources(
                hwnd
            )
        )
    )
    {
        return;
    }


    g_renderTarget
        ->BeginDraw();


    g_renderTarget
        ->Clear(
            ColorFromArgb(
                g_config.backgroundColor
            )
        );


    if (
        !g_bitmaps.empty()
    )
    {
        for (
            std::size_t monitorIndex = 0;
            monitorIndex < g_monitors.size();
            ++monitorIndex
        )
        {
            const RECT& monitor =
                g_monitors[
                    monitorIndex
                ];


            MonitorState& state = g_monitorStates[monitorIndex];
            float progress = 0.0f;
            if (state.transitioning && g_config.transitionMs > 0)
            {
                progress = std::clamp(
                    static_cast<float>(GetTickCount64() - state.transitionStartedAt)
                    / static_cast<float>(g_config.transitionMs),
                    0.0f,
                    1.0f
                );
            }

            if (!state.transitioning)
            {
                const std::size_t imageIndex =
                    ImageIndexForMonitor(
                        monitorIndex,
                        0
                    );


                DrawBitmapInMonitor(
                    g_bitmaps[
                        imageIndex
                    ].Get(),

                    monitor,

                    1.0f
                );
            }

            else
            {
                DrawTransitionInMonitor(
                    monitor,
                    progress,
                    monitorIndex,
                    state.activeTransitionMode
                );
            }
        }
    }

    // ========================================================
    // Text overlays
    // ========================================================

    if (
        g_textConfig.enabled
        &&
        !g_textTemplate.empty()
    )
    {
        for (
            const RECT& monitor
            :
            g_monitors
        )
        {
            DrawTextInMonitor(
                monitor
            );
        }
    }


    const HRESULT hr =
        g_renderTarget
        ->EndDraw();


    if (
        hr
        ==
        D2DERR_RECREATE_TARGET
    )
    {
        ReleaseDeviceResources();


        InvalidateRect(
            hwnd,
            nullptr,
            FALSE
        );
    }
}


// ============================================================
// Slideshow
// ============================================================

void UpdateSlideshow(
    HWND hwnd
)
{
    if (g_bitmaps.size() <= 1 || g_monitorStates.empty())
    {
        return;
    }

    const ULONGLONG now = GetTickCount64();

    for (MonitorState& state : g_monitorStates)
    {
        if (!state.transitioning)
        {
            if (now - state.slideStartedAt < g_config.displayMs)
            {
                continue;
            }

            state.activeTransitionMode = ResolveTransitionMode();
            if (state.activeTransitionMode == 6)
            {
                state.sequencePosition =
                    (state.sequencePosition + 1) % g_imageOrder.size();
                state.slideStartedAt = now;
                continue;
            }

            state.transitioning = true;
            state.transitionStartedAt = now;
        }
        else if (now - state.transitionStartedAt >= g_config.transitionMs)
        {
            state.sequencePosition =
                (state.sequencePosition + 1) % g_imageOrder.size();
            state.transitioning = false;
            state.slideStartedAt = now;
        }
    }

    InvalidateRect(hwnd, nullptr, FALSE);
}


// ============================================================
// Cleanup
// ============================================================

void ReleaseDeviceResources()
{
    g_bitmaps.clear();


    g_textBrush.Reset();

    g_shadowBrush.Reset();


    g_renderTarget.Reset();
}


// ============================================================
// Window procedure
// ============================================================

LRESULT CALLBACK WindowProc(
    HWND hwnd,
    UINT message,
    WPARAM wParam,
    LPARAM lParam
)
{
    switch (message)
    {
        case WM_CREATE:
        {
            g_startedAt =
                GetTickCount64();


            for (MonitorState& state : g_monitorStates)
            {
                state.slideStartedAt = g_startedAt;
            }


            GetCursorPos(
                &g_initialCursor
            );


            SetTimer(
                hwnd,
                INPUT_TIMER_ID,
                100,
                nullptr
            );


            SetTimer(
                hwnd,
                FRAME_TIMER_ID,
                16,
                nullptr
            );

            SetTimer(
                hwnd,
                TEXT_TIMER_ID,
                250,
                nullptr
            );


            return 0;
        }


        case WM_SETCURSOR:
        {
            SetCursor(
                nullptr
            );


            return TRUE;
        }


        case WM_SIZE:
        {
            if (g_renderTarget)
            {
                const UINT width =
                    LOWORD(
                        lParam
                    );


                const UINT height =
                    HIWORD(
                        lParam
                    );


                if (
                    width > 0
                    &&
                    height > 0
                )
                {
                    g_renderTarget
                        ->Resize(
                            D2D1::SizeU(
                                width,
                                height
                            )
                        );
                }
            }


            return 0;
        }


        case WM_PAINT:
        {
            PAINTSTRUCT paint{};


            BeginPaint(
                hwnd,
                &paint
            );


            Render(
                hwnd
            );


            EndPaint(
                hwnd,
                &paint
            );


            return 0;
        }


        case WM_TIMER:
        {
            // ----------------------------------------------
            // Input
            // ----------------------------------------------

            if (
                wParam
                ==
                INPUT_TIMER_ID
            )
            {
                if (!g_inputEnabled)
                {
                    if (
                        GetTickCount64()
                        -
                        g_startedAt
                        >=
                        INPUT_DELAY_MS
                    )
                    {
                        GetCursorPos(
                            &g_initialCursor
                        );


                        g_inputEnabled =
                            true;
                    }


                    return 0;
                }


                POINT current{};


                GetCursorPos(
                    &current
                );


                const LONG dx =
                    current.x
                    -
                    g_initialCursor.x;


                const LONG dy =
                    current.y
                    -
                    g_initialCursor.y;


                const LONG distanceSquared =
                    (
                        dx * dx
                    )
                    +
                    (
                        dy * dy
                    );


                if (
                    distanceSquared
                    >=
                    (
                        MOUSE_EXIT_THRESHOLD
                        *
                        MOUSE_EXIT_THRESHOLD
                    )
                )
                {
                    DestroyWindow(
                        hwnd
                    );
                }


                return 0;
            }


            // ----------------------------------------------
            // Animation / slideshow
            // ----------------------------------------------

            if (
                wParam
                ==
                FRAME_TIMER_ID
            )
            {
                UpdateSlideshow(
                    hwnd
                );


                return 0;
            }

            if (
                wParam
                ==
                TEXT_TIMER_ID
            )
            {
                if (
                    g_textConfig.enabled
                    &&
                    !g_textTemplate.empty()
                )
                {
                    InvalidateRect(
                        hwnd,
                        nullptr,
                        FALSE
                    );
                }


                return 0;
            }


            break;
        }


        case WM_KEYDOWN:
        case WM_SYSKEYDOWN:
        {
            if (g_inputEnabled)
            {
                DestroyWindow(
                    hwnd
                );
            }


            return 0;
        }


        case WM_LBUTTONDOWN:
        case WM_RBUTTONDOWN:
        case WM_MBUTTONDOWN:
        case WM_XBUTTONDOWN:
        {
            if (g_inputEnabled)
            {
                DestroyWindow(
                    hwnd
                );
            }


            return 0;
        }


        case WM_DESTROY:
        {
            KillTimer(
                hwnd,
                INPUT_TIMER_ID
            );


            KillTimer(
                hwnd,
                FRAME_TIMER_ID
            );

            KillTimer(
                hwnd,
                TEXT_TIMER_ID
            );


            ReleaseDeviceResources();


            PostQuitMessage(
                0
            );


            return 0;
        }
    }


    return DefWindowProcW(
        hwnd,
        message,
        wParam,
        lParam
    );
}


// ============================================================
// Entry point
// ============================================================

int WINAPI wWinMain(
    HINSTANCE instance,
    HINSTANCE,
    PWSTR,
    int
)
{
    // Melhor comportamento com monitores
    // usando escalas DPI diferentes.

    SetProcessDpiAwarenessContext(
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    );


    // --------------------------------------------------------
    // Arguments
    // --------------------------------------------------------

    int argc = 0;


    LPWSTR* argv =
        CommandLineToArgvW(
            GetCommandLineW(),
            &argc
        );


    bool configurationMode =
        false;


    bool previewMode =
        false;


    if (argv)
    {
        for (
            int index = 1;
            index < argc;
            ++index
        )
        {
            const std::wstring argument =
                argv[index];


            if (
                IsMode(
                    argument,
                    L'c'
                )
            )
            {
                configurationMode =
                    true;
            }


            if (
                IsMode(
                    argument,
                    L'p'
                )
            )
            {
                previewMode =
                    true;
            }
        }


        LocalFree(
            argv
        );
    }


    // --------------------------------------------------------
    // /c
    // --------------------------------------------------------

    if (configurationMode)
    {
        MessageBoxW(
            nullptr,

            L"Este protetor de tela foi criado "
            L"com o OpenSCR.\n\n"
            L"Open-source Windows Screensaver Creator",

            L"OpenSCR",

            MB_OK
            |
            MB_ICONINFORMATION
            |
            MB_TOPMOST
            |
            MB_SETFOREGROUND
        );


        return 0;
    }


    // --------------------------------------------------------
    // /p
    // --------------------------------------------------------

    if (previewMode)
    {
        return 0;
    }


    // --------------------------------------------------------
    // Config
    // --------------------------------------------------------

    LoadRuntimeConfig();

    LoadTextResources();


    // --------------------------------------------------------
    // COM
    // --------------------------------------------------------

    const HRESULT comResult =
        CoInitializeEx(
            nullptr,
            COINIT_APARTMENTTHREADED
        );


    if (FAILED(comResult))
    {
        return 1;
    }


    // --------------------------------------------------------
    // Virtual desktop
    // --------------------------------------------------------

    g_virtualX =
        GetSystemMetrics(
            SM_XVIRTUALSCREEN
        );


    g_virtualY =
        GetSystemMetrics(
            SM_YVIRTUALSCREEN
        );


    g_virtualWidth =
        GetSystemMetrics(
            SM_CXVIRTUALSCREEN
        );


    g_virtualHeight =
        GetSystemMetrics(
            SM_CYVIRTUALSCREEN
        );


    LoadMonitors();


    // --------------------------------------------------------
    // Window class
    // --------------------------------------------------------

    constexpr wchar_t CLASS_NAME[] =
        L"OpenSCRNativeRuntimeWindow";


    WNDCLASSW windowClass{};


    windowClass.lpfnWndProc =
        WindowProc;


    windowClass.hInstance =
        instance;


    windowClass.lpszClassName =
        CLASS_NAME;


    windowClass.hCursor =
        nullptr;


    if (
        !RegisterClassW(
            &windowClass
        )
    )
    {
        CoUninitialize();

        return 1;
    }


    // --------------------------------------------------------
    // One window over entire virtual desktop
    // --------------------------------------------------------

    HWND hwnd =
        CreateWindowExW(

            WS_EX_TOPMOST
            |
            WS_EX_TOOLWINDOW,

            CLASS_NAME,

            L"OpenSCR",

            WS_POPUP,

            g_virtualX,
            g_virtualY,

            g_virtualWidth,
            g_virtualHeight,

            nullptr,
            nullptr,

            instance,
            nullptr
        );


    if (!hwnd)
    {
        CoUninitialize();

        return 1;
    }


    SetWindowPos(
        hwnd,

        HWND_TOPMOST,

        g_virtualX,
        g_virtualY,

        g_virtualWidth,
        g_virtualHeight,

        SWP_SHOWWINDOW
    );


    ShowWindow(
        hwnd,
        SW_SHOW
    );


    UpdateWindow(
        hwnd
    );


    SetForegroundWindow(
        hwnd
    );


    // --------------------------------------------------------
    // Message loop
    // --------------------------------------------------------

    MSG message{};


    while (
        GetMessageW(
            &message,
            nullptr,
            0,
            0
        )
        >
        0
    )
    {
        TranslateMessage(
            &message
        );


        DispatchMessageW(
            &message
        );
    }


    CoUninitialize();


    return static_cast<int>(
        message.wParam
    );
}