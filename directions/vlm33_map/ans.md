(authored by agents unless marked 🧑)

```
<svg xmlns="http://www.w3.org/2000/svg" width="2800" height="1840" viewBox="0 0 2800 1840" role="img" aria-labelledby="title desc">
<title id="title">Web things to formally verify: where each direction stands (Nov 2026)</title>
<desc id="desc">Research directions grouped by area and colored by status, with bug badges for confirmed bugs.</desc>
<rect width="100%" height="100%" fill="#ffffff"/>
<style>
  text { font-family: 'DejaVu Sans', sans-serif; fill:#17202a; }
  .title { font-size:58px; font-weight:700; }
  .panel-title { font-size:32px; font-weight:700; }
  .kept-title { font-size:36px; font-weight:700; fill:#0b5d2a; }
  .item { font-size:30px; font-weight:500; dominant-baseline:middle; }
  .item-kept { font-size:34px; font-weight:700; fill:#ffffff; }
  .legend { font-size:22px; font-weight:700; dominant-baseline:middle; }
  .legend-note { font-size:21px; font-weight:600; fill:#a61b11; dominant-baseline:middle; }
  .dropped { fill:#666b73; }
  .bug { font-size:15px; font-weight:800; fill:white; dominant-baseline:middle; text-anchor:middle; }
</style>

<text x="70" y="78" class="title">Web things to formally verify: where each direction stands (Nov 2026)</text>

<rect x="60" y="112" width="2680" height="112" rx="22" fill="#f8fafc" stroke="#d9e0e7" stroke-width="2"/>

<rect x="85" y="138" width="300" height="58" rx="13" fill="#16a34a" stroke="#087a35" stroke-width="4"/>
<text x="235" y="168" class="legend" text-anchor="middle" style="fill:#ffffff">KEPT</text>

<rect x="405" y="138" width="335" height="58" rx="13" fill="#f6c453" stroke="#b37a15" stroke-width="2"/>
<text x="572.5" y="168" class="legend" text-anchor="middle" style="fill:#352600">LOW PRIORITY</text>

<rect x="760" y="138" width="300" height="58" rx="13" fill="#dceeff" stroke="#4f8fc8" stroke-width="2"/>
<text x="910" y="168" class="legend" text-anchor="middle" style="fill:#163a5c">MENTION</text>

<rect x="1080" y="138" width="410" height="58" rx="13" fill="#dfccf7" stroke="#8358b8" stroke-width="2"/>
<text x="1285" y="168" class="legend" text-anchor="middle" style="fill:#422363">NOT READY TO SHARE</text>

<rect x="1510" y="138" width="405" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1712.5" y="168" class="legend dropped" text-anchor="middle" style="fill:#666b73">DROPPED by the human</text>
<line x1="1563.3" y1="168" x2="1861.7" y2="168" stroke="#666b73" stroke-width="2.2"/>

<rect x="1935" y="138" width="360" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="2115" y="168" class="legend" text-anchor="middle" style="fill:#333b44">NOT DISCUSSED</text>

<rect x="2320" y="151" width="62" height="32" rx="10" fill="#d92d20"/>
<text x="2351" y="168" class="bug">BUG</text>
<text x="2398" y="168" class="legend-note">real bug found and confirmed</text>

<!-- kept directions -->
<rect x="60" y="250" width="2680" height="238" rx="26" fill="#edfff3" stroke="#2a9d57" stroke-width="3"/>
<text x="88" y="298" class="kept-title">Kept directions</text>

<rect x="88" y="322" width="858.7" height="138" rx="19" fill="#16a34a" stroke="#087a35" stroke-width="5"/>
<text x="517.3" y="380" class="item-kept" text-anchor="middle">Agent-browser core on Servo:</text>
<text x="517.3" y="423" class="item-kept" text-anchor="middle">many sessions in one process</text>

<rect x="970.7" y="322" width="858.7" height="138" rx="19" fill="#16a34a" stroke="#087a35" stroke-width="5"/>
<text x="1400" y="393" class="item-kept" text-anchor="middle" dominant-baseline="middle">SSO sign-in / sign-out consistency</text>

<rect x="1853.3" y="322" width="858.7" height="138" rx="19" fill="#16a34a" stroke="#087a35" stroke-width="5"/>
<text x="2282.7" y="393" class="item-kept" text-anchor="middle" dominant-baseline="middle">Collaborative-editor sync protocol</text>

<!-- JS engines -->
<rect x="60" y="518" width="834" height="629" rx="24" fill="#f7f9fb" stroke="#d6dde5" stroke-width="2"/>
<text x="84" y="563" class="panel-title">JS engines</text>

<rect x="82" y="588" width="790" height="58" rx="13" fill="#f6c453" stroke="#b37a15" stroke-width="2"/>
<text x="100" y="618" class="item" style="fill:#352600">JS engines vs spec (Rust engine, map to V8)</text>
<rect x="802" y="603" width="58" height="28" rx="9" fill="#d92d20"/>
<text x="831" y="618" class="bug">BUG</text>

<rect x="82" y="654" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="100" y="684" class="item" style="fill:#333b44">JIT proofs (side effects, ranges, phases)</text>

<rect x="82" y="720" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="100" y="750" class="item" style="fill:#333b44">Wasm / V8 sandbox bounds</text>

<!-- agent browsers -->
<rect x="953" y="518" width="834" height="629" rx="24" fill="#f7f9fb" stroke="#d6dde5" stroke-width="2"/>
<text x="977" y="563" class="panel-title">Agent browsers &amp; shared processes</text>

<rect x="975" y="588" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="618" class="item" style="fill:#333b44">Lightpanda block-urls misses WebSocket</text>
<rect x="1695" y="603" width="58" height="28" rx="9" fill="#d92d20"/>
<text x="1724" y="618" class="bug">BUG</text>

<rect x="975" y="654" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="993" y="684" class="item dropped" style="fill:#666b73">Servo cookie/credential destinations</text>
<line x1="993" y1="684" x2="1539.2" y2="684" stroke="#666b73" stroke-width="2.2"/>

<rect x="975" y="720" width="790" height="58" rx="13" fill="#dceeff" stroke="#4f8fc8" stroke-width="2"/>
<text x="993" y="750" class="item" style="fill:#163a5c">click / user activation across processes (Servo)</text>

<rect x="975" y="786" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="993" y="816" class="item dropped" style="fill:#666b73">agent context isolation</text>
<line x1="993" y1="816" x2="1338.3" y2="816" stroke="#666b73" stroke-width="2.2"/>

<rect x="975" y="852" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="882" class="item" style="fill:#333b44">agent's view = human's view</text>

<rect x="975" y="918" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="948" class="item" style="fill:#333b44">leak budget for shared processes</text>

<rect x="975" y="984" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="1014" class="item" style="fill:#333b44">per-tenant check of JIT output</text>

<!-- browser state -->
<rect x="1846" y="518" width="834" height="629" rx="24" fill="#f7f9fb" stroke="#d6dde5" stroke-width="2"/>
<text x="1870" y="563" class="panel-title">Browser state &amp; permissions</text>

<rect x="1868" y="588" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1886" y="618" class="item dropped" style="fill:#666b73">back/forward cache can't revive the past</text>
<line x1="1886" y1="618" x2="2499.3" y2="618" stroke="#666b73" stroke-width="2.2"/>

<rect x="1868" y="654" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="1886" y="684" class="item" style="fill:#333b44">Clear-Site-Data really erases</text>

<rect x="1868" y="720" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="1886" y="750" class="item" style="fill:#333b44">Storage Access answers agree</text>

<rect x="1868" y="786" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="1886" y="816" class="item" style="fill:#333b44">extension permissions</text>

<rect x="1868" y="852" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="1886" y="882" class="item" style="fill:#333b44">domain changes owner</text>

<rect x="1868" y="918" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1886" y="948" class="item dropped" style="fill:#666b73">cross-tab coordination</text>
<line x1="1886" y1="948" x2="2220.6" y2="948" stroke="#666b73" stroke-width="2.2"/>

<rect x="1868" y="984" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1886" y="1014" class="item dropped" style="fill:#666b73">cookie domain vs Public Suffix List</text>
<line x1="1886" y1="1014" x2="2402.8" y2="1014" stroke="#666b73" stroke-width="2.2"/>

<rect x="1868" y="1050" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="1886" y="1080" class="item" style="fill:#333b44">URL parser = WHATWG (rust-url)</text>
<rect x="2588" y="1065" width="58" height="28" rx="9" fill="#d92d20"/>
<text x="2617" y="1080" class="bug">BUG</text>

<!-- privacy -->
<rect x="60" y="1171" width="834" height="629" rx="24" fill="#f7f9fb" stroke="#d6dde5" stroke-width="2"/>
<text x="84" y="1216" class="panel-title">Privacy &amp; ads</text>

<rect x="82" y="1241" width="790" height="58" rx="13" fill="#dfccf7" stroke="#8358b8" stroke-width="2"/>
<text x="100" y="1271" class="item" style="fill:#422363">cookie consent revocation</text>

<rect x="82" y="1307" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="100" y="1337" class="item" style="fill:#333b44">ad-blocker rule compilation</text>

<rect x="82" y="1373" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="100" y="1403" class="item" style="fill:#333b44">ad-measurement privacy budget</text>

<rect x="82" y="1439" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="100" y="1469" class="item" style="fill:#333b44">bounce-tracking cleanup timing</text>

<!-- servers -->
<rect x="953" y="1171" width="834" height="629" rx="24" fill="#f7f9fb" stroke="#d6dde5" stroke-width="2"/>
<text x="977" y="1216" class="panel-title">Servers, CDNs, protocols</text>

<rect x="975" y="1241" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="993" y="1271" class="item dropped" style="fill:#666b73">shared caches</text>
<line x1="993" y1="1271" x2="1209.2" y2="1271" stroke="#666b73" stroke-width="2.2"/>

<rect x="975" y="1307" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="993" y="1337" class="item dropped" style="fill:#666b73">CDN purge across tiers</text>
<line x1="993" y1="1337" x2="1338.1" y2="1337" stroke="#666b73" stroke-width="2.2"/>

<rect x="975" y="1373" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="993" y="1403" class="item dropped" style="fill:#666b73">HTTP/2 flow-control liveness</text>
<line x1="993" y1="1403" x2="1416.2" y2="1403" stroke="#666b73" stroke-width="2.2"/>

<rect x="975" y="1439" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="993" y="1469" class="item dropped" style="fill:#666b73">HTTP/1.1 framing agreement (Pingora/hyper)</text>
<line x1="993" y1="1469" x2="1670.6" y2="1469" stroke="#666b73" stroke-width="2.2"/>

<rect x="975" y="1505" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="1535" class="item" style="fill:#333b44">HTTP/2 stream limits (Rapid Reset)</text>

<rect x="975" y="1571" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="1601" class="item" style="fill:#333b44">Encrypted Client Hello fallback</text>

<rect x="975" y="1637" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="1667" class="item" style="fill:#333b44">certificate transparency logs can't fork</text>

<rect x="975" y="1703" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="993" y="1733" class="item" style="fill:#333b44">federated social sync (Bluesky/Mastodon)</text>

<!-- pages -->
<rect x="1846" y="1171" width="834" height="629" rx="24" fill="#f7f9fb" stroke="#d6dde5" stroke-width="2"/>
<text x="1870" y="1216" class="panel-title">Pages, archives, odd ideas</text>

<rect x="1868" y="1241" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1886" y="1271" class="item dropped" style="fill:#666b73">page-scripts load-time check</text>
<line x1="1886" y1="1271" x2="2320.6" y2="1271" stroke="#666b73" stroke-width="2.2"/>

<rect x="1868" y="1307" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1886" y="1337" class="item dropped" style="fill:#666b73">web archive replay</text>
<line x1="1886" y1="1337" x2="2170.8" y2="1337" stroke="#666b73" stroke-width="2.2"/>

<rect x="1868" y="1373" width="790" height="58" rx="13" fill="#e6e8eb" stroke="#a6abb2" stroke-width="2"/>
<text x="1886" y="1403" class="item dropped" style="fill:#666b73">proofs that expire with web atoms</text>
<line x1="1886" y1="1403" x2="2400.4" y2="1403" stroke="#666b73" stroke-width="2.2"/>

<rect x="1868" y="1439" width="790" height="58" rx="13" fill="#ffffff" stroke="#9ca3af" stroke-width="2" stroke-dasharray="9 7"/>
<text x="1886" y="1469" class="item" style="fill:#333b44">measurement shims invisible to pages</text>
</svg>
```
