part_apple: Apple rules for a Rust-owned page + JavaScriptCore-only script
(fetched 2026-11-13; quotes come via WebFetch extraction, re-verify any decisive one in a browser)

1. Guidelines
https://developer.apple.com/app-store/review/guidelines/
- 2.5.6: "Apps that browse the web must use the appropriate WebKit framework and WebKit JavaScript. You may apply for an entitlement to use an alternative web browser engine in your app. Learn more about these entitlements for the EU and Japan."
- 2.5.2: "Apps should be self-contained in their bundles, and may not read or write data outside the designated container area, nor may they download, install, or execute code which introduces or changes features or functionality of the app, including other apps. Educational apps designed to teach, develop, or allow students to test executable code may, in limited circumstances, download code provided that such code is not used for other purposes. Such apps must make the source code provided by the app completely viewable and editable by the user."
- the word "JavaScriptCore" does not appear in the guidelines (only the first 100000 of 114384 chars were read; 2.5.6 itself is complete)

2. Alternative engine entitlements
- EU: https://developer.apple.com/support/alternative-browser-engines/
  - "iOS and iPadOS include capabilities that let apps use alternative browser engines — browser engines other than WebKit — for dedicated browser apps and apps providing in-app browsing experiences in the EU."
  - "These capabilities are available to EU users on devices running a minimum of iOS 17.4 or iPadOS 18."
  - both entitlements: "Be distributed solely on iOS and/or iPadOS in the European Union;"
  - names: "Web Browser Engine Entitlement" (needs default web browser entitlement), "Embedded Browser Engine Entitlement" (must not have it)
  - JIT: "Apple will provide authorized developers access to technologies within the system that enable critical functionality and help developers offer high-performance modern browser engines. These technologies include just-in-time compilation, multiprocess support, and more."
  - tests: "90% of Web Platform Tests", "80% of Test262 on an iOS device, iPadOS device, or Mac with Apple silicon", and "Meet the above test suite requirement if Just in Time (JIT) compilation is unavailable (e.g., if Lockdown Mode is enabled by the user)"
  - security: "Use memory-safe programming languages, or features that improve memory safety within other languages, within the alternative web browser engine at a minimum for all code that processes web content;" and (browser entitlement only) "Use process separation to limit the effects of exploitation and validate inter-process communication (IPC) within the alternative web browser engine;"
  - privacy: "Block cross-site cookies (i.e., third-party cookies) by default unless the user expressly opts to allow such cookies with informed consent..."
- Japan (MSCA): https://developer.apple.com/support/alternative-browser-engines-jp
  - "In iOS 26.2 and later, browser engines other than WebKit can be used in two types of apps for users in Japan: Dedicated browser apps that provide a full web browser experience, and apps from browser engine stewards that provide in-app browsing experiences using an embedded browser engine."
  - "Be distributed solely on iOS in Japan (except for any other jurisdiction or Apple platform expressly permitted by Apple under the Developer Agreement ...)"
  - same JIT sentence and same 90% WPT / 80% Test262 / JIT-unavailable wording as EU
  - embedded entitlement: "A browser engine steward is an entity with the primary responsibility for operating a distinct web browser engine." (so not available to a new minimal browser)
  - browser apps must adopt "Pointer Authentication Codes (PAC); Memory Integrity Enforcement (MIE) ..."
  - context: https://developer.apple.com/support/app-distribution-in-japan (MSCA); Apple newsroom https://www.apple.com/newsroom/2025/12/apple-announces-changes-to-ios-in-japan/
- entitlement key names: I could not fetch the key docs (Apple docs render with JS). Not verified from a source: com.apple.developer.web-browser-engine.host / .webcontent / .networking / .rendering. Only the page title "com.apple.developer.web-browser-engine.webcontent | Apple Developer Documentation" was seen.
- JIT in the alt-engine path, https://developer.apple.com/documentation/browserenginekit/protecting-code-compiled-just-in-time (via the .json data endpoint):
  - "To prepare the compiled code, the web content extension must be able to write to a region of memory."
  - "Add the following entitlements to your web content extension's target, setting their values to true: com.apple.developer.kernel.extended-virtual-addressing, com.apple.security.cs.allow-jit"
  - so JIT lives only in the web content extension of an approved alt engine
- Regions elsewhere (US, etc.): I don't know of any; the guideline says "for the EU and Japan" only.

3. JIT in third-party apps
- https://developer.apple.com/forums/thread/746159
  - OP KTRosenberg: "Years ago, JSCore on non-macOS disabled JIT, leading to much worse performance than could possibly be achieved with JIT on. Has anything changed recently to permit greater optimizations for JSCore on mobile platforms?"
  - Apple DTS (Quinn "The Eskimo!"): "The only thing that springs to mind is the BrowserEngineKit stuff. ... I'm not sure if that changes the story for JavaScriptCore but, regardless, it has a limited scope."
  - another user (endecotp): "If you want to run Javascript with JIT on iOS, you can use WKWebView."
  - no Apple statement that JSContext is interpreter-only; Apple did not confirm or deny. Community/secondary claim only. I don't know of an Apple primary source stating it. (HN/Lucid posts claim JIT is off in-process; not quoted verbatim here.)
- WKWebView JIT: only the endecotp forum quote above (not Apple). I don't know of a primary Apple statement; the out-of-process reason is secondary.
- "dynamic-codesigning" entitlement: only seen as listed in WebKit's JavaScriptCore entitlements.plist (https://github.com/WebKit/WebKit/blob/main/Source/JavaScriptCore/entitlements.plist) per search snippet; contents not fetched. Apple not seen saying third parties cannot get it. I don't know.
- Lockdown Mode: https://support.apple.com/en-us/105120 says only "Certain complex web technologies are blocked, which might cause some websites to load more slowly or not operate correctly." It does not name JIT. Apple's alt-engine page does say JIT may be "unavailable (e.g., if Lockdown Mode is enabled by the user)".

4. Key question: JSContext for scripts + own DOM/renderer
- Not settled by any source I found. I don't know.
- Text reading: 2.5.6 says apps that "browse the web must use the appropriate WebKit framework and WebKit JavaScript". A Servo-style engine whose DOM/layout/network are non-WebKit is an "alternative browser engine" in practice, which outside EU/Japan has no entitlement path. Using JavaScriptCore.framework might or might not count as "WebKit JavaScript"; this phrase is undefined in the guidelines (inference, not sourced).
- 2.5.2 adds risk: page scripts are downloaded code. No quote from Apple on whether web page JS counts.
- No rejection or Apple statement found for this exact design. Search found none (UK CMA WP2 https://assets.publishing.service.gov.uk/media/667d2f0caec8650b100900c0/WP2_-_The_requirement_for_browsers_operating_on_iOS_devices_to_use_Apple_s_WebKit_browser_engine_1.pdf says browsers are prevented from using "modified versions or 'light forks' of the browser engine" per search snippet; not fetched/verified).
- Only way to get a definitive answer: ask App Review / Apple DTS (needs human approval; nothing was filed).
