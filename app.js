/* Saved result playback only. No model loading or inference in the browser. */
(() => {
  'use strict';
  const data = window.REVERB_DEMO;
  const RAW = 'raw-clap', OURS = 'reverbalign-512-v1';
  const metrics = [
    ['rt60_s', 'RT60', 's', 'Reverberation time'],
    ['c50_db', 'C50', 'dB', 'Speech clarity'],
    ['drr_db', 'DRR', 'dB', 'Direct-to-reverberant ratio'],
    ['edt_s', 'EDT', 's', 'Early decay time']
  ];
  const tracks = [
    ['dry', 'Dry speech', 'INPUT', 'Original speech, before reverb'],
    [RAW, 'Raw CLAP', 'BASELINE', 'FDN · final 300 updates'],
    [OURS, 'ReverbAlign', '512-v1', 'FDN · final 300 updates'],
    ['reference', 'Reference', 'MEASURED RIR', 'Evaluation reference only']
  ];
  const esc = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  const pct = value => (100 * Number(value)).toFixed(1) + '%';
  const joint = (model, n) => data.joint.find(r => r.model === model && Number(r.matched) === n);
  const agreement = (model, n) => Number(joint(model, n).at_least_fraction);
  const inRegion = (ex, model, metric) => {
    const bucket = value => data.edges[metric].filter(edge => value >= edge).length;
    return bucket(ex.values[model][metric]) === bucket(ex.values.reference[metric]);
  };
  if (!data) {
    document.getElementById('examples').textContent = 'Saved demo data could not be loaded. Keep the data folder next to index.html.';
    return;
  }
  document.getElementById('total-count').textContent = data.examples.length;
  document.getElementById('case-count').textContent = `${data.examples.length} examples`;
  const exampleHTML = ex => `
    <article class="example" id="${esc(ex.job)}" data-room="${esc(ex.room)}" aria-labelledby="title-${esc(ex.job)}">
      <div class="case-head"><div class="case-heading"><span class="case-number">${String(ex.number).padStart(2,'0')}</span><h3 id="title-${esc(ex.job)}">${esc(ex.title)}</h3><span class="case-subtitle">Speaker ${esc(ex.speaker)} · ${esc(ex.speech_id.split('/').pop())} · RT60 ${ex.values.reference.rt60_s.toFixed(2)} s</span></div><a class="case-id" href="#${esc(ex.job)}">${esc(ex.job)}</a></div>
      <div class="caption"><blockquote><span class="caption-label">Caption</span>${esc(ex.caption)}</blockquote></div>
      <div class="tracks">${tracks.map(([key, name, tag]) => `<div class="track ${key === OURS ? 'ours' : ''}"><div class="track-name"><span>${name}</span><span class="track-tag">${tag} · <a href="${esc(ex.audio[key].path)}" target="_blank" rel="noopener" aria-label="Open ${esc(name)} WAV — ${esc(ex.job)}">WAV</a></span></div><audio controls preload="metadata" data-case="${esc(ex.job)}" data-track="${key}" aria-label="${esc(name)} — ${esc(ex.title)} — ${esc(ex.job)}" src="${esc(ex.audio[key].path)}"><a href="${esc(ex.audio[key].path)}">Download ${name} WAV</a></audio><p class="audio-error" role="alert" hidden>Audio could not load. <a href="${esc(ex.audio[key].path)}">Open WAV</a></p></div>`).join('')}</div>
      <details class="case-details"><summary>Metrics <span>Regions: Raw ${ex.matches[RAW]}/4 · ReverbAlign ${ex.matches[OURS]}/4</span></summary><div class="table-scroll"><table class="case-metrics"><caption class="case-footnote">RIR attributes for ${esc(ex.job)}. ✓ = inside the target caption interval.</caption><thead><tr><th scope="col">Attribute</th><th scope="col">Reference</th><th scope="col">Raw CLAP</th><th scope="col">ReverbAlign</th></tr></thead><tbody>${metrics.map(([metric, label, unit]) => `<tr><th scope="row">${label} (${unit})</th><td>${ex.values.reference[metric].toFixed(3)}</td>${[RAW, OURS].map(m => `<td class="${inRegion(ex,m,metric)?'in-region':'miss'}">${ex.values[m][metric].toFixed(3)} <span aria-label="${inRegion(ex,m,metric)?'inside target region':'outside target region'}">${inRegion(ex,m,metric)?'✓':'·'}</span></td>`).join('')}</tr>`).join('')}</tbody></table></div><p class="case-footnote">RIR: ${esc(ex.rir_id)}<br>Utterance: ${esc(ex.speech_id)} · Shared listening gain: ${ex.common_listening_gain.toFixed(5)}<br>All test RIRs included; one matched utterance per RIR. <a href="data/manifest.json">Full provenance ↗</a></p></details>
    </article>`;
  document.getElementById('summary-body').innerHTML = metrics.map(([metric,label,unit,description]) => {
    const rows = [RAW, OURS].map(m => data.summary.find(r => r.model === m && r.metric === metric));
    return `<tr><th scope="row">${label}<span class="unit">${description} · ${unit}</span></th><td>${Number(rows[0].mae).toFixed(3)}</td><td class="ours">${Number(rows[1].mae).toFixed(3)}</td><td>${pct(rows[0].bucket_accuracy)}</td><td class="ours">${pct(rows[1].bucket_accuracy)}</td></tr>`;
  }).join('');
  document.getElementById('joint-results').innerHTML = `At least three target regions matched: <strong>${pct(agreement(RAW,3))} → ${pct(agreement(OURS,3))}</strong>. All four: <strong>${pct(agreement(RAW,4))} → ${pct(agreement(OURS,4))}</strong> (Raw CLAP → ReverbAlign).`;
  document.getElementById('bucket-table').innerHTML = `<table><thead><tr><th scope="col">Attribute</th><th scope="col">Levels</th><th scope="col">Training quantile cut points</th></tr></thead><tbody>${metrics.map(([metric,label,unit]) => `<tr><th scope="row">${label} (${unit})</th><td>${data.edges[metric].length+1}</td><td>${data.edges[metric].map(v=>v.toFixed(3)).join(', ')}</td></tr>`).join('')}</tbody></table>`;
  const filter = document.getElementById('room-filter');
  let selectedRoom = 'all';
  const rooms = new Map(data.examples.map(ex=>[ex.room,ex.title]));
  for (const [room,title] of rooms) {
    const button = document.createElement('button');
    button.type='button'; button.dataset.room=room; button.textContent=title;
    button.setAttribute('aria-pressed','false'); filter.append(button);
  }
  const pageSize = 5;
  const targetIndex = data.examples.findIndex(ex=>ex.job===location.hash.slice(1));
  let page = targetIndex>=0 ? Math.floor(targetIndex/pageSize) : 0;
  const previousButton = document.getElementById('previous-page');
  const nextButton = document.getElementById('next-page');
  function renderPage(){
    document.querySelectorAll('audio').forEach(audio=>audio.pause());
    active=null;
    filter.querySelectorAll('button').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.room===selectedRoom)));
    const selected=data.examples.filter(ex=>selectedRoom==='all'||selectedRoom===ex.room);
    const pages=Math.ceil(selected.length/pageSize);
    page=Math.max(0,Math.min(page,pages-1));
    const start=page*pageSize;
    document.getElementById('examples').innerHTML=selected.slice(start,start+pageSize).map(exampleHTML).join('');
    document.getElementById('case-count').textContent=`${selected.length} examples`;
    document.getElementById('page-label').textContent=`${start+1}–${Math.min(start+pageSize,selected.length)} of ${selected.length}`;
    previousButton.disabled=page===0;
    nextButton.disabled=page===pages-1;
    wirePlayers();
  }
  filter.addEventListener('click',event=>{
    const button=event.target.closest('button[data-room]');
    if(!button||!filter.contains(button)||selectedRoom===button.dataset.room) return;
    selectedRoom=button.dataset.room; page=0; renderPage();
  });
  previousButton.addEventListener('click',()=>{page--;renderPage();});
  nextButton.addEventListener('click',()=>{page++;renderPage();});
  window.addEventListener('hashchange',()=>{
    const index=data.examples.findIndex(ex=>ex.job===location.hash.slice(1));
    if(index<0) return;
    selectedRoom='all';page=Math.floor(index/pageSize);renderPage();
    document.getElementById(data.examples[index].job).scrollIntoView();
  });
  let active = null;
  const pendingPosition = new WeakMap();
  function wirePlayers(){
  document.querySelectorAll('audio').forEach(audio => {
    audio.addEventListener('play', () => {
      const previous=active;
      const transfer=previous && previous!==audio && previous.dataset.case===audio.dataset.case && !previous.paused && !previous.ended && document.getElementById('sync-position').checked;
      const time=transfer ? previous.currentTime : null;
      document.querySelectorAll('audio').forEach(other => {if(other!==audio) other.pause();});
      if(time!==null) pendingPosition.set(audio,time);
      active=audio; audio.closest('.track').classList.add('playing');
    });
    // Apply after native controls have started playback, including WebKit's first-play setup.
    audio.addEventListener('playing',()=>{
      if(!pendingPosition.has(audio)) return;
      const time=pendingPosition.get(audio); pendingPosition.delete(audio);
      audio.currentTime=Math.min(time,Number.isFinite(audio.duration)?Math.max(0,audio.duration-.05):time);
    });
    ['pause','ended'].forEach(event=>audio.addEventListener(event,()=>audio.closest('.track').classList.remove('playing')));
    audio.addEventListener('loadedmetadata',()=>{audio.closest('.track').querySelector('.audio-error').hidden=true;});
    audio.addEventListener('error',()=>{audio.closest('.track').querySelector('.audio-error').hidden=false;});
  });
  }
  renderPage();
})();
