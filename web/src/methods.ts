import { marked } from 'marked';
import source from '../../docs/methods.md?raw';

document.getElementById('doc')!.innerHTML = marked.parse(source, { async: false });
