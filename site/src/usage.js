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
  const orgNext={
    fleet:'Review the extension permissions in the public source, then tell us how your team manages installs and updates.',
    host:'Help define which files an agent may read, how it asks permission, and how you pause or remove it.',
    audit:'Try PS on this device and download its result summary. A detailed record is a separate, optional export. “Download details” in this panel saves the offering description, not a checked answer.',
    sso:'Compare the proposed configure, view, review and export permissions with your team’s groups. Tell us what needs to change.',
    support:'Use Report an issue for a defect. For a vulnerability, choose the private security channel; do not post sensitive details publicly.',
    proprietary:'Review the proposed private-policy boundaries. Share your requirements without including confidential documents.'};
  const tagNext={
    NF:'Suggest a claim and the reference passage that supports it.',
    FI:'Share a claim and a reference passage that disagree.',
    HP:'Suggest a claim that needs checking, with a source that explains why.',
    MT:'Share an example of urgent wording and the context that makes it helpful or pressuring.',
    IV:'Help define what a reviewer should record, and how to correct or withdraw a review.',
    FA:'Suggest a generation record that could show where an item came from.',
    PA:'Suggest a consented example of an AI draft and the edits made afterward.',
    UNK:'Share a case where a checker should say it does not have enough evidence.',
    PII_OUTBOUND:'Help identify where a useful privacy reminder should appear before sending.',
    UC:'Review the proposed name and command scope in How it works.',
    SC:'Suggest a suspicious message and a similar everyday request to compare.',
    BT:'Suggest verifiable automation evidence and a human example that could look similar.'};
  if (!available) return {available:false,summary:tag.audience==='enterprise'
    ? 'Explore the plan and tell us what your team needs. This offering is not available to buy.'
    : tag.proposed ? 'Read the proposal or share an example that would help us test it.'
    : 'Explore how this tag would work, or share an example to help us build it.',
    steps:[],next:orgNext[tag.id]||tagNext[tag.id]};
  return {available:true,summary:tag.id==='PS'
    ? 'Copy an AI answer, paste it and check. No account or install needed. Commands are checked, never run.'
    : 'PII runs before PS in the local service. Set it up once and detected personal details are redacted automatically. This is not part of the website’s on-device checker.',
    prerequisites:'Developer preview: Linux or macOS, Python 3.12+, Git, make, and Docker Engine with Compose. First setup downloads packages and models. A one-click installer and a Chrome Web Store release are not available yet.',
    phone:tag.id==='PS' ? 'Open aitrustid.com/#person/PS and choose Check on this device. Optional: save the public app for offline use and add it to your home screen. No answer is uploaded; the phone preview performs no redaction.' : null,
    steps:setup,next:tag.id==='PS'
      ? 'A PS finding asks you to review a command pattern. No finding means no supported pattern was found, not “safe.” If a check cannot finish, it says so.'
      : 'A PII tag means detected values were redacted. Without a tag, private details may still be present.',
    browser:'Optional Chrome tags: open chrome://extensions, enable Developer mode, choose Load unpacked, select this repository’s extension folder, then enter your local token in its options. Keep the services running and open ChatGPT. Tags appear below supported answers; click a tag for a short explanation.',
    privacy:'Your answer goes to your own local service, not this website or a training database. Keep your token private. Do not paste it into a public report.',
    stop:'make down ENV_FILE="$HOME/.config/aitrust-id/runtime.env"'};
}
export function usageHTML(tag,esc) {
  const use=usage(tag);
  return `<section data-tag-usage><h2>${use.available?'Use this tag':'What you can do'}</h2><p>${esc(use.available?use.summary:use.next)}</p>${use.available
    ? `${use.phone ? `<p class="mt-2"><a href="/#person/PS">Check on this device</a></p><p>${esc(use.phone)}</p><h3 class="mt-3 font-semibold">Developer local service (optional)</h3>` : ''}<p class="mt-2 text-sm text-muted">${esc(use.prerequisites)}</p><p class="mt-3"><a href="${sourceDownload}">Download source</a> · <a href="${quickstart}">Full setup guide</a></p><ol class="mt-3 list-decimal space-y-3 pl-5">${use.steps.map(step=>`<li><h3 class="font-semibold">${esc(step.title)}</h3><p>${esc(step.body)}</p><pre class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(step.command)}</code></pre></li>`).join('')}</ol><p class="mt-3">${esc(use.next)}</p><p class="mt-3">${esc(use.browser)}</p><p class="mt-3">${esc(use.privacy)}</p><h3 class="mt-3 font-semibold">Stop the checker</h3><pre class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(use.stop)}</code></pre>`
    : `${tag.today?`<p data-tag-today class="mt-3">${esc(tag.today)}</p>`:''}${tag.id==='audit'?'<p class="mt-3"><a href="/#person/PS">Try PS exports</a></p>':''}`}</section>`;
}
