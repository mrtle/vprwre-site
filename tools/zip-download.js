// Run in the same Chrome tab (instagram.com) after scrape-post.js has stored the posts.
// Prepend two lines before this file's contents when running it:
//   const CODES = ["ABC123", "DEF456"];        // post codes to package
//   const FILENAME = "vprwre-new-2026-10-03.zip";
// Builds one uncompressed zip (vprwre/<CODE>/meta.json + slides) from IndexedDB, saves it to the
// computer's Downloads folder, then deletes those entries from IndexedDB.
await (async () => {
  const db = await new Promise((res, rej) => { const r = indexedDB.open('vprwre-scrape', 1); r.onupgradeneeded = () => r.result.createObjectStore('files'); r.onsuccess = () => res(r.result); r.onerror = () => rej(r.error); });
  const all = await new Promise(res => { const st = db.transaction('files').objectStore('files'); const ks = st.getAllKeys(); ks.onsuccess = () => { const vs = st.getAll(); vs.onsuccess = () => res(ks.result.map((k, i) => [k, vs.result[i]])); }; });
  const files = all.filter(([k, v]) => v instanceof Blob && CODES.some(c => k.startsWith(c + '/')));
  if (!files.length) return JSON.stringify({ err: 'nothing stored for these codes' });
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1; table[n] = c >>> 0; }
  const crc32 = u8 => { let c = 0xFFFFFFFF; for (let i = 0; i < u8.length; i++) c = table[(c ^ u8[i]) & 0xFF] ^ (c >>> 8); return (c ^ 0xFFFFFFFF) >>> 0; };
  const enc = new TextEncoder(); const parts = []; const central = []; let offset = 0;
  for (const [name, blob] of files) {
    const data = new Uint8Array(await blob.arrayBuffer()); const nm = enc.encode('vprwre/' + name); const crc = crc32(data);
    const lh = new DataView(new ArrayBuffer(30)); lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, nm.length, true);
    parts.push(lh.buffer, nm, data);
    const ch = new DataView(new ArrayBuffer(46)); ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, nm.length, true); ch.setUint32(42, offset, true);
    central.push(ch.buffer, nm); offset += 30 + nm.length + data.length;
  }
  const cdSize = central.reduce((a, p) => a + (p.byteLength ?? p.length), 0);
  const end = new DataView(new ArrayBuffer(22)); end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true); end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  const zip = new Blob([...parts, ...central, end.buffer], { type: 'application/zip' });
  const a = document.createElement('a'); a.href = URL.createObjectURL(zip); a.download = FILENAME; document.body.appendChild(a); a.click(); a.remove();
  await new Promise(res => { const tx = db.transaction('files', 'readwrite'); const st = tx.objectStore('files'); all.filter(([k]) => CODES.some(c => k.startsWith(c + '/'))).forEach(([k]) => st.delete(k)); tx.oncomplete = res; });
  return JSON.stringify({ filename: FILENAME, files: files.length, bytes: zip.size });
})()
