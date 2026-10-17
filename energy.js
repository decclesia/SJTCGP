'use strict';
(() => {
  const markers = window.SJTCG_ENERGY_MARKERS || [];
  const grid = document.querySelector('#energyGrid');
  const search = document.querySelector('#energySearch');
  const dialog = document.querySelector('#energyDialog');
  const preview = document.querySelector('#energyPreview');
  const imageUrl = marker => marker.image + '?v=' + marker.imageVersion;
  function open(marker) {
    document.querySelector('#energyTitle').textContent = marker.name;
    preview.src = imageUrl(marker);
    preview.alt = marker.name;
    document.querySelector('#energyFull').href = imageUrl(marker);
    dialog.showModal();
  }
  function render() {
    const query = search.value.trim().toLowerCase();
    const visible = markers.filter(marker => (marker.set+' '+marker.name).toLowerCase().includes(query));
    grid.replaceChildren(...visible.map(marker => {
      const button = document.createElement('button');
      button.type = 'button';button.className = 'marker';
      const img = document.createElement('img');img.src = imageUrl(marker);img.alt = marker.name;img.loading = 'lazy';
      const title = document.createElement('strong');title.textContent = marker.set;
      const caption = document.createElement('span');caption.textContent = 'Energy Marker';
      button.append(img,title,caption);button.addEventListener('click',()=>open(marker));return button;
    }));
    document.querySelector('#energyCount').textContent = `${visible.length} of ${markers.length} markers`;
    document.querySelector('#energyEmpty').hidden = visible.length > 0;
  }
  search.addEventListener('input',render);
  dialog.querySelector('.close').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target===dialog){const box=dialog.getBoundingClientRect();if(event.clientX<box.left||event.clientX>box.right||event.clientY<box.top||event.clientY>box.bottom)dialog.close();}});
  render();
})();
