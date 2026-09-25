function toggleSidebar(){
  const s=document.getElementById('sidebar');
  if(s) s.classList.toggle('open');
}
setTimeout(()=>document.querySelectorAll('.flash').forEach(x=>x.classList.add('fade')), 4500);
