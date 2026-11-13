# vl_meeting_todo_1: is the "tabs race on refresh-token rotation" sign-out real? (GitHub issue dig)
(authored by agents)

Why: to-do 2 (Harsha: "Have people studied why some tabs get logged out and others don't?"). ../vlm41_sso inferred the cause is clients racing on a rotating refresh token, backed only by "small issue threads; no frequency data"; ../vlm43_oidc reproduced it in TLA+. This dig checks public bug reports.

## Takeaways
1. Fact: the race is reported repeatedly in real software, with the same mechanism: two holders spend one refresh token, the server's reuse detection (RFC 6819 5.2.2.3) revokes the whole token family, all holders are signed out. 105 unique issues matched 6 GitHub searches (raw/global.json); I read 10 (raw/bodies.txt).
2. Inference: in 2026 the dominant victims are no longer browser tabs but parallel agent processes sharing one credential (Claude Code, Codex, MCP SDK). This is the same bug, larger blast radius ("mid-run agents die").
3. Fact: library fixes are ad hoc and partial (Vikunja's dedupe fix "#2948" still fails in v2.4.0). Opinion: this supports the SSO direction as "client-side token handling is unverified concurrent code", a cleaner target than provider bugs.
4. I don't know frequency: issue counts are not user counts; reactions are small (0-3 per issue read). Per-library searches (auth0-spa-js, next-auth, MSAL, Firebase, Okta, Clerk) returned 0-5 hits each; search terms may miss them.

## Verbatim evidence
- modelcontextprotocol/typescript-sdk#1760: "When two requests for the same OAuth MCP server arrive in parallel, both calls independently detect a 401, call `auth()`, and race to refresh using the same refresh token. With OAuth servers that use rotating refresh tokens (e.g. Atlassian, Asana), this triggers RFC 6819 5.2.2.3 replay detection — the authorization server detects that a consumed refresh token was reused and revokes the entire token family, permanently breaking the connection until the user manually re-authorizes."
- anthropics/claude-code#74250: "Multiple concurrent Claude Code sessions (or subagent connections) on one machine share the per-server entry in `~/.claude/.credentials.json` ... Each process appears to refresh from its **in-memory copy** of the refresh token rather than re-reading the store." ... "the AS treats it as token theft, revokes the **entire family** ... only interactive `/mcp` re-auth recovers — mid-run agents die."
- manfredsteyer/angular-oauth2-oidc#1077 (2021, browser tabs): "When using application it multiple tabs, refresh token triggered and fails. Issue seems to be due to concurrent calls to refresh token in all tabs."
- go-vikunja/vikunja#3383: "Related to #2863 / fixed by #2948 ("dedupe and retry token refresh to prevent spurious logouts"), which shipped in v2.4.0. We're running v2.4.0 and still seeing the identical symptom" ... "Users get logged out every few minutes".
- the-momentum/open-wearables#1433 (server workers, not tabs): "Multiple Celery workers can load the same stored refresh token near access-token expiry ... Only one refresh succeeds".
- openai/codex#14201, #25599: "Your access token could not be refreshed because your refresh token was already used. Please log out and sign in again."
- Related non-race sign-out: supabase/supabase-js#2715: "a rate-limited refresh signs the user out" (429/408 treated as a dead session).

## Next (opinion)
- Model claude-code#74250's shared-file store in ../vlm43_oidc's TLA+ model (cross-process, not cross-tab) and check the "re-read the store under a file lock before refresh" fix.
- Count reuse-detection defaults per provider (GoTrue 10 s window, Auth0, Okta) to see which providers make the race fatal.
