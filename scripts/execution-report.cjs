// Public execution JSON only. Historical runs are exclusive; scratch is replaceable.
const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const ROOT=path.resolve(__dirname,'..');
function writeReport(target,record,root=ROOT){
 const text=JSON.stringify(record,(key,value)=>{if(typeof value==='number'&&!Number.isFinite(value))throw Error('Non-finite report value');return value;},2)+'\n';JSON.parse(text);
 root=path.resolve(root);const file=path.resolve(root,target),relative=path.relative(root,file);
 if(relative.startsWith('..'+path.sep)||path.isAbsolute(relative)||!['runs','output'].includes(relative.split(path.sep)[0])||path.extname(file)!=='.json')throw Error('Invalid report destination');
 let current=root;
 for(const part of relative.split(path.sep)){
  current=path.join(current,part);
  if(fs.existsSync(current)||(()=>{try{return fs.lstatSync(current).isSymbolicLink()}catch{return false}})()){
   if(fs.lstatSync(current).isSymbolicLink())throw Error('Report symlink refused');
  }
 }
 fs.mkdirSync(path.dirname(file),{recursive:true});
 const temporary=path.join(path.dirname(file),'.report-'+crypto.randomUUID());let fd;
 try{
  fd=fs.openSync(temporary,'wx',0o600);fs.writeFileSync(fd,text);fs.fsyncSync(fd);fs.closeSync(fd);fd=undefined;
  if(relative.split(path.sep)[0]==='runs'){fs.linkSync(temporary,file);fs.unlinkSync(temporary);}else fs.renameSync(temporary,file);
 }finally{if(fd!==undefined)fs.closeSync(fd);if(fs.existsSync(temporary))fs.unlinkSync(temporary);}
 return file;
}
module.exports={writeReport};
