// Runs in the PAGE's JS world at document_start, before the site's own bundle.
// Manifest V3 removed response-body access from chrome.webRequest, so this is the
// only supported way to observe streamed model output with structure intact.
// It NEVER sends anything anywhere — it posts to the isolated world and stops.

(() => {
  const MATCHERS = [
    /\/api\/organizations\/.*\/chat_conversations\/.*\/completion/,
    /\/backend-api\/conversation/,
    /StreamGenerate/
  ];

  const origFetch = window.fetch;
  window.fetch = async function (input, init) {
    const res = await origFetch.call(this, input, init);
    const url = typeof input === "string" ? input : (input && input.url) || "";
    if (!res.body || !MATCHERS.some((m) => m.test(url))) return res;

    // tee() so the page's own consumer is completely untouched
    let pageStream, tapStream;
    try {
      [pageStream, tapStream] = res.body.tee();
    } catch {
      return res; // never break the host page
    }
    drain(tapStream, url).catch(() => {});
    return new Response(pageStream, {
      status: res.status,
      statusText: res.statusText,
      headers: res.headers
    });
  };

  async function drain(stream, url) {
    const reader = stream.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
    }
    window.postMessage(
      { __aitrust: "capture", url, raw: buf, at: Date.now() },
      window.location.origin
    );
  }
})();
