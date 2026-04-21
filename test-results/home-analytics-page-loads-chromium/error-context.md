# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: home.spec.ts >> analytics page loads
- Location: tests/e2e/home.spec.ts:18:5

# Error details

```
Error: Channel closed
```

```
Error: page.goto: Target page, context or browser has been closed
Call log:
  - navigating to "http://localhost:3000/analytics", waiting until "domcontentloaded"

```

```
Error: browserContext.close: Test ended.
Browser logs:

<launching> /home/westonaaron675/.cache/ms-playwright/chromium_headless_shell-1217/chrome-headless-shell-linux64/chrome-headless-shell --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-extensions --disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,BoundaryEventDispatchTracksNodeRemoval,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,Translate,AutoDeElevate,RenderDocument,OptimizationHints --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --enable-automation --disable-infobars --disable-search-engine-choice-screen --disable-sync --enable-unsafe-swiftshader --headless --hide-scrollbars --mute-audio --blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4 --no-sandbox --user-data-dir=/tmp/playwright_chromiumdev_profile-5iPq5T --remote-debugging-pipe --no-startup-window
<launched> pid=30746
[pid=30746][err] [0421/003233.822663:ERROR:content/app/content_main_runner_impl.cc:413] Failed to initialize cpuinfo
[pid=30746][err] [0421/003233.822142:ERROR:content/app/content_main_runner_impl.cc:413] Failed to initialize cpuinfo
[pid=30746][err] [0421/003242.425587:WARNING:sandbox/policy/linux/sandbox_linux.cc:405] InitializeSandbox() called with multiple threads in process gpu-process.
[pid=30746][err] [0421/003247.145886:INFO:CONSOLE:32366] "%cDownload the React DevTools for a better development experience: https://reactjs.org/link/react-devtools font-weight:bold", source: webpack-internal:///(app-pages-browser)/./node_modules/next/dist/compiled/react-dom/cjs/react-dom.development.js (32366)
[pid=30746][err] [0421/003254.423717:INFO:CONSOLE:32366] "%cDownload the React DevTools for a better development experience: https://reactjs.org/link/react-devtools font-weight:bold", source: webpack-internal:///(app-pages-browser)/./node_modules/next/dist/compiled/react-dom/cjs/react-dom.development.js (32366)
[pid=30746] <gracefully close start>
```