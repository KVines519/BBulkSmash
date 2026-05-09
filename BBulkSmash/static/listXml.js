// ── Panel switching ──────────────────────────────────────────────────────────

const PANEL_KEY = 'fm_active_panel';

function showPanel(panelId) {
    document.querySelectorAll('.fm-panel').forEach(p => p.style.display = 'none');
    document.querySelectorAll('.fm-tab-btn').forEach(b => b.classList.remove('active'));
    const panel = document.getElementById(panelId);
    if (panel) panel.style.display = 'block';
    const btn = document.querySelector(`.fm-tab-btn[data-panel="${panelId}"]`);
    if (btn) btn.classList.add('active');
    sessionStorage.setItem(PANEL_KEY, panelId);
}

document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.fm-tab-btn').forEach(btn => {
        btn.addEventListener('click', () => showPanel(btn.getAttribute('data-panel')));
    });

    // Restore last active panel
    const saved = sessionStorage.getItem(PANEL_KEY);
    if (saved && document.getElementById(saved)) {
        showPanel(saved);
    }

    // Upload modal open/close
    const uploadModal = document.getElementById('upload-modal');
    document.getElementById('upload-xml-b').addEventListener('click', () => {
        uploadModal.style.display = 'block';
    });
    const closeBtn = uploadModal.querySelector('.close');
    if (closeBtn) closeBtn.onclick = () => { uploadModal.style.display = 'none'; };
    window.addEventListener('click', e => {
        if (e.target === uploadModal) uploadModal.style.display = 'none';
    });
});


// ── SVG icons ────────────────────────────────────────────────────────────────

const SVG_DOWNLOAD = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" height="14px" width="14px" fill="currentColor"><path d="M288 32c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 242.7-73.4-73.4c-12.5-12.5-32.8-12.5-45.3 0s-12.5 32.8 0 45.3l128 128c12.5 12.5 32.8 12.5 45.3 0l128-128c12.5-12.5 12.5-32.8 0-45.3s-32.8-12.5-45.3 0L288 274.7 288 32zM64 352c-35.3 0-64 28.7-64 64l0 32c0 35.3 28.7 64 64 64l384 0c35.3 0 64-28.7 64-64l0-32c0-35.3-28.7-64-64-64l-101.5 0-45.3 45.3c-25 25-65.5 25-90.5 0L165.5 352 64 352zm368 56a24 24 0 1 1 0 48 24 24 0 1 1 0-48z"/></svg>`;
const SVG_EDIT     = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" height="14px" width="14px" fill="currentColor"><path d="M471.6 21.7c-21.9-21.9-57.3-21.9-79.2 0L362.3 51.7l97.9 97.9 30.1-30.1c21.9-21.9 21.9-57.3 0-79.2L471.6 21.7zm-299.2 220c-6.1 6.1-10.8 13.6-13.5 21.9l-29.6 88.8c-2.9 8.6-.6 18.1 5.8 24.6s15.9 8.7 24.6 5.8l88.8-29.6c8.2-2.7 15.7-7.4 21.9-13.5L437.7 172.3 339.7 74.3 172.4 241.7zM96 64C43 64 0 107 0 160L0 416c0 53 43 96 96 96l256 0c53 0 96-43 96-96l0-96c0-17.7-14.3-32-32-32s-32 14.3-32 32l0 96c0 17.7-14.3 32-32 32L96 448c-17.7 0-32-14.3-32-32l0-256c0-17.7 14.3-32 32-32l96 0c17.7 0 32-14.3 32-32s-14.3-32-32-32L96 64z"/></svg>`;
const SVG_DELETE   = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 448 512" height="14px" width="14px" fill="currentColor"><path d="M135.2 17.7L128 32 32 32C14.3 32 0 46.3 0 64S14.3 96 32 96l384 0c17.7 0 32-14.3 32-32s-14.3-32-32-32l-96 0-7.2-14.3C307.4 6.8 296.3 0 284.2 0L163.8 0c-12.1 0-23.2 6.8-28.6 17.7zM416 128L32 128 53.2 467c1.6 25.3 22.6 45 47.9 45l245.8 0c25.3 0 46.3-19.7 47.9-45L416 128z"/></svg>`;
const SVG_SORT_ASC  = `▲`;
const SVG_SORT_DESC = `▼`;
const SVG_SORT_NONE = `⇅`;


