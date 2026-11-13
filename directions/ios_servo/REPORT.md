# Minimal secure browser on iOS with JavaScriptCore (vlm46_ios)
(authored by agents unless marked 🧑)

Human's words 🧑: "We'll need something that could have its JS engine swapped for JavaScriptCore so it works on iOS with lesser security"; "Yes, let's say e.g. whether we can put Servo on top"; "If that's how they do it, maybe we should just do like they do in terms of what UI stuffs they support? Do we have more info on how that stack is? Maybe already written in Rust??"

Detailed quotes with URLs are in part_apple.md, part_servo.md and part_motivation.md in this directory. Some quotes were taken from a fetch tool's summary rather than the page, and those files mark which ones. Re-check any quote that a decision depends on.

## Bottom line
- Technically, a design where Servo owns the page and JavaScriptCore runs only scripts looks possible, but it is a large port. Servo is tightly bound to SpiderMonkey, and no abstraction layer exists yet.
- Policy is the blocker. Guideline 2.5.6 quoted: "Apps that browse the web must use the appropriate WebKit framework and WebKit JavaScript. You may apply for an entitlement to use an alternative web browser engine in your app." Servo doing DOM and layout is a non-WebKit engine, whatever JS engine it uses. Swapping to JavaScriptCore does not by itself make it allowed.
- Outside the EU and Japan, I don't know whether "WebKit JavaScript" plus our own renderer passes App Review. No source, rejection or Apple statement settles it. Only Apple can answer, and asking needs human approval.
- A design that avoids the question entirely is a Gibbon-like app runtime: our own UI primitives (not a browser for arbitrary web) plus JSContext. Netflix ships exactly that, and policy then concerns 2.5.2 (downloaded code) rather than 2.5.6.

## Apple rules
- 2.5.2 quoted: "...nor may they download, install, or execute code which introduces or changes features or functionality of the app..." Whether web page JS counts here is not addressed by Apple in anything found.
- Alternative engine entitlement:
  - EU: iOS 17.4+, app "distributed solely on iOS and/or iPadOS in the European Union".
  - Japan (MSCA): iOS 26.2+, "distributed solely on iOS in Japan".
  - Requirements: 90% Web Platform Tests and 80% Test262 pass rates, also with JIT off. Memory-safe language for code that processes web content (Rust fits).
  - JIT is granted to entitled engines.
- JIT:
  - Standalone JSContext in a third-party app: the common claim is that it runs interpreter-only. I found no Apple statement confirming it.
  - WKWebView: only a forum user says it gets JIT, not Apple.
  - Netflix independently runs "an older non-JIT version of JavaScriptCore", so interpreter-only performance is shippable for app UIs.

## Servo distance to a JavaScriptCore swap
- Coupling (shallow clone, `components/`): 814 .rs files match mozjs/js::, 150 use raw `js::jsapi`. `components/script` is about 286k lines, and the WebIDL codegen is about 9.9k lines of Python. Its GC rooting and tracing are SpiderMonkey's.
- No engine abstraction exists. Servo's 2024 blog post names React Native's JSI as a model. Issue #49095 has maintainers discussing a possible layer, and a QuickJS fork swaps engines by substituting the mozjs crate. No source mentions JavaScriptCore.
- iOS: I don't know whether Servo currently builds or runs there. The only iOS item is meta-issue #18154 from about 2017, and current mobile work covers Android and OpenHarmony. SpiderMonkey interpreter-only builds have precedent, so if entitled (EU/Japan), keeping SpiderMonkey may be cheaper than switching to JavaScriptCore.
- Prior art for engine swaps:
  - React Native: JSC to Hermes via the JSI interface.
  - NativeScript: V8 on iOS.
  - node-chakracore.
  - Edge: Chakra to V8.
  These are partly unverified; see part_servo.md.

## Motivation sources
- Electron lag: USENIX Security 2024 (Ali et al.): apps are "consistently behind the latest version of Chrome". ElectroVolt (DEF CON 2022) covers Discord and Teams. Ox Security (via BleepingComputer) reports 94+ n-day Chromium bugs in Cursor and Windsurf.
- Spotify: Spotify's engineering blog confirms the desktop client uses CEF. I found no lag or CVE source specific to Spotify.
- TV web apps:
  - LG webOS: LG confirms web apps on a fixed Chromium version per release.
  - RDK/Lightning: Comcast says it is WebGL-based.
  - Tizen, Vizio, Amazon Vega: no verbatim sources found.

## Gibbon and similar non-DOM UI stacks
- Netflix Gibbon:
  - "a custom rendering layer known as Gibbon", alongside a "C++ SDK". I infer Gibbon itself is C++; I don't know for sure.
  - JS engine: "an older non-JIT version of JavaScriptCore". Netflix tried V8 and SpiderMonkey.
  - UI: "instead of divs, spans, inputs etc, we have a single "widget" drawing primitive that supports inline styling". It is optimized for images, text and fills, with blur, tint and mask effects. Focus is declarative (`<Widget focused={true} />`). The layout model is undocumented.
  - React targets it through a custom renderer, React-Gibbon.
  - Open source: none found. It is not Rust, as far as the sources show.
- Similar stacks and the UI subset each supports:
  - Lightning.js: WebGL canvas, own element tree, runs inside an HTML5 browser. The claim that it has a flexbox layout engine is unverified.
  - React Native: native platform views with a Flexbox subset (Yoga) and its own style objects, no DOM. Runs on Hermes or JSC.
  - Flutter: own widget set drawn by Impeller, Dart rather than JS, no HTML/CSS.
  - Slint (Rust): own declarative .slint markup and widgets, no DOM or JS.
  - Blitz (Dioxus, Rust): renders real HTML and CSS via Stylo, Taffy and Parley. I don't know its JS story. It is the closest Rust "browser-lite" for a Servo-without-SpiderMonkey shape.
  - Makepad (Rust): own DSL and GPU widgets, no DOM.
  - Lynx (ByteDance): web-like markup and CSS subset on a native renderer, with a JS runtime.
  - Hippy: nothing verified.

## Open questions (I don't know)
- Does App Review accept JSContext with a non-WebKit renderer outside the EU and Japan? Only Apple can say, and asking needs approval.
- Does third-party JSContext really lack JIT on current iOS? Needs a device test or an Apple source.
- Does Servo or mozjs build for iOS today?
