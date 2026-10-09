export const origin='https://aitrustid.com';
export const siteTitle='AI Trust ID — Explainable Tags and Evidence';
export const siteDescription='Explore explainable tags and evidence for AI output. Try the free, open-source command-risk checker on your phone or computer. Each tag has its own validation gate before release.';
export const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const tagPath=tag=>'/tags/'+tag.id.toLowerCase().replaceAll('_','-')+'/';
export const tagDescription=tag=>`${tag.code} — ${tag.name}. ${tag.proposed?'Research proposal':'Development preview'}. Read its job, method, evidence, limits and validation gate.`;
export const website={'@type':'WebSite','@id':origin+'/#website',url:origin+'/',name:'AI Trust ID',description:siteDescription,inLanguage:'en'};
export function metadata({title=siteTitle,description=siteDescription,path='/',schema}) {
  const url=origin+path;
  const data=schema||{'@context':'https://schema.org','@graph':[website,{'@type':'CollectionPage','@id':url+'#page',url,name:title,description,inLanguage:'en',isPartOf:{'@id':website['@id']}}]};
  const json=JSON.stringify(data).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
  return `<title>${escapeHTML(title)}</title>
<meta name="description" content="${escapeHTML(description)}"/>
<meta name="robots" content="index,follow,max-image-preview:large"/>
<link rel="canonical" href="${escapeHTML(url)}"/>
<meta property="og:type" content="website"/>
<meta property="og:site_name" content="AI Trust ID"/>
<meta property="og:title" content="${escapeHTML(title)}"/>
<meta property="og:description" content="${escapeHTML(description)}"/>
<meta property="og:url" content="${escapeHTML(url)}"/>
<meta property="og:image" content="${origin}/share-card.png"/>
<meta property="og:image:width" content="1200"/>
<meta property="og:image:height" content="630"/>
<meta property="og:image:alt" content="AI Trust ID tag logo. Explainable tags and evidence. Development preview."/>
<meta name="twitter:card" content="summary_large_image"/>
<meta name="twitter:title" content="${escapeHTML(title)}"/>
<meta name="twitter:description" content="${escapeHTML(description)}"/>
<meta name="twitter:image" content="${origin}/share-card.png"/>
<meta name="twitter:image:alt" content="AI Trust ID tag logo. Explainable tags and evidence. Development preview."/>
<script type="application/ld+json">${json}</script>`;
}
