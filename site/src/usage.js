// One use contract feeds the interactive modal, static reference and no-JS page.
export const repository = 'https://github.com/knwvmbrr/aitrust-id';
export const sourceDownload = repository + '/archive/refs/heads/main.zip';
export const quickstart = repository + '/blob/main/docs/open-validation-path.md';
const setup = [
  {title:'Get the source',body:'Download the ZIP and read its README, or use Git:',command:'git clone https://github.com/knwvmbrr/aitrust-id.git\ncd aitrust-id'},
  {title:'Prepare the checker',body:'From the repository folder, install its checker dependencies:',command:'python3 -m venv .venv\n.venv/bin/python -m pip install -r eval/requirements.txt\npython3 scripts/aitrust.py init'},
  {title:'Start your local services',body:'With Docker Engine and Compose running, build and start only AI Trust ID:',command:'make deploy ENV_FILE="$HOME/.config/aitrust-id/runtime.env"\n.venv/bin/python scripts/aitrust.py doctor'},
  {title:'Check an answer',body:'Save the answer as response.txt in this folder, then run:',command:'.venv/bin/python scripts/aitrust.py check response.txt'},
];
export function usage(tag) {
  const available = ['PS','PII_REDACTED'].includes(tag.id);
  if (!available) return {available:false,summary:tag.audience==='enterprise'
    ? 'Coming Soon. This team offering has no installer, checkout or active service yet.'
    : tag.proposed ? 'Research proposal. This code is not issued and has no downloadable checker yet.'
    : 'Coming Soon. This tag has no working checker to install yet.',
    steps:[],next:'See How it works for its intended job. Help improve this tag to contribute or follow its progress.'};
  return {available:true,summary:tag.id==='PS'
    ? 'On phone or computer: copy an AI answer, choose Check on this device, paste and check. No account, extension or Docker needed. The command patterns are checked, never executed.'
    : 'PII runs automatically before PS in the same local package. There is no separate PII installation or complete-privacy guarantee.',
    prerequisites:'Developer preview: Linux or macOS, Python 3.12+, Git, make, and Docker Engine with Compose. First setup downloads packages and models. A one-click installer and a Chrome Web Store release are not available yet.',
    phone:tag.id==='PS' ? 'Open aitrustid.com/#person/PS and choose Check on this device. Optional: save the public app for offline use and add it to your home screen. No answer is uploaded; the phone preview performs no redaction.' : null,
    steps:setup,next:tag.id==='PS'
      ? 'PS finding = a supported command-risk pattern. No finding = no supported pattern found, not “safe.” UNAVAILABLE = the check did not complete successfully.'
      : 'A PII tag means detected values were redacted before checking. No PII tag does not prove that the answer contains no private information.',
    browser:'Optional Chrome tags: open chrome://extensions, enable Developer mode, choose Load unpacked, select this repository’s extension folder, then enter your local token in its options. Keep the services running and open ChatGPT. Tags appear below supported answers; click a tag for a short explanation.',
    privacy:'Your answer goes to your own local service, not this website or a training database. Keep your token private. Do not paste it into a public report.',
    stop:'make down ENV_FILE="$HOME/.config/aitrust-id/runtime.env"'};
}
export function usageHTML(tag,esc) {
  const use=usage(tag);
  return `<section data-tag-usage><h2>Use this tag</h2><p>${esc(use.summary)}</p>${use.available
    ? `${use.phone ? `<p class="mt-2"><a href="/#person/PS">Check on this device</a></p><p>${esc(use.phone)}</p><h3 class="mt-3 font-semibold">Developer local service (optional)</h3>` : ''}<p class="mt-2 text-sm text-muted">${esc(use.prerequisites)}</p><p class="mt-3"><a href="${sourceDownload}">Download source</a> · <a href="${quickstart}">Full setup guide</a></p><ol class="mt-3 list-decimal space-y-3 pl-5">${use.steps.map(step=>`<li><h3 class="font-semibold">${esc(step.title)}</h3><p>${esc(step.body)}</p><pre class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(step.command)}</code></pre></li>`).join('')}</ol><p class="mt-3">${esc(use.next)}</p><p class="mt-3">${esc(use.browser)}</p><p class="mt-3">${esc(use.privacy)}</p><h3 class="mt-3 font-semibold">Stop the checker</h3><pre class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(use.stop)}</code></pre>`
    : `<p class="mt-2">${esc(use.next)}</p>`}</section>`;
}