// ── Delete confirmation modal ─────────────────────────────────────────────────

let _deleteCallback = null;

function showDeleteModal(names, onConfirm) {
    const modal = document.getElementById('delete-confirm-modal');
    const list  = document.getElementById('delete-confirm-list');
    list.innerHTML = '';
    names.forEach(n => {
        const li = document.createElement('li');
        li.textContent = n;
        list.appendChild(li);
    });
    document.getElementById('delete-confirm-count').textContent =
        names.length === 1 ? '1 file' : `${names.length} files`;
    _deleteCallback = onConfirm;
    modal.style.display = 'flex';
}

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('delete-confirm-ok').addEventListener('click', () => {
        document.getElementById('delete-confirm-modal').style.display = 'none';
        if (_deleteCallback) { _deleteCallback(); _deleteCallback = null; }
    });
    document.getElementById('delete-confirm-cancel').addEventListener('click', () => {
        document.getElementById('delete-confirm-modal').style.display = 'none';
        _deleteCallback = null;
    });
});


// ── AJAX delete ───────────────────────────────────────────────────────────────

function getCsrfToken() {
    const el = document.querySelector('[name=csrfmiddlewaretoken]');
    return el ? el.value : '';
}

async function deleteFiles(names, onSuccess) {
    try {
        const resp = await fetch('/delete-files/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken(),
            },
            body: JSON.stringify({ files: names }),
        });
        const result = await resp.json();
        onSuccess(result.deleted || [], result.errors || []);
    } catch (e) {
        console.error('Delete failed:', e);
    }
}


// ── Sortable file table ───────────────────────────────────────────────────────

/**
 * Build a sortable, multi-select file table inside `container`.
 *
 * @param {HTMLElement} container  - The div to render into
 * @param {Array}       files      - [{name, mtime}, ...]
 * @param {Function}    downloadUrl - (name) => URL string
 * @param {Function}    [editUrl]  - (name) => URL string, or null
 * @param {Function}    [onRowClick] - optional click handler for flow diagrams
 */
