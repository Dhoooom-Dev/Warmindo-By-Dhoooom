// WARMINDO BY DHOO_CO — © 2026 dhoo_co | Original source project

const $=s=>document.querySelector(s);
function flashLocal(msg){alert(msg)}
async function postJSON(url,data){
  const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(data)});
  return r.json();
}
