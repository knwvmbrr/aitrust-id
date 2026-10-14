// One use contract feeds the interactive modal, static reference and no-JS page.
export const repository = 'https://github.com/knwvmbrr/aitrust-id';
export const sourceDownload = repository + '/archive/refs/heads/main.zip';
export const quickstart = repository + '/blob/main/docs/open-validation-path.md';
const setup = [
  {title:'Get the source',body:'Download and unzip the source, then open its folder. Or use Git:',command:'git clone https://github.com/knwvmbrr/aitrust-id.git\ncd aitrust-id'},
  {title:'Start your own checker',body:'On Linux with Python 3.12+ and a working Podman engine, run this from the source folder. It creates a private installation and checks that it works:',command:'python3 scripts/setup-local.py --engine podman'},
];
const localState='LOCAL_STATE="$HOME/.config/aitrust-id/local-stack"';
const checkStep=tag=>tag.id==='PII_REDACTED'
  ? {title:'Review a draft before sharing',body:'Save text as draft.txt. This optional privacy check uses your local redactor and does not depend on PS. It does not edit or send the draft:',command:localState+'\n"$LOCAL_STATE/checker/bin/python" scripts/aitrust.py privacy draft.txt --env-file "$LOCAL_STATE/runtime.env"'}
  : {title:'Check an answer',body:'Save an answer as response.txt, then run:',command:localState+'\n"$LOCAL_STATE/checker/bin/python" scripts/aitrust.py check response.txt --env-file "$LOCAL_STATE/runtime.env"'};

export function usage(tag) {
  const available = ['PS','PII_REDACTED'].includes(tag.id);
  const orgNext={
    fleet:'Review the extension permissions in the public source, then tell us how your team manages installs and updates.',
    host:'Help define which files an agent may read, how it asks permission, and how you pause or remove it.',
    audit:'Try PS on this device and download its result summary. A detailed record is a separate, optional export. “Download details” in this panel saves the offering description, not a checked answer.',
    sso:'Compare the proposed configure, view, review and export permissions with your team’s groups. Tell us what needs to change.',
    support:'Use Report an issue for a defect. For a vulnerability, choose the private security channel; do not post sensitive details publicly.',
    proprietary:'Open the local practice guide in How it works. Read its invented policy before checking the example; share requirements without confidential documents.'};
  const tagNext={
    NF:'Suggest a claim and the reference passage that supports it.',
    FI:'Share a claim and a reference passage that disagree.',
    HP:'Suggest a claim that needs checking, with a source that explains why.',
    MT:'Share an example of urgent wording and the context that makes it helpful or pressuring.',
    IV:'Help define what a reviewer should record, and how to correct or withdraw a review.',
    FA:'Suggest a generation record that could show where an item came from.',
    PA:'Suggest a consented example of an AI draft and the edits made afterward.',
    UNK:'Share a case where a checker should say it does not have enough evidence.',
    PII_OUTBOUND:'Try the manual draft privacy check in the PII instructions. A browser reminder or send interception is still planned.',
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
    : 'Check a draft with your own local redactor before you share it. Review the result and make any edits yourself. This is a local-service preview, separate from the website’s on-device PS checker.',
    prerequisites:'Developer preview: Linux, Python 3.12+ and an installed, working Podman engine. First setup downloads pinned dependencies. Read the full guide for private build-network options and the older manual Docker Compose path. This command does not install an engine; no Chrome Web Store release is offered.',
    standalone:tag.id==='PS' ? {description:'Prefer Terminal? Download the source, save an answer as response.txt, and run the command below with Python 3.12+. No local service or privacy checker is needed. Up to 20,000 characters. No redaction is performed.',command:'python3 scripts/check-ps.py response.txt'} : null,
    phone:tag.id==='PS' ? 'Open aitrustid.com/#person/PS and choose Check on this device. Optional: save the public app for offline use and add it to your home screen. No answer is uploaded; the phone preview performs no redaction.' : null,
    steps:[...setup,checkStep(tag)],next:tag.id==='PS'
      ? 'A PS finding asks you to review a command pattern. No finding means no supported pattern was found, not “safe.” If a check cannot finish, it says so.'
      : 'A finding means supported detections were masked during this local check. Your original draft is unchanged. No finding does not mean all private details are absent.',
    browser:'Optional Chrome tags: follow docs/gateway-authentication.md in the downloaded repository to set up gateway signing. Open chrome://extensions, enable Developer mode, choose Load unpacked and select the extension folder. In its settings, choose your gateway public-key JSON, confirm its fingerprint separately and enter your local token. Turn on Enable checks on ChatGPT when ready. Keep your services running. Tags appear below supported answers; click for a short explanation. Unsigned or altered results stay unavailable. Pause or reset at any time.',
    privacy:'Your answer goes to your own local service, not this website or a training database. Keep your token private. Do not paste it into a public report.',
    stop:'python3 scripts/setup-local.py --engine podman --stop'};
}
export function usageHTML(tag,esc) {
  const use=usage(tag);
  return `<section data-tag-usage><h2>${use.available?'Use this tag':'What you can do'}</h2><p>${esc(use.available?use.summary:use.next)}</p>${use.available
    ? `${use.standalone ? `<h3 class="mt-3 font-semibold">PS in Terminal</h3><p>${esc(use.standalone.description)}</p><p><a href="${sourceDownload}">Download source</a></p><pre tabindex="0" class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(use.standalone.command)}</code></pre>` : ''}${use.phone ? `<p class="mt-2"><a href="/#person/PS">Check on this device</a></p><p>${esc(use.phone)}</p><h3 class="mt-3 font-semibold">Developer local service (optional)</h3>` : ''}<p class="mt-2 text-sm text-muted">${esc(use.prerequisites)}</p><p class="mt-3"><a href="${sourceDownload}">Download source</a> · <a href="${quickstart}">Full setup guide</a></p><ol class="mt-3 list-decimal space-y-3 pl-5">${use.steps.map(step=>`<li><h3 class="font-semibold">${esc(step.title)}</h3><p>${esc(step.body)}</p><pre tabindex="0" class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(step.command)}</code></pre></li>`).join('')}</ol><p class="mt-3">${esc(use.next)}</p><p class="mt-3">${esc(use.browser)}</p><p class="mt-3">${esc(use.privacy)}</p><p class="mt-3"><a href="${repository}/blob/main/docs/assertion-replay.md">Repeat a saved local-service check</a>. This compares your saved findings against the same method; it does not send research data to us.</p><h3 class="mt-3 font-semibold">Stop the checker</h3><pre tabindex="0" class="my-2 overflow-x-auto rounded-lg border border-line bg-canvas p-3 text-sm"><code>${esc(use.stop)}</code></pre>`
    : `${tag.today?`<p data-tag-today class="mt-3">${esc(tag.today)}</p>`:''}${tag.id==='audit'?'<p class="mt-3"><a href="/#person/PS">Try PS exports</a></p>':''}`}</section>`;
}
