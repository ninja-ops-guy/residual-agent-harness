import {DECLARATION_FIELDS, reducePreparation} from './agent-preparation-model.mjs';

// No network, storage, credentials, execution or Station integration.
export function mountAgentPreparation(root, initial = {}, clock = () => Date.now() / 1000) {
  const doc = root.ownerDocument;
  const element = (tag, content, attributes = {}) => {
    const node = doc.createElement(tag);
    if (content !== undefined) node.textContent = content;
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    return node;
  };
  let current = initial;
  let destroyed = false;
  root.classList.add('agent-preparation');
  const title = element('h1', 'Agent preparation');
  const notice = element('p', 'Isolated preview - not integrated and not native-qualified.', {class: 'preparation-notice'});
  const explanation = element('p', 'Prepare intended identity labels without contacting Station. Declarations are unverified. Do not enter credentials or private profile contents. Nothing is saved.');
  const form = element('form');
  const fields = element('fieldset');
  fields.append(element('legend', 'Owner declarations - unverified'));
  const grid = element('div', undefined, {class: 'preparation-fields'});
  const controls = new Map();
  for (const [key, label, max] of [...DECLARATION_FIELDS, ['capabilities', 'Requested capabilities (comma separated)', 1024]]) {
    const wrapper = element('label', label);
    const control = element('input', undefined, {name: key, type: 'text', maxlength: String(max), autocomplete: 'off', spellcheck: 'false'});
    controls.set(key, control);
    wrapper.append(control);
    grid.append(wrapper);
  }
  fields.append(grid);
  const review = element('button', 'Review declarations', {type: 'submit'});
  const clear = element('button', 'Clear preparation', {type: 'button'});
  form.append(fields, review, clear);
  const output = element('section', undefined, {'aria-label': 'Preparation stages', 'aria-live': 'polite'});
  const declarationSummary = element('p', undefined, {class: 'preparation-declarations'});
  const binding = element('p');
  const list = element('ol', undefined, {class: 'preparation-stages'});
  output.append(declarationSummary, binding, list);
  root.replaceChildren(title, notice, explanation, form, output);

  function render(resetControls) {
    const result = reducePreparation(current, clock());
    if (!result.valid) current = {};
    if (resetControls) {
      for (const [key, control] of controls) {
        const value = result.intended[key];
        control.value = Array.isArray(value) ? value.join(', ') : value ?? '';
      }
    }
    declarationSummary.textContent = result.valid
      ? 'Unverified declarations: ' + (Object.entries(result.intended).map(([key, value]) => key + ' = ' + (Array.isArray(value) ? value.join(', ') : value)).join('; ') || 'none')
      : 'Unsupported or malformed input. No declarations or reports accepted.';
    binding.textContent = result.binding;
    list.replaceChildren();
    for (const stage of result.stages) {
      const row = element('li', undefined, {'data-stage': stage.id, 'data-state': stage.state});
      row.append(element('h2', stage.title), element('strong', stage.state), element('p', stage.detail));
      list.append(row);
    }
  }
  function onSubmit(event) {
    event.preventDefault();
    const intended = {};
    for (const [key, control] of controls) {
      const value = control.value.trim();
      if (value) intended[key] = key === 'capabilities' ? value.split(',').map(item => item.trim()) : value;
    }
    current = {...current, intended};
    render(false);
  }
  function onClear() { current = {}; render(true); }
  form.addEventListener('submit', onSubmit);
  clear.addEventListener('click', onClear);
  render(true);
  return {
    update(input) { if (!destroyed) { current = input; render(true); } },
    clear() { if (!destroyed) onClear(); },
    destroy() {
      destroyed = true;
      current = {};
      form.removeEventListener('submit', onSubmit);
      clear.removeEventListener('click', onClear);
      root.replaceChildren();
      root.classList.remove('agent-preparation');
    },
  };
}
