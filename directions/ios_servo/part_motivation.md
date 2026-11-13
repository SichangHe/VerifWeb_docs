# vlm46 motivation research (web, 2026-11-13). Nothing published.

## 1. Netflix Gibbon

Language/architecture (partly settled)
- "our TV application consists of a C++ SDK installed natively on the device, an updatable JavaScript user interface (UI) layer, and a custom rendering layer known as Gibbon." (Netflix TechBlog, Bringing Rich Experiences to Memory-Constrained TV Devices, https://netflixtechblog.com/bringing-rich-experiences-to-memory-constrained-tv-devices-6de771eabb16)
- Language of Gibbon itself: I don't know. Only the SDK is called C++; the posts say "Our SDK team built a new rendering engine" (https://medium.com/netflix-techblog/building-the-new-netflix-experience-for-tv-920d71d875de) without naming a language. Inference only: Gibbon is in the C++ SDK.

JS engine
- "While we're not running full WebKit, we are heavily leveraging JavaScriptCore. We experimented with V8 and SpiderMonkey (with JIT), yet both were impractical without stable ports for the various chipset architectures in use by device manufacturers." (Netflix TechBlog, Pioneering application design on TVs & TV-connected devices, https://netflixtechblog.com/pioneering-application-design-on-tvs-tv-connected-devices-e361dbe02f66)
- "our JavaScript environment is an older non-JIT version of JavaScriptCore." (Netflix TechBlog, Crafting a high-performance TV user interface using React, https://medium.com/netflix-techblog/crafting-a-high-performance-tv-user-interface-using-react-3350e5a6ad3b)

Why not DOM/CSS
- "We wanted more fine-grained control of the graphics layer and wanted optimizations for apps that do not need reflowable content." (Building the New Netflix Experience for TV, https://medium.com/netflix-techblog/building-the-new-netflix-experience-for-tv-920d71d875de)

UI primitives
- "Our framework is optimized for fast 2D rendering of images, text and color fills. We render from a tree of graphics objects. The approach offers ease of use over immediate mode rendering contexts such as HTML canvas. Display property changes in these objects are aggregated then applied en masse post user interaction." (Pioneering application design..., URL above)
- Surfaces: "A bespoke rendering pipeline enables granular control over surfaces, the bitmap data representation of one or more graphics objects." Effects: "a pluggable cinematic effect pipeline with blur, desaturation, masking and tinting." (same post)
- Layout model: I don't know. No source states it (no flexbox/CSS claim found). Not documented in the posts I read.

React
- "Obviously, we'd need our own flavor of React since at that time it only targeted the DOM. We were able to create a prototype that targeted Gibbon pretty quickly. This prototype eventually evolved into React-Gibbon" (Crafting..., URL above)
- "React-Gibbon's API would be very familiar to anyone who has worked with React-DOM. The primary difference is that instead of divs, spans, inputs etc, we have a single "widget" drawing primitive that supports inline styling." (same)
- Focus: "we instead implemented a declarative focus API" (`<Widget focused={true} />`) instead of `.focus()` on refs. (same)

Open source: I don't know. Found no statement and no repo for Gibbon or React-Gibbon; absence of evidence only.

## 2. Motivation

Electron lags Chromium
- "Despite Electron's regular releases, these apps are consistently behind the latest version of Chrome. Additionally, each app follows its own release and update cycle, independent of Electron and Chrome. As a result, security fixes and updates remain unfixed and known vulnerabilities remain exploitable" (Ali et al., Rise of Inspectron, USENIX Security 2024, sec. on outdated Chromium, 8 apps Aug 2020-May 2023; https://www.usenix.org/system/files/sec24summer-prepub-120-ali.pdf)
- "The Wordpress desktop app utilizes outdated versions of Chromium, V8, and Blink, which contain bugs that have been targeted in RCE attacks." (same)
- "our findings indicate that most apps do not keep up with them." (same)
- ElectroVolt, DEF CON 2022: "the Discord desktop app was running with an older version of Electron, which in turn was using an older version of Chromium that was at risk. Microsoft Teams also found to be vulnerable to an account takeover risk, due in part to the fact that the application was using an older version of Electron." and Purani: "There is a noticeable patch gap between chromium and electron applications, which makes most of them susceptible to this attack" (Infosecurity Magazine, https://www.infosecurity-magazine.com/news/defcon-electrovolt-exploits/)
- Ox Security via BleepingComputer: "The latest releases of Cursor and Windsurf integrated development environments are vulnerable to more than 94 known and patched security issues in the Chromium browser and the V8 JavaScript engine." (https://www.bleepingcomputer.com/news/security/cursor-windsurf-ides-riddled-with-94-plus-n-day-chromium-vulnerabilities/)
- Slack incident: not searched; I don't know.

Spotify uses CEF
- "The Spotify Desktop client is a Windows and Mac native application that uses CEF (Chromium Embedded Framework) to display a web-based user interface." (Spotify Engineering, Building the Future of Our Desktop Apps, 2021, https://engineering.atspotify.com/2021/04/building-the-future-of-our-desktop-apps)
- No Spotify-specific CVE/lag source found.

TV platforms
- RDK/Comcast Lightning: "Lightning is an open-source WebGL/JavaScript-based UI framework that enables anyone to build high-quality TV apps with great performance. This framework has been specifically built to enable high-quality UI rendering on lower-end set-top boxes with memory constraints." (https://docs.developer.comcast.com/docs/lightning-for-xfinity). Also "a javascript TV app development framework that uses WebGL for rendering; apps developed in Lightning will run on all platforms with a modern, HTML5-based browser." (RDK Central, https://rdkcentral.com/lightning-thunder-and-resource-constrained-set-tops-training-recap/)
- LG webOS: "Web apps for webOS TV can be sub-categorized into two types: basic (packaged) web apps and hosted web apps." (https://webostv.developer.lge.com/develop/getting-started/web-app-types). Engine per release is a fixed Chromium on the TV; LG's table (https://webostv.developer.lge.com/develop/specifications/web-api-and-web-engine) lists it per version, per a search summary (not verbatim-checked by me): webOS 23 = Chromium 94, webOS 25 = Chromium 120. Treat those numbers as unverified; fetch the table before citing. Quote available: "From webOS TV 4.0, we do not provide the charts any longer. Instead, we let you know web engines and its versions used on webOS TV."
- Samsung Tizen, Vizio SmartCast: I don't know; fetches returned no usable text, no verbatim quotes.
- Amazon Vega: only third-party summaries (Dolby, Spyro-soft, MarketCast); claims "React Native", Hermes, Linux-based. No Amazon primary quote obtained; my fetches of Amazon docs returned 404/empty. Unverified.

## 3. Non-DOM UI stacks (README/docs quotes)

- Lightning/Lightning.js: "Lightning also enables additional performance gains by relying on WebGL and Canvas2D instead of DOM elements." Subset: render tree plus flexbox layout engine, animations, focus handling (Comcast docs list "Render tree (WebGL or Canvas2d)"; flexbox claim came from search summary, not verified verbatim). Lightning 3: "open-source project focused on lightweight solutions for developing User Interfaces with hyper fast animations using Javascript and WebGL rendering." (https://lightningjs.io/)
- React Native: "Fabric is React Native's new rendering system... The core principles are to unify more render logic in C++, improve interoperability with host platforms" Subset: host views, not DOM; Amazon docs for Vega not verified. (https://reactnative.dev/architecture/fabric-renderer)
- Flutter: "Flutter minimizes those abstractions, bypassing the system UI widget libraries in favor of its own widget set. The Dart code that paints Flutter's visuals is compiled into native code, which uses Impeller for rendering." Subset: widget tree; no HTML/CSS. (https://docs.flutter.dev/resources/architectural-overview)
- Slint: "Slint is an open-source declarative GUI toolkit to build native user interfaces for any device. Write your UI in `.slint`, a simple markup language" Subset: own markup, no HTML/CSS. (https://github.com/slint-ui/slint)
- Blitz (Dioxus native): "Blitz is designed to render HTML and CSS - we don't want to support the entirety of browser features (or at least we want to make all such "extra" features opt-in). In our opinion, the browser is bloated for the basic use case of rendering HTML/CSS." Uses "Stylo (CSS parsing/resolution), Taffy (box-level layout), Parley (text layout)"; renderer crate `blitz-renderer-vello`. "Modern HTML layout (flexbox, grid, table, block, inline, absolute/fixed, etc)." No JS engine in the quoted text; I don't know its JS story. (https://github.com/DioxusLabs/blitz)
- Makepad: "a cross-platform UI runtime for native and web targets." "A Rust-first framework with a scriptable UI DSL." "GPU-accelerated 2D and 3D rendering." Subset: own DSL, no HTML/CSS. (https://github.com/makepad/makepad)
- Lynx (ByteDance): "empowering developers to use their existing web skills to create truly native UIs for both mobile and web from a single codebase"; "Leverage your existing knowledge of CSS and React." Subset: CSS-like styling on native views, not full DOM. (https://github.com/lynx-family/lynx)
- Hippy (Tencent): no verbatim description obtained (README fetch gave only a directory tree). I don't know.
