// Supported Cloudflare static-header subset for owned verification servers.
'use strict';
function parseHeaders(text){
 const rules=[];let current;
 for(const line of text.split('\n')){
  if(!line.trim()||line.trimStart().startsWith('#'))continue;
  if(!/^\s/.test(line)){
   if(!/^\/[A-Za-z0-9/_.-]*\*?$/.test(line))throw Error('Unsupported static-header route');
   current={route:line,headers:{}};rules.push(current);continue;
  }
  if(!current)throw Error('Header lacks route');
  const match=/^\s+([A-Za-z0-9-]+):\s*(\S[^\r\n]*)$/.exec(line);
  if(!match)throw Error('Invalid static header');
  const key=match[1].toLowerCase();if(Object.hasOwn(current.headers,key))throw Error('Duplicate static header');current.headers[key]=match[2];
 }
 if(!rules.length)throw Error('Empty static-header rules');return rules;
}
function headersFor(rules,route){
 const result={};for(const rule of rules){const match=rule.route.endsWith('*')?route.startsWith(rule.route.slice(0,-1)):route===rule.route;if(match)Object.assign(result,rule.headers);}return result;
}
module.exports={parseHeaders,headersFor};
