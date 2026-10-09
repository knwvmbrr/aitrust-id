const input=document.querySelector('#token'),status=document.querySelector('#status');
document.querySelector('form').addEventListener('submit',async event=>{
 event.preventDefault();if(input.value==='change-me'||input.value.length<16){input.setAttribute('aria-invalid','true');status.textContent='Enter a generated token of at least 16 characters.';return;}
 try{await chrome.storage.local.set({token:input.value});input.value='';input.removeAttribute('aria-invalid');status.textContent='Token saved locally.';}catch{status.textContent='Token could not be saved.';}
});
document.querySelector('#clear').addEventListener('click',async()=>{try{await chrome.storage.local.remove('token');input.value='';status.textContent='Token removed.';}catch{status.textContent='Token could not be removed.';}});
