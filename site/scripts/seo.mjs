import {presentation} from '../src/presentation.js';
export const origin='https://aitrustid.com';
export const siteTitle='AI Trust ID — Free, Open-Source AI Output Checks';
export const siteDescription='Check AI answers for supported command-risk patterns with the free PS preview. Runs on your phone or computer. Explore each tag’s evidence, limits and validation.';
export const escapeHTML=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const tagPath=tag=>'/tags/'+tag.id.toLowerCase().replaceAll('_','-')+'/';
// Search and social summaries use the same purpose and availability as the page.
// `proposed` alone cannot distinguish a working local tool from a planned tag.
export function tagDescription(tag) {
  const intro=presentation(tag);
  return `${tag.code} — ${tag.name}. ${intro.summary} ${intro.availability}`;
}
export const website={'@type':'WebSite','@id':origin+'/#website',url:origin+'/',name:'AI Trust ID',description:siteDescription,inLanguage:'en'};
export function metadata({title=siteTitle,description=siteDescription,path='/',schema}) {
  const url=origin+path;
  const data=schema||{'@context':'https://schema.org','@graph':[website,{'@type':path==='/'||path==='/tags/'?'CollectionPage':'WebPage','@id':url+'#page',url,name:title,description,inLanguage:'en',isPartOf:{'@id':website['@id']}}]};
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
