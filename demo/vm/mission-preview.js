const CSP = "default-src 'none'; img-src data: blob:; media-src data: blob:; font-src data:; style-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'; frame-src 'none'; object-src 'none'; form-action 'none'; base-uri 'none'";

function cleanPath(value) {
  if (typeof value !== 'string' || !value || value.startsWith('/') || value.includes('\\')) return null;
  const parts = value.split('/');
  if (parts.some(part => !part || part === '.' || part === '..' || part.startsWith('.'))) return null;
  return parts.join('/');
}

function resolveLocal(entry, ref) {
  if (typeof ref !== 'string' || !ref || ref.startsWith('#') || ref.startsWith('data:') || ref.startsWith('blob:')) return null;
  try {
    const base = new URL(entry, 'https://preview.invalid/');
    const resolved = new URL(ref, base);
    if (resolved.origin !== 'https://preview.invalid') return null;
    return decodeURIComponent(resolved.pathname.slice(1));
  } catch { return null; }
}

export function previewEntry(bundle) {
  if (!bundle || !Array.isArray(bundle.files)) return null;
  const files = bundle.files.filter(item => item && cleanPath(item.path) && typeof item.content === 'string');
  if (!files.length) return null;
  return files.find(item => item.path === 'index.html') || files.find(item => item.path.endsWith('/index.html')) || files.find(item => item.path.endsWith('.html')) || null;
}

export function previewDocument(bundle) {
  const entry = previewEntry(bundle);
  if (!entry) return null;
  const map = new Map(bundle.files.map(item => [cleanPath(item?.path), item?.content]).filter(([path, content]) => path && typeof content === 'string'));
  const parsed = new DOMParser().parseFromString(entry.content, 'text/html');
  parsed.querySelectorAll('base,object,embed,iframe,meta[http-equiv="refresh" i]').forEach(node => node.remove());
  for (const link of [...parsed.querySelectorAll('link[rel~="stylesheet"][href]')]) {
    const path = resolveLocal(entry.path, link.getAttribute('href'));
    if (path && map.has(path)) {
      const style = parsed.createElement('style'); style.textContent = map.get(path); link.replaceWith(style);
    } else link.remove();
  }
  for (const script of [...parsed.querySelectorAll('script[src]')]) {
    const path = resolveLocal(entry.path, script.getAttribute('src'));
    if (path && map.has(path)) {
      const inline = parsed.createElement('script');
      if (script.type) inline.type = script.type;
      inline.textContent = map.get(path); script.replaceWith(inline);
    } else script.remove();
  }
  const meta = parsed.createElement('meta'); meta.httpEquiv = 'Content-Security-Policy'; meta.content = CSP;
  parsed.head.prepend(meta);
  return '<!doctype html>\n' + parsed.documentElement.outerHTML;
}

export function renderPreview(container, bundle, {frameId = '', status = null} = {}) {
  container.replaceChildren();
  const srcdoc = previewDocument(bundle);
  if (!srcdoc) {
    if (status) status.textContent = 'No HTML entry point was generated. Download the files to inspect this deliverable.';
    return null;
  }
  const controls = document.createElement('div'); controls.className = 'preview-controls';
  const note = document.createElement('span'); note.className = 'muted'; note.textContent = 'Interactive isolated preview · network blocked · not semantic verification';
  const stop = document.createElement('button'); stop.type = 'button'; stop.textContent = 'Stop preview';
  controls.append(note, stop);
  const frame = document.createElement('iframe');
  if (frameId) frame.id = frameId;
  frame.title = 'Generated app preview'; frame.sandbox = 'allow-scripts'; frame.referrerPolicy = 'no-referrer'; frame.srcdoc = srcdoc;
  frame.addEventListener('load', () => { if (status) status.textContent = 'Preview loaded in an isolated browser sandbox. Interact with it below to verify behavior.'; });
  stop.onclick = () => { frame.remove(); stop.disabled = true; if (status) status.textContent = 'Preview stopped. Generated files remain saved in the guest.'; };
  container.append(controls, frame);
  return frame;
}
