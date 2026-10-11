#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path');
const statement=require('../protocol/conformance-statement.cjs'),{publish}=require('./atomic-output.cjs');
function main(args){
 const [command,inputFile,outputFile]=args;
 if(command==='help'||!command){console.log('AI Trust ID · engineering self-declaration\ncreate <input.json> <new-statement.json>\ncheck <input.json> <statement.json>\n\nEvidence paths are relative to the input file. Nothing is uploaded. This is not certification, a trademark license, independent validation or proof that declared test results are true. See docs/mark-usage.md.');return 0;}
 if(args.length!==3||!['create','check'].includes(command))throw Error('Unsupported statement command');
 const input=statement.load(inputFile),base=path.dirname(path.resolve(inputFile));
 if(command==='check'){console.log(JSON.stringify(statement.verify(input,base,statement.load(outputFile))));return 0;}
 const result=statement.declaration(input,base),file=path.resolve(outputFile);
 if(fs.realpathSync(path.dirname(file))!==path.dirname(file))throw Error('Symlink output directory refused');
 publish(file,Buffer.from(JSON.stringify(result,null,2)+'\n'));console.log('Local self-declaration created. Review before sharing; no certification or mark authorization was granted.');return 0;
}
if(require.main===module){try{process.exitCode=main(process.argv.slice(2));}catch(_){console.error('Statement refused: invalid fields, unavailable evidence, changed bytes or unsafe destination. No approval was granted.');process.exitCode=2;}}
module.exports={main};
