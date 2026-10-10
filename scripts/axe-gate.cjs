// Automated severity gate only; does not claim human accessibility conformance.
function assess(results){
 if(!results||!Array.isArray(results.violations))throw Error('Missing axe results');
 const serious=results.violations.filter(v=>['serious','critical'].includes(v.impact));
 for(const v of results.violations)if(typeof v.id!=='string'||!Array.isArray(v.nodes)||!['minor','moderate','serious','critical',null].includes(v.impact))throw Error('Invalid axe violation');
 return {pass:serious.length===0,serious:serious.filter(v=>v.impact==='serious').length,critical:serious.filter(v=>v.impact==='critical').length,failures:serious.map(v=>({id:v.id,impact:v.impact,targets:v.nodes.map(n=>n.target)})),human_conformance:false};
}
module.exports={assess};
