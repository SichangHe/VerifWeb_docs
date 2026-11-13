servo -> JavaScriptCore on iOS: findings (2026-11-13)

bottom line (inference)
- no JSC effort exists that I found; no abstraction layer exists; i don't know of any servo iOS build
- swap = rewrite of script crate glue + WebIDL codegen + GC rooting; closest precedent is an out-of-tree quickjs fork via mozjs-crate shim
- JSC on iOS has its own wall: stock apps cannot JIT, JSC embedding API is C (JavaScriptCore.framework) with no SpiderMonkey-style rooted-handle model (my knowledge, unchecked)

coupling (measured, shallow clone of servo/servo main, HEAD dated 2026-11-13, /tmp/servo_clone/servo)
- /tmp/servo_clone/servo/Cargo.toml:146 `js = { package = "mozjs", version = "=0.26.14", default-features = false, features = ["intl", "libz-sys"] }`
- 814 .rs files under components/ match `mozjs|js::|use js`; 2597 matching lines (grep)
- 150 files / 191 lines reference `js::jsapi` (raw SpiderMonkey API)
- components/script: 285,875 lines of rust; components/script/dom: 261,144; components/script_bindings: 13,406
- WebIDL codegen: components/script_bindings/codegen/codegen.py is 9,906 lines (python, emits rust against js::/mozjs types); plus configuration.py 627, run.py 244
- script_bindings/lib.rs:36 `pub mod js;` (a js module exists in the bindings crate; i did not read whether it is a real abstraction)
- crate features debugmozjs/profilemozjs are passed straight to js (components/script/Cargo.toml:22,33)
- i did not count #[dom_struct]/JSTraceable usage: my grep for JSTraceable returned 0 because of a shell glob error; unsettled

servo's own words, https://servo.org/blog/2024/04/15/spidermonkey/
- "Servo already comes with abstractions and interfaces for a large surface area of its integration with SpiderMonkey"
- "Other parts of that integration rely on direct, and unsafe, calls into the low-level SpiderMonkey APIs."
- "the safer higher-level constructs that replace low-level SpiderMonkey API calls are still internally tightly coupled"
- "a second layer of abstraction: one that would hide the underlying script engine."
- "An existing, and encouraging, example of such a layer comes from React Native in the form of its JavaScript Interface (JSI)."
- "how easy would it be for Servo to use Chrome's V8 engine, or the next big script engine?"
- note: quotes via WebFetch summarizer, truncated at 125 chars; JSC not named

discussion, https://github.com/servo/servo/issues/49095 ("Minimum size builds")
- jschwe: QuickJS swap "showed ~31MB size reduction (86->54.4MB)"; fork works via substitute `mozjs` crate with cargo `patch`
- sagudev: "QuickJS does not have JIT."
- nicoburns: "Maintained a fork seems non-ideal. I wonder if we should look again at an abstraction layer." cites gterzian/formal-web as feasibility evidence; cites Boa in Blitz, Hermes in React Native
- jschwe: "It would definitely be nice to be able to work towards an abstraction layer"; sees it as unrealistic short-term
- webbeef: "I would absolutely not go with a non-JIT JS runtime for instance, even to save 50MB."
- JSC / JavaScriptCore appears nowhere on the page
- other: https://github.com/XiaoxiangCoding/servo-quickjs (experimental, agent-driven quickjs backend implementing mozjs crate API); https://github.com/gterzian/spidermonkey_servo (background doc); https://www.phoronix.com/news/Servo-JavaScript-Engine-Modular. not opened by me beyond search snippets
- i did not search Servo Zulip (not web-indexed as far as i know); i don't know whether "jsc" was discussed there

servo on iOS
- https://github.com/servo/servo/issues/18154 "Apple iOS support": open meta-issue, label P-iOS, ~2017; instructs `./mach build -d --target aarch64-apple-ios`. snippet only, not fully read
- local repo: ports/ has only servoshell; grep for ios in .rs/.toml/.md gave no output (globbing error risk, so weak evidence)
- mobile servoshell work found: Android and OpenHarmony only (https://github.com/servo/servo/pull/35192; issue #48369 labels android/ohos)
- i don't know if servo currently builds or runs on iOS; no evidence it does

spidermonkey on iOS
- interpreter-only has precedent: https://github.com/play-co/spidermonkey-ios/blob/master/README.md "Apple does not allow self-modifying app code onto the App Store, so the Game Closure SDK is based on the interpreter mode of SpiderMonkey, rather than the much faster IonMonkey engine." (search-snippet text; old SpiderMonkey 1.8-era)
- https://bugzilla.mozilla.org/show_bug.cgi?id=735728 "add support for building JS on iOS"
- newer: https://cfallin.org/blog/2023/10/11/spidermonkey-pbl/ Portable Baseline Interpreter needs no runtime codegen (snippet paraphrase)
- gecko iOS: https://bugzilla.mozilla.org/show_bug.cgi?id=1883457 "[Gecko iOS] Basic support for BrowserEngineCore JIT on iOS": "This will be used on iOS, where the jit entitlements are only available for sandboxed content processes."
- implication (inference): SpiderMonkey with JIT off is plausible on iOS, so JSC is not required for technical reasons; it matters only if you want Apple-grade JIT inside WKWebView-like rules. whether current mozjs crate builds for aarch64-apple-ios: i don't know

app store rules, https://developer.apple.com/support/alternative-browser-engines
- "These capabilities are available to EU users on devices running a minimum of iOS 17.4 or iPadOS 18."
- "Be distributed solely on iOS and/or iPadOS in the European Union;"
- "90% of Web Platform Tests" and "80% of Test262 on an iOS device..." and must "Meet the above test suite requirement if Just in Time (JIT) compilation is unavailable"
- "These technologies include just-in-time compilation, multiprocess support, and more."
- so outside EU/Japan, only WKWebView (WebKit) is allowed for browsers (my knowledge; search result says Japan also allows). JSC swap alone does not fix that: servo itself is a non-WebKit engine, so it needs the EU/Japan entitlement anyway
- firefox for iOS: uses WebKit (widely known; no primary source fetched). sources disagree whether gecko shipped on iOS EU in 2026 (ttlab blog May 2026 says piloted; browserpedia says none). i don't know

prior art on swapping engines (mostly from search snippets; names only where unfetched)
- react native: JSI, C++ interface. snippet: "no further changes were required in order to actually switch the engine itself" (old ExecutorFactory); Hermes default since 2022 (snippet). https://github.com/facebook/hermes/discussions/1393 tmikov: JSI is the only way to write extensions compatible across JSC, v8, Hermes. cost: meta designed JSI up front for own host objects
- expo: per-platform jsEngine override incl. "jsc" on ios (https://docs.expo.dev/guides/using-hermes/)
- from my memory, not checked this session: nativescript runs V8 on iOS jitless; node-chakracore shimmed V8 API on ChakraCore then was archived; ladybird writes own LibJS (no swap, built from SerenityOS); edge moved Chakra+EdgeHTML to V8+Blink in 2020 by replacing the whole engine, not swapping; blitz uses Boa (per nicoburns above); deno/bun tied to V8/JSC respectively. i did not verify any of these
