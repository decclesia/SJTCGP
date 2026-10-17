'use strict';
(() => {
  const kindOrder = {energy: 0, guard: 1, sj: 2};
  const typeNames = {energy: 'Energy Marker', guard: 'Guard Trigger', sj: 'SJ Marker'};
  const setCompare = (a,b) => (a==='GENERIC')-(b==='GENERIC') || a.localeCompare(b,undefined,{numeric:true});
  const markers = [...(window.SJTCG_ACCESSORIES || [])].sort((a,b)=>setCompare(a.set,b.set)||kindOrder[a.kind]-kindOrder[b.kind]||a.id.localeCompare(b.id,undefined,{numeric:true}));
  const grid = document.querySelector('#energyGrid');
  const search = document.querySelector('#energySearch');
  const setFilter = document.querySelector('#setFilter');
  const typeFilter = document.querySelector('#typeFilter');
  const dialog = document.querySelector('#energyDialog');
  const preview = document.querySelector('#energyPreview');
  const imageUrl = marker => marker.image + '?v=' + marker.imageVersion;
  const sets = [...new Set(markers.map(marker=>marker.set))].sort(setCompare);
  for (const set of sets) {
    const option = document.createElement('option');option.value=set;option.textContent=set==='GENERIC'?'Generic':set;setFilter.append(option);
  }
  const params = new URLSearchParams(location.search);
  search.value=params.get('q')||'';
  setFilter.value=sets.includes(params.get('set'))?params.get('set'):'';
  typeFilter.value=Object.hasOwn(typeNames,params.get('type'))?params.get('type'):'';
  function open(marker) {
    document.querySelector('#energyTitle').textContent = marker.name;
    document.querySelector('#energyMeta').textContent = `Set: ${marker.set} · ${typeNames[marker.kind]} · ${marker.id.replace(/^TOKEN-/, '')}`;
    preview.src = imageUrl(marker);
    preview.alt = marker.name;
    document.querySelector('#energyFull').href = imageUrl(marker);
    dialog.showModal();
  }
  function card(marker) {
      const button = document.createElement('button');
      button.type = 'button';button.className = 'marker';button.dataset.id=marker.id;
      button.setAttribute('aria-label',`Preview ${marker.name}`);
      const img = document.createElement('img');img.src = imageUrl(marker);img.alt = marker.name;img.loading = 'lazy';
      const title = document.createElement('strong');title.textContent = typeNames[marker.kind];
      const caption = document.createElement('span');caption.textContent = marker.kind==='energy'?marker.set:marker.id.replace(/^TOKEN-/,'');
      button.append(img,title,caption);button.addEventListener('click',()=>open(marker));return button;
  }
  function render() {
    const query = search.value.trim().toLowerCase();
    const visible = markers.filter(marker => (!setFilter.value||marker.set===setFilter.value)&&(!typeFilter.value||marker.kind===typeFilter.value)&&(marker.set+' '+marker.name+' '+marker.id+' '+typeNames[marker.kind]).toLowerCase().includes(query));
    const groups=new Map();
    for(const marker of visible){if(!groups.has(marker.set))groups.set(marker.set,[]);groups.get(marker.set).push(marker);}
    grid.replaceChildren(...[...groups].map(([set,items])=>{
      const section=document.createElement('section');section.className='set-group';section.dataset.set=set;
      const heading=document.createElement('h2');heading.textContent=set==='GENERIC'?'Generic':set;
      const count=document.createElement('span');count.textContent=`${items.length} ${items.length===1?'artwork':'artworks'}`;heading.append(count);
      const cards=document.createElement('div');cards.className='energy-grid';cards.append(...items.map(card));section.append(heading,cards);return section;
    }));
    document.querySelector('#energyCount').textContent = `${visible.length} of ${markers.length} accessories · ${groups.size} Sets · ordered by Set`;
    document.querySelector('#energyEmpty').hidden = visible.length > 0;
    const next=new URLSearchParams();if(search.value)next.set('q',search.value);if(setFilter.value)next.set('set',setFilter.value);if(typeFilter.value)next.set('type',typeFilter.value);
    history.replaceState(null,'',location.pathname+(next.size?'?'+next.toString():''));
  }
  search.addEventListener('input',render);
  setFilter.addEventListener('change',render);typeFilter.addEventListener('change',render);
  document.querySelector('#resetFilters').addEventListener('click',()=>{search.value='';setFilter.value='';typeFilter.value='';render();});
  dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}});
  render();
})();
