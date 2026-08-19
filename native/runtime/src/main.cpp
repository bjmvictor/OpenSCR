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

constexpr std::uint32_t CONFIG_MAGIC =
    0x5243534F;

constexpr std::uint32_t CONFIG_VERSION =
    2;


// ============================================================
// Config
// ============================================================

struct RuntimeConfig
{
    std::uint32_t magic =
        CONFIG_MAGIC;

    std::uint32_t version =
        CONFIG_VERSION;

    std::uint32_t imageCount =
        1;

    std::uint32_t displayMs =
        8000;

    std::uint32_t transitionMs =
        1500;

    std::uint32_t transitionMode =
        0;

    std::uint32_t fitMode =
        0;

    std::uint32_t orderMode =
        0;
};

static_assert(
    sizeof(RuntimeConfig)
    ==
    32
);

// ============================================================
// Text config
// ============================================================

struct TextConfig
{
    std::uint32_t enabled = 0;

    std::uint32_t fontSize = 32;

    std::uint32_t color =
        0xFFFFFFFF;

    std::uint32_t position = 6;

    std::uint32_t margin = 50;


    std::uint32_t shadowEnabled = 1;

    std::uint32_t shadowColor =
        0xFF000000;

    std::int32_t shadowOffsetX = 2;

    std::int32_t shadowOffsetY = 2;

    std::uint32_t shadowOpacity = 180;
};


static_assert(
    sizeof(TextConfig)
    ==
    40
);

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

std::size_t
    g_sequencePosition = 0;

bool g_transitioning = false;

std::uint32_t g_activeTransitionMode = 0;


ULONGLONG g_slideStartedAt = 0;
ULONGLONG g_transitionStartedAt = 0;


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


    g_sequencePosition = 0;
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

    g_config.transitionMode =
    std::clamp(
        g_config.transitionMode,
        0u,
        5u
    );
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


        g_textConfig.margin =
            std::clamp(
                g_textConfig.margin,
                0u,
                500u
            );

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


    const float margin =
        static_cast<float>(
            g_textConfig.margin
        );


    const D2D1_RECT_F textRect =
        D2D1::RectF(

            static_cast<float>(
                monitor.left
            )
            +
            margin,

            static_cast<float>(
                monitor.top
            )
            +
            margin,

            static_cast<float>(
                monitor.right
            )
            -
            margin,

            static_cast<float>(
                monitor.bottom
            )
            -
            margin
        );


    // --------------------------------------------------------
    // Shadow
    // --------------------------------------------------------

    if (
        g_textConfig.shadowEnabled
        &&
        g_shadowBrush
    )
    {
        const float offsetX =
            static_cast<float>(
                g_textConfig.shadowOffsetX
            );


        const float offsetY =
            static_cast<float>(
                g_textConfig.shadowOffsetY
            );


        const D2D1_RECT_F shadowRect =
            D2D1::RectF(
                textRect.left + offsetX,
                textRect.top + offsetY,

                textRect.right + offsetX,
                textRect.bottom + offsetY
            );


        g_renderTarget
            ->DrawTextW(
                text.c_str(),

                static_cast<UINT32>(
                    text.size()
                ),

                g_textFormat.Get(),

                shadowRect,

                g_shadowBrush.Get(),

                D2D1_DRAW_TEXT_OPTIONS_CLIP
            );
    }


    // --------------------------------------------------------
    // Main text
    // --------------------------------------------------------

    g_renderTarget
        ->DrawTextW(

            text.c_str(),

            static_cast<UINT32>(
                text.size()
            ),

            g_textFormat.Get(),

            textRect,

            g_textBrush.Get(),

            D2D1_DRAW_TEXT_OPTIONS_CLIP
        );
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

    g_transitioning =
        false;

    g_slideStartedAt =
        GetTickCount64();

    g_transitioning =
        false;

    g_slideStartedAt =
        GetTickCount64();
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


    const std::size_t position =
        (
            g_sequencePosition
            +
            monitorIndex
            +
            offset
        )
        %
        g_imageOrder.size();


    return g_imageOrder[
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
        5
    )
    {
        return g_config.transitionMode;
    }


    static std::mt19937 generator(
        static_cast<std::uint32_t>(
            GetTickCount64()
        )
    );


    static std::uniform_int_distribution<
        std::uint32_t
    > distribution(
        0,
        4
    );


    return distribution(
        generator
    );
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
    std::size_t monitorIndex
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


    switch (
        g_activeTransitionMode
    )
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
            D2D1::ColorF(
                D2D1::ColorF::Black
            )
        );


    if (
        !g_bitmaps.empty()
    )
    {
        float progress =
            0.0f;


        if (
            g_transitioning
            &&
            g_config.transitionMs
            >
            0
        )
        {
            const ULONGLONG elapsed =
                GetTickCount64()
                -
                g_transitionStartedAt;


            progress =
                static_cast<float>(
                    elapsed
                )
                /
                static_cast<float>(
                    g_config.transitionMs
                );


            progress =
                std::clamp(
                    progress,
                    0.0f,
                    1.0f
                );
        }


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


            if (!g_transitioning)
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
                    monitorIndex
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
    if (
        g_bitmaps.size()
        <=
        1
    )
    {
        return;
    }


    const ULONGLONG now =
        GetTickCount64();


    if (!g_transitioning)
    {
        const ULONGLONG elapsed =
            now
            -
            g_slideStartedAt;


        if (
            elapsed
            >=
            g_config.displayMs
        )
        {
            g_activeTransitionMode =
                ResolveTransitionMode();


            g_transitioning =
                true;


            g_transitionStartedAt =
                now;


            InvalidateRect(
                hwnd,
                nullptr,
                FALSE
            );
        }


        return;
    }


    const ULONGLONG elapsed =
        now
        -
        g_transitionStartedAt;


    if (
        elapsed
        >=
        g_config.transitionMs
    )
    {
        g_sequencePosition =
        (
            g_sequencePosition
            +
            1
        )
        %
        g_imageOrder.size();


        g_transitioning =
            false;


        g_slideStartedAt =
            now;
    }


    InvalidateRect(
        hwnd,
        nullptr,
        FALSE
    );
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


            g_slideStartedAt =
                g_startedAt;


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