function buildFileTable(container, files, downloadUrl, editUrl, onRowClick) {
    // Sort state
    let sortCol = 'mtime';   // 'name' | 'mtime'
    let sortDir = 'desc';    // 'asc'  | 'desc'

    // Working copy — we sort this in place
    let rows = files.slice();

    function doSort() {
        rows.sort((a, b) => {
            const va = a[sortCol] || '';
            const vb = b[sortCol] || '';
            const cmp = va.localeCompare(vb);
            return sortDir === 'asc' ? cmp : -cmp;
        });
    }

    function render() {
        doSort();
        container.innerHTML = '';

        // ── toolbar ──
        const toolbar = document.createElement('div');
        toolbar.className = 'fm-table-toolbar';

        const selectAllCb = document.createElement('input');
        selectAllCb.type = 'checkbox';
        selectAllCb.title = 'Select all';
        selectAllCb.style.marginRight = '8px';

        const deleteSelBtn = document.createElement('button');
        deleteSelBtn.className = 'button';
        deleteSelBtn.style.cssText = 'padding:2px 12px; font-size:0.85em;';
        deleteSelBtn.innerHTML = SVG_DELETE + ' Delete selected';
        deleteSelBtn.disabled = true;

        toolbar.appendChild(selectAllCb);
        toolbar.appendChild(deleteSelBtn);
        container.appendChild(toolbar);

        // ── table ──
        const table = document.createElement('table');
        table.className = 'fm-table';

        // header
        const thead = document.createElement('thead');
        const hrow  = document.createElement('tr');

        const thCb = document.createElement('th');
        thCb.style.width = '32px';
        hrow.appendChild(thCb);

        function makeHeader(label, col) {
            const th = document.createElement('th');
            th.style.cursor = 'pointer';
            th.style.userSelect = 'none';
            const indicator = sortCol === col
                ? (sortDir === 'asc' ? SVG_SORT_ASC : SVG_SORT_DESC)
                : SVG_SORT_NONE;
            th.innerHTML = `${label} <span style="font-size:0.75em;color:#66798c">${indicator}</span>`;
            th.addEventListener('click', () => {
                if (sortCol === col) {
                    sortDir = sortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    sortCol = col;
                    sortDir = 'asc';
                }
                render();
            });
            return th;
        }

        hrow.appendChild(makeHeader('Filename', 'name'));
        hrow.appendChild(makeHeader('Modified', 'mtime'));

        const thActions = document.createElement('th');
        thActions.textContent = 'Actions';
        thActions.style.width = '80px';
        hrow.appendChild(thActions);

        thead.appendChild(hrow);
        table.appendChild(thead);

        // body
        const tbody = document.createElement('tbody');

        rows.forEach((file, idx) => {
            const tr = document.createElement('tr');
            tr.style.backgroundColor = idx % 2 === 0 ? '#e7e7e7' : '#dbdbdb';
            tr.dataset.filename = file.name;

            // checkbox
            const tdCb = document.createElement('td');
            const cb = document.createElement('input');
            cb.type = 'checkbox';
            cb.dataset.filename = file.name;
            // change listener added after updateDeleteBtn is defined below
            tdCb.appendChild(cb);
            tr.appendChild(tdCb);

            // filename
            const tdName = document.createElement('td');
            tdName.style.fontFamily = 'monospace';
            tdName.style.fontSize = '0.9em';
            tdName.style.wordBreak = 'break-all';
            if (onRowClick) {
                tdName.style.cursor = 'pointer';
                tdName.classList.add('show-flow');
                tdName.setAttribute('data-filename', file.name);
                tdName.addEventListener('click', () => onRowClick(file.name, tr));
            }
            tdName.textContent = file.name;
            tr.appendChild(tdName);

            // mtime
            const tdMtime = document.createElement('td');
            tdMtime.style.fontSize = '0.82em';
            tdMtime.style.color = '#555';
            tdMtime.style.whiteSpace = 'nowrap';
            tdMtime.textContent = file.mtime || '';
            tr.appendChild(tdMtime);

            // actions
            const tdAct = document.createElement('td');
            tdAct.style.whiteSpace = 'nowrap';

            const dlLink = document.createElement('a');
            dlLink.href = downloadUrl(file.name);
            dlLink.className = 'xml-li-button';
            dlLink.title = 'Download';
            dlLink.download = file.name;
            dlLink.innerHTML = SVG_DOWNLOAD;
            tdAct.appendChild(dlLink);

            if (editUrl) {
                const editLink = document.createElement('a');
                editLink.href = editUrl(file.name);
                editLink.className = 'xml-li-button';
                editLink.title = 'Edit';
                editLink.innerHTML = SVG_EDIT;
                tdAct.appendChild(editLink);
            }

            const delBtn = document.createElement('a');
            delBtn.href = '#';
            delBtn.className = 'xml-li-button';
            delBtn.title = 'Delete';
            delBtn.innerHTML = SVG_DELETE;
            delBtn.addEventListener('click', e => {
                e.preventDefault();
                showDeleteModal([file.name], () => {
                    deleteFiles([file.name], (deleted) => {
                        if (deleted.includes(file.name)) {
                            rows = rows.filter(r => r.name !== file.name);
                            render();
                        }
                    });
                });
            });
            tdAct.appendChild(delBtn);

            tr.appendChild(tdAct);
            tbody.appendChild(tr);
        });

        table.appendChild(tbody);
        container.appendChild(table);

        // ── select-all and bulk-delete wiring (defined after tbody exists) ──
        function updateDeleteBtn() {
            const checked = tbody.querySelectorAll('input[type=checkbox]:checked');
            deleteSelBtn.disabled = checked.length === 0;
            selectAllCb.indeterminate =
                checked.length > 0 && checked.length < rows.length;
            selectAllCb.checked = checked.length === rows.length && rows.length > 0;
        }

        selectAllCb.addEventListener('change', () => {
            tbody.querySelectorAll('input[type=checkbox]').forEach(cb => {
                cb.checked = selectAllCb.checked;
            });
            updateDeleteBtn();
        });

        deleteSelBtn.addEventListener('click', () => {
            const checked = [...tbody.querySelectorAll('input[type=checkbox]:checked')];
            const names = checked.map(cb => cb.dataset.filename);
            if (!names.length) return;
            showDeleteModal(names, () => {
                deleteFiles(names, (deleted) => {
                    rows = rows.filter(r => !deleted.includes(r.name));
                    render();
                });
            });
        });

        // Re-wire each row checkbox now that updateDeleteBtn is in scope
        tbody.querySelectorAll('input[type=checkbox]').forEach(cb => {
            cb.addEventListener('change', updateDeleteBtn);
        });
    }

    render();
}


