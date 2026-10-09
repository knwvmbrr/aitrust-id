// Semantic anchors observed in live ChatGPT's Elements tree on 2026-10-08.
// This observation is not verification of the installed extension on that site.
(() => {
  const anchors = [
    '[data-markdown-text-style="assistant-message"]',
    '[data-message-author-role="assistant"]'
  ];
  const ids = ['data-chatgpt-selection-message-id', 'data-message-id'];
  const blocks = new Set(['DIV','P','PRE','LI','UL','OL','BLOCKQUOTE','H1','H2','H3','H4','TABLE','TR']);
  const excluded = '.aitrust-mount,[data-markdown-copy="exclude"],[hidden],[aria-hidden="true"],script,style,button';
  let anchorUsed = null;

  function responses() {
    const nodes = [...document.querySelectorAll(anchors.join(','))];
    // When an older wrapper contains a modern body, capture only the body.
    const bodies = nodes.filter(node => !nodes.some(other => other !== node && node.contains(other)));
    anchorUsed = bodies.length ? anchors.filter(selector => bodies.some(node => node.matches(selector))).join(', ') : null;
    return bodies;
  }
  function responseId(element) {
    for (let node = element; node && node !== document.body; node = node.parentElement) {
      for (const attr of ids) {
        const value = node.getAttribute(attr);
        if (value) return value;
      }
      if (node.hasAttribute('data-turn-key')) break;
    }
    // Some builds put the source identity inside the assistant body.
    for (const attr of ['data-dil-source-message-id','data-dil-message-id']) {
      const nodes = [...element.querySelectorAll(`[${attr}]`)];
      const values = new Set(nodes.map(node => node.getAttribute(attr)).filter(Boolean));
      if (values.size === 1) return [...values][0];
      if (values.size > 1) return null;
    }
    return null;
  }
  function text(element) {
    function collect(node) {
      if (node.nodeType === Node.TEXT_NODE) return node.nodeValue;
      if (node.nodeType !== Node.ELEMENT_NODE || node.matches(excluded)) return '';
      const style = getComputedStyle(node);
      if (style.display === 'none' || style.visibility === 'hidden') return '';
      if (node.tagName === 'BR') return '\n';
      const value = [...node.childNodes].map(collect).join('');
      return blocks.has(node.tagName) ? '\n' + value + '\n' : value;
    }
    return collect(element).replace(/\n{3,}/g, '\n\n').trim();
  }
  function streaming(element) {
    const turn = element?.closest('[data-talvt-turn-state]');
    if (turn && turn.getAttribute('data-talvt-turn-state') !== 'complete') return true;
    return Boolean(document.querySelector('button[data-testid="stop-button"],button[aria-label="Stop streaming"],button[aria-label="Stop generating"]'));
  }
  globalThis.AITrustAdapter = {responses,responseId,text,streaming,anchor:()=>anchorUsed,site:'chatgpt.com'};
})();
