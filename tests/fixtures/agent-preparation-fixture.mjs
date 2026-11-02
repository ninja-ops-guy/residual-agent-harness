import {mountAgentPreparation} from '../../residual/station/static/agent-preparation-view.mjs';
import {fixture, DISPLAY_TIME} from './agent-preparation-data.mjs';

const view = mountAgentPreparation(document.getElementById('preparation'), {}, () => DISPLAY_TIME);
for (const button of document.querySelectorAll('[data-fixture]')) {
  button.addEventListener('click', () => view.update(fixture(button.dataset.fixture)));
}
