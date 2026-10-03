// Run in a Chrome tab that has an Instagram post page open (https://www.instagram.com/vprwre/p/CODE/).
// Works signed out. Reads the post data Instagram embeds in the page (no timers, so it also works
// in a background tab), downloads every slide at 1080px, and stores everything in this browser's
// IndexedDB ("vprwre-scrape") under CODE/slide-NN.jpg and CODE/meta.json.
// Returns a short JSON summary. Never returns image URLs (they carry signed query strings).
await (async () => {
  const code = location.pathname.split('/p/')[1].replace(/\/.*/, '');
  const txt = [...document.querySelectorAll('script')].map(s => s.textContent)
    .find(t => t.includes('"code":"' + code + '"') && (t.includes('carousel_media') || t.includes('image_versions2')));
  if (!txt) return JSON.stringify({ code, err: 'post data not found in page; reload and retry' });
  let found = null;
  const walk = (o, d = 0) => {
    if (found || !o || typeof o !== 'object' || d > 60) return;
    if (o.code === code && (o.carousel_media || o.image_versions2)) { found = o; return; }
    for (const k in o) walk(o[k], d + 1);
  };
  walk(JSON.parse(txt));
  if (!found) return JSON.stringify({ code, err: 'post object not found' });
  const media = found.carousel_media || [found];
  const pick = m => {
    const c = m.image_versions2?.candidates || [];
    const p = c.find(x => { try { const s = new URL(x.url).searchParams.get('stp') || ''; return s.includes('p1080x1080') && !s.startsWith('c0'); } catch (e) { return false; } });
    return (p || c[0])?.url;
  };
  const db = await new Promise((res, rej) => { const r = indexedDB.open('vprwre-scrape', 1); r.onupgradeneeded = () => r.result.createObjectStore('files'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const put = (key, val) => new Promise((res, rej) => { const tx = db.transaction('files', 'readwrite'); tx.objectStore('files').put(val, key); tx.oncomplete = res; tx.onerror = () => rej(tx.error); });
  const sizes = await Promise.all(media.map(async (m, i) => {
    try { const b = await (await fetch(pick(m))).blob(); await put(`${code}/slide-${String(i + 1).padStart(2, '0')}.jpg`, b); return b.size; }
    catch (e) { return -1; }
  }));
  const meta = {
    code, url: `https://www.instagram.com/vprwre/p/${code}/`, taken_at: found.taken_at,
    caption: found.caption?.text || '',
    slides: media.map((m, i) => ({ file: `slide-${String(i + 1).padStart(2, '0')}.jpg`, w: m.original_width, h: m.original_height, alt: m.accessibility_caption || '' })),
  };
  await put(`${code}/meta.json`, new Blob([JSON.stringify(meta, null, 2)], { type: 'application/json' }));
  return JSON.stringify({ code, slides: media.length, failed: sizes.filter(s => s < 0).length, kb: Math.round(sizes.reduce((a, b) => a + Math.max(b, 0), 0) / 1024), caption_start: meta.caption.slice(0, 60) });
})()