// ── Populate panels ───────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {

    // XML panel — UAC
    buildFileTable(
        document.getElementById('uac-list-container'),
        uacXmlFiles,
        name => `/xml/${name}`,
        name => `/edit-xml/?xml=${name}&back=file-management`,
        (name, tr) => {
            document.querySelectorAll('.fm-table tr.fm-selected').forEach(r => r.classList.remove('fm-selected'));
            tr.classList.add('fm-selected');
            fetchAndRenderDiagram(name);
        }
    );

    // XML panel — UAS
    buildFileTable(
        document.getElementById('uas-list-container'),
        uasXmlFiles,
        name => `/xml/${name}`,
        name => `/edit-xml/?xml=${name}&back=file-management`,
        (name, tr) => {
            document.querySelectorAll('.fm-table tr.fm-selected').forEach(r => r.classList.remove('fm-selected'));
            tr.classList.add('fm-selected');
            fetchAndRenderDiagram(name);
        }
    );

    // PCAP audio files
    buildFileTable(
        document.getElementById('pcap-list-container'),
        pcapFiles,
        name => `/download/${name}`
    );

    // WAV audio files
    buildFileTable(
        document.getElementById('wav-list-container'),
        wavFiles,
        name => `/download/${name}`
    );

    // CSV injection files
    buildFileTable(
        document.getElementById('csv-list-container'),
        csvFiles,
        name => `/download/${name}`
    );

    // Logs & Trace files
    buildFileTable(
        document.getElementById('log-list-container'),
        logFiles,
        name => `/download-log/${name}`
    );
});


// ── Flow diagram (XML panel) ─────────────────────────────────────────────────

async function fetchAndRenderDiagram(fileName) {
    const container = document.getElementById('flow-diagram');
    const xmlFlow   = document.getElementById('xml-flow');
    try {
        const response = await fetch(`/xml/${fileName}`);
        if (!response.ok) throw new Error(`Could not fetch ${fileName}`);
        const xmlText = await response.text();
        const xmlDoc  = new DOMParser().parseFromString(xmlText, 'text/xml');

        let umlText = fileName.startsWith('uac')
            ? `\nparticipant ${fileName} as thisXml\nparticipant farEnd\n`
            : `\nparticipant farEnd\nparticipant ${fileName} as thisXml\n`;

        Array.from(xmlDoc.getElementsByTagName('*')).forEach(el => {
            if (el.tagName === 'send') {
                const req = el.textContent.trim().match(/^\s*(INVITE|ACK|BYE|CANCEL|OPTIONS|REGISTER|PRACK|SUBSCRIBE|NOTIFY|PUBLISH|INFO|REFER|MESSAGE|UPDATE)\s+/m);
                const res = el.textContent.trim().match(/^\s*SIP\/\d\.\d\s*(\d{3})\s+/m);
                const label = req ? req[1] : (res ? res[1] : 'Unknown');
                umlText += `thisXml -> farEnd: send    ${label}\n`;
            } else if (el.tagName === 'recv') {
                const label = el.getAttribute('request') || el.getAttribute('response') || '';
                umlText += `farEnd -> thisXml: recv    ${label}\n`;
            }
        });

        container.innerHTML = '';
        if (xmlFlow) xmlFlow.style.display = 'block';
        const diagram = Diagram.parse(umlText);
        diagram.drawSVG(container, { theme: 'simple' });
    } catch (err) {
        if (container) container.innerHTML = `<br>${err}`;
        if (xmlFlow) xmlFlow.style.display = 'block';
    }
}
