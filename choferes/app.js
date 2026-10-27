'use strict';
const $=s=>document.querySelector(s);
let account=null, photos=[], recording=null, busy=false;
const status=m=>$('#status').textContent=m;
async function render(){
 const rows=(await Cola.op('reportes','getAll')).filter(r=>r.usuario_id===(account&&account.usuario_id)).reverse();
 $('#pending').replaceChildren();
 for(const r of rows){
   const a=document.createElement('article'),h=document.createElement('strong'),p=document.createElement('p');
   h.textContent=r.enviado?'Enviado al taller':'Pendiente de envío';p.textContent=r.descripcion;
   a.append(h,p);const small=document.createElement('small');small.textContent=new Date(r.ocurrido_en).toLocaleString()+(r.error?' · '+r.error:'');a.append(small);$('#pending').append(a);
 }
}
async function context(){
 try{
   const r=await fetch('/api/reportes-chofer?op=contexto',{credentials:'same-origin',cache:'no-store',redirect:'error'});
   if(!r.ok){const e=new Error('Sesión no iniciada o sin permiso de choferes.');e.auth=true;throw e;}
   account=await r.json();await Cola.op('config','put',account,'cuenta');
 }catch(e){
   if(e.auth){account=null;status(e.message);return;}
   account=await Cola.op('config','get','cuenta');
   if(!account){status('Para usar la app sin señal se requiere un primer ingreso con conexión.');return;}
   status('Sin conexión verificada. Los reportes quedarán pendientes para '+account.nombre+'.');
 }
 $('#session').textContent='Cuenta: '+account.nombre;
 $('#unit').replaceChildren(new Option('Elegí una unidad',''));
 for(const u of account.unidades)$('#unit').add(new Option(u.patente+(u.interno?' · '+u.interno:''),u.id));
 $('#save').disabled=false;await render();
}
async function sync(){
 if(busy||!navigator.onLine)return;
 busy=true;$('#sync').disabled=true;
 try{await Cola.sync();status('Envíos verificados. Los reportes confirmados figuran como enviados.');}
 catch(e){status((e instanceof TypeError?'No hay conexión con el servidor.':e.message)+' Los pendientes se conservan en este teléfono.');}
 finally{busy=false;$('#sync').disabled=false;await render();}
}
async function photo(file){
 if(file.size>25*1024*1024)throw Error('La foto supera los 25 MB.');
 const bitmap=await createImageBitmap(file),scale=Math.min(1,1600/Math.max(bitmap.width,bitmap.height));
 const c=document.createElement('canvas');c.width=Math.round(bitmap.width*scale);c.height=Math.round(bitmap.height*scale);
 c.getContext('2d').drawImage(bitmap,0,0,c.width,c.height);bitmap.close();
 const url=c.toDataURL('image/jpeg',.8),datos=url.split(',')[1];
 if(datos.length>2796200)throw Error('La foto sigue siendo demasiado grande. Usar una más pequeña.');
 return {mime:'image/jpeg',datos};
}
function previews(){
 $('#preview').replaceChildren();photos.forEach((p,i)=>{
   const box=document.createElement('div'),img=document.createElement('img'),b=document.createElement('button');
   img.src='data:'+p.mime+';base64,'+p.datos;img.alt='Foto adjunta '+(i+1);b.type='button';b.className='secondary';b.textContent='Quitar foto';b.onclick=()=>{photos.splice(i,1);previews();};box.append(img,b);$('#preview').append(box);
 });
}
let processing=false;
async function addPhotos(e){
 if(processing)return;processing=true;$('#save').disabled=true;
 try{
 const files=[...e.target.files];if(photos.length+files.length>3)throw Error('Máximo 3 fotos.');
 const converted=[];for(const f of files)converted.push(await photo(f));photos.push(...converted);previews();
 }catch(e){status(e.message);}finally{processing=false;e.target.value='';$('#save').disabled=!account;}
}
$('#photos').onchange=addPhotos;$('#camera').onchange=addPhotos;
$('#report').onsubmit=async e=>{
 e.preventDefault();if(!account||processing)return;$('#save').disabled=true;
 try{
 const item={id:crypto.randomUUID(),usuario_id:account.usuario_id,unidad_id:Number($('#unit').value),descripcion:$('#description').value.trim(),urgencia:$('#urgency').value,ocurrido_en:new Date().toISOString(),fotos:photos};
 if(!item.descripcion)throw Error('Falta la descripción de la falla.');
 await Cola.op('reportes','put',item);
 $('#report').reset();photos=[];previews();status('Reporte guardado en el teléfono. Pendiente de confirmación del taller.');await render();
 if('serviceWorker' in navigator){const reg=await navigator.serviceWorker.getRegistration('/choferes/');if(reg&&reg.sync)await reg.sync.register('reportes-chofer').catch(()=>{});}
 await sync();
 }catch(e){status('No se pudo completar: '+e.message);}finally{$('#save').disabled=false;}
};
$('#dictate').onclick=()=>{
 const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!Speech){status('Dictado no disponible en este equipo: usar el micrófono del teclado.');$('#description').focus();return;}
 if(recording){recording.stop();return;}
 recording=new Speech();recording.lang='es-AR';recording.interimResults=false;
 recording.onresult=e=>{$('#description').value=($('#description').value+' '+e.results[0][0].transcript).trim().slice(0,2000);};
 recording.onerror=()=>status('No se pudo dictar. Revisar el permiso del micrófono y la conexión, o usar el teclado.');
 recording.onend=()=>{recording=null;$('#dictate').textContent='Dictar por voz';};
 try{recording.start();$('#dictate').textContent='Detener dictado';}catch(e){recording=null;status(e.message);}
};
$('#sync').onclick=sync;window.addEventListener('online',sync);window.addEventListener('offline',()=>status('Sin conexión. La falla y las fotos se guardan igual.'));
document.addEventListener('visibilitychange',()=>{if(!document.hidden)sync();});
setInterval(()=>{if(!document.hidden)sync();},30000);
(async()=>{
 $('#save').disabled=true;
 // Si había una versión anterior instalada, al tomar el control la nueva se recarga una vez.
 if('serviceWorker' in navigator&&navigator.serviceWorker.controller){let una=false;navigator.serviceWorker.addEventListener('controllerchange',()=>{if(!una){una=true;location.reload();}});}
 if('serviceWorker' in navigator)await navigator.serviceWorker.register('/choferes/sw.js',{updateViaCache:'none'}).catch(()=>status('No se pudo preparar el uso sin conexión. Revisar la conexión y volver a abrir.'));
 await context();
 if(account&&navigator.onLine)await sync();
})().catch(e=>status('No se pudo abrir el almacenamiento del teléfono: '+e.message));
const URGENCIA={PUEDE_ESPERAR:'Puede esperar',OPERA_CON_RIESGO:'Opera con riesgo',UNIDAD_PARADA:'Unidad parada'};
const fecha=v=>v?new Date(v).toLocaleString('es-AR',{dateStyle:'short',timeStyle:'short'}):'';
function estadoReporte(r){
 if(r.estado==='DESESTIMADA')return['desestimada','Desestimado por el taller','Motivo: '+r.motivo];
 if(r.estado==='ORDEN_CREADA'){
   const n='Orden de trabajo N.º '+r.orden_numero;
   if(r.orden_estado==='cerrada')return['cerrada','Reparación terminada',n+' cerrada'+(r.orden_cierre?' el '+new Date(r.orden_cierre+'T12:00').toLocaleDateString('es-AR'):'')+'.'];
   if(r.orden_estado==='anulada')return['desestimada','Orden anulada',n+' anulada.'];
   return['orden','En reparación',n+' abierta.'];
 }
 return['pendiente','Recibido, pendiente de revisión','Sin decisión del taller.'];
}
$('#lookup').onsubmit=async e=>{
 e.preventDefault();const patente=$('#plate').value.trim();if(!patente)return;
 $('#lookup-btn').disabled=true;$('#lookup-status').textContent='Consultando…';$('#results').replaceChildren();
 try{
   const r=await fetch('/api/reportes-chofer?op=consultar&patente='+encodeURIComponent(patente),{credentials:'same-origin',cache:'no-store',redirect:'error'});
   const d=await r.json().catch(()=>({}));
   if(!r.ok)throw Error(d.error||(r.status===401||r.status===403?'Sesión no iniciada o sin permiso.':'No se pudo consultar.'));
   $('#lookup-status').textContent=d.reportes.length?d.reportes.length+' reporte(s) para '+d.patente+'.':'Sin reportes para '+d.patente+'.';
   for(const x of d.reportes){
     const [clase,titulo,detalle]=estadoReporte(x),a=document.createElement('article');a.className='estado '+clase;
     const h=document.createElement('h3');h.textContent=titulo;
     const desc=document.createElement('p');desc.className='description';desc.textContent=x.descripcion;
     const det=document.createElement('p');det.textContent=detalle;
     const s=document.createElement('small');s.textContent=[x.patente+(x.interno?' · '+x.interno:''),URGENCIA[x.urgencia]||x.urgencia,'Informado '+fecha(x.ocurrido_en),x.chofer].join(' · ');
     a.append(h,desc,det,s);$('#results').append(a);
   }
 }catch(err){$('#lookup-status').textContent=err instanceof TypeError?'Sin conexión con el servidor. La consulta requiere señal.':err.message;}
 finally{$('#lookup-btn').disabled=false;}
};
