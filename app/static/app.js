// Minimal JS: focus the palette, wire up keyboard shortcut, and show hint text.
(function(){
  const input = document.getElementById('palette-input');
  window.addEventListener('keydown', (e)=>{
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k'){
      e.preventDefault();
      input?.focus();
      input?.select();
    }
  });
  const hints = [
    'add task call Megan tomorrow 3pm',
    'new lead Sarah from Orbit Labs, email sarah@orbitlabs.com, budget 12k',
    'create invoice for Sarah 1200 for "Logo design"',
    'show tasks', 'show leads', 'show invoices'
  ];
  let ix = 0;
  const hintEl = document.getElementById('hint');
  setInterval(()=>{
    ix = (ix + 1) % hints.length;
    if (hintEl){ hintEl.textContent = hints[ix];}
  }, 4000);
})();
