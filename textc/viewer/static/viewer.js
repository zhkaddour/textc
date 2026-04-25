'use strict';

const $ = (id) => document.getElementById(id);

const state = {
  selectedSha: null,
  detailTab: 'commit',
  lastTopSha: null,
  currentDetail: null,
};

async function fetchState() {
  const res = await fetch('/api/state');
  if (!res.ok) throw new Error(`/api/state: ${res.status}`);
  return await res.json();
}

async function fetchCommit(sha) {
  const res = await fetch(`/api/commit/${sha}`);
  if (!res.ok) throw new Error(`/api/commit/${sha}: ${res.status}`);
  return await res.json();
}

function renderBranches(branches, currentBranch) {
  const ul = $('branch-list');
  ul.innerHTML = '';
  for (const b of branches) {
    const li = document.createElement('li');
    li.textContent = b;
    if (b === currentBranch) li.className = 'current';
    ul.appendChild(li);
  }
  $('branch-name').textContent = currentBranch || '—';
}

function renderCommitList(commits, options = {}) {
  const ul = $('commit-list');
  const { pulseTopSha } = options;
  ul.innerHTML = '';
  if (commits.length === 0) {
    ul.innerHTML = '<li class="empty">no [textc] commits on this branch yet</li>';
    return;
  }
  for (const c of commits) {
    const li = document.createElement('li');
    li.className = 'commit-row';
    if (c.sha === state.selectedSha) li.className += ' selected';
    if (c.sha === pulseTopSha) li.className += ' new-pulse';
    li.dataset.sha = c.sha;

    const dot = document.createElement('div'); dot.className = 'dot'; li.appendChild(dot);

    if (c.sculpts && c.sculpts.length) {
      const sub = document.createElement('div'); sub.className = 'sub-dots';
      for (let i = 0; i < c.sculpts.length; i++) {
        const d = document.createElement('div'); d.className = 'sub-dot';
        d.title = c.sculpts[i].note || '';
        sub.appendChild(d);
      }
      li.appendChild(sub);
    }

    const subject = document.createElement('div');
    subject.className = 'subject';
    subject.textContent = `${c.sha.slice(0, 7)} · ${c.subject}`;
    li.appendChild(subject);

    const meta = document.createElement('div');
    meta.className = 'meta';
    const sculptCount = (c.sculpts || []).length;
    meta.textContent =
      (sculptCount ? `${sculptCount} sculpt${sculptCount === 1 ? '' : 's'} · ` : '') +
      (c.compiled_at || '');
    li.appendChild(meta);

    li.addEventListener('click', () => selectCommit(c.sha));
    ul.appendChild(li);
  }
}

async function selectCommit(sha) {
  state.selectedSha = sha;
  document.querySelectorAll('.commit-row').forEach((el) => {
    el.classList.toggle('selected', el.dataset.sha === sha);
  });
  try {
    const detail = await fetchCommit(sha);
    state.currentDetail = detail;
    renderSpec(detail.spec_lines);
    renderCode(detail.code_diff);
    renderDetail(detail);
  } catch (err) {
    console.error(err);
  }
}

function renderSpec(lines) {
  const body = $('spec-body');
  body.innerHTML = '';
  if (!lines || lines.length === 0) {
    body.innerHTML = '<div class="empty">no spec content</div>';
    return;
  }
  for (const line of lines) {
    const div = document.createElement('div');
    let cls = `spec-line ${line.kind}`;
    if (line.text === '') cls += ' blank';
    else if (line.text.startsWith('# ')) cls += ' heading-1';
    else if (line.text.startsWith('## ')) cls += ' heading-2';
    else if (line.text.startsWith('### ')) cls += ' heading-3';
    div.className = cls;
    div.textContent = line.text || ' ';
    body.appendChild(div);
  }
  $('spec-meta').textContent = `${lines.filter(l => l.kind === 'added').length} added · ${lines.filter(l => l.kind === 'removed').length} removed`;
}

function renderCode(files) {
  const body = $('code-body');
  body.innerHTML = '';
  if (!files || files.length === 0) {
    body.innerHTML = '<div class="empty">no code changes (spec-only commit)</div>';
    $('code-meta').textContent = '0 files';
    return;
  }
  for (const f of files) {
    const fileDiv = document.createElement('div');
    fileDiv.className = 'code-file';
    const header = document.createElement('div');
    header.className = 'code-file-header';
    header.textContent = f.file;
    fileDiv.appendChild(header);
    for (const hunk of f.hunks) {
      const hHeader = document.createElement('div');
      hHeader.className = 'code-hunk-header';
      hHeader.textContent = hunk.header;
      fileDiv.appendChild(hHeader);
      for (const line of hunk.lines) {
        const div = document.createElement('div');
        div.className = `code-line ${line.kind}`;
        const prefix = line.kind === 'added' ? '+' : line.kind === 'removed' ? '-' : ' ';
        div.textContent = `${prefix}${line.text}`;
        fileDiv.appendChild(div);
      }
    }
    body.appendChild(fileDiv);
  }
  $('code-meta').textContent = `${files.length} file${files.length === 1 ? '' : 's'}`;
}

function renderDetail(detail) {
  const body = $('detail-body');
  body.innerHTML = '';
  if (state.detailTab === 'commit') {
    const block = document.createElement('div');
    block.className = 'commit-meta-block';

    const subj = document.createElement('div');
    subj.className = 'commit-meta-subject';
    subj.textContent = `[textc] ${detail.subject}`;
    block.appendChild(subj);

    const t = document.createElement('div');
    t.className = 'commit-meta-time';
    t.textContent = `Compiled: ${detail.compiled_at || '?'}`;
    block.appendChild(t);

    for (const sc of detail.sculpts || []) {
      const div = document.createElement('div');
      div.className = 'commit-meta-sculpt';
      div.textContent = `↪ Sculpted: ${sc.note}`;
      block.appendChild(div);
    }

    const extra = document.createElement('div');
    extra.className = 'commit-meta-extra';
    extra.innerHTML = `
      <div>sha: ${detail.sha}</div>
      <div>session: ${detail.session_index !== null ? `index ${detail.session_index}` : 'none'}</div>
      <div>${(detail.code_diff || []).length} files · ${(detail.sculpts || []).length} sculpts</div>
    `;
    block.appendChild(extra);
    body.appendChild(block);
  } else {
    const events = detail.conversation || [];
    if (events.length === 0) {
      body.innerHTML = '<div class="empty">no conversation events</div>';
      return;
    }
    for (const ev of events) {
      const div = document.createElement('div');
      div.className = `conv-event conv-${ev.kind}`;
      if (ev.kind === 'assistant_text') {
        div.textContent = ev.text;
      } else if (ev.kind === 'tool_use') {
        div.textContent = `${ev.tool}: ${ev.summary}`;
      } else if (ev.kind === 'tool_result') {
        const summary = document.createElement('span');
        summary.textContent = ev.summary;
        div.appendChild(summary);
        const full = document.createElement('div'); full.className = 'full'; full.textContent = ev.full;
        div.appendChild(full);
        div.addEventListener('click', () => div.classList.toggle('expanded'));
      } else if (ev.kind === 'system_init') {
        const tools = (ev.tools || []).slice(0, 8).join(', ');
        const more = (ev.tools || []).length > 8 ? ` +${ev.tools.length - 8} more` : '';
        const lines = [
          `model: ${ev.model || '?'}`,
          `cwd: ${ev.cwd || '?'}`,
          `tools (${(ev.tools || []).length}): ${tools}${more}`,
        ];
        if (ev.permission_mode) lines.push(`permission: ${ev.permission_mode}`);
        div.textContent = lines.join('\n');
      } else if (ev.kind === 'thinking') {
        div.textContent = ev.text;
      } else if (ev.kind === 'compile_input') {
        div.textContent = ev.text;
      } else if (ev.kind === 'sculpt') {
        const note = document.createElement('div'); note.textContent = ev.note;
        div.appendChild(note);
        if (ev.at) {
          const at = document.createElement('span'); at.className = 'at'; at.textContent = ev.at;
          div.appendChild(at);
        }
      } else if (ev.kind === 'ask') {
        const q = document.createElement('div'); q.className = 'question'; q.textContent = `Q: ${ev.question}`;
        const a = document.createElement('div'); a.className = 'answer'; a.textContent = `A: ${ev.answer}`;
        div.appendChild(q); div.appendChild(a);
        if (ev.at) {
          const at = document.createElement('span'); at.className = 'at'; at.textContent = ev.at;
          div.appendChild(at);
        }
      }
      body.appendChild(div);
    }
  }
}

function setupTabs() {
  for (const tab of document.querySelectorAll('.tab')) {
    tab.addEventListener('click', () => {
      state.detailTab = tab.dataset.tab;
      document.querySelectorAll('.tab').forEach((t) => t.classList.toggle('active', t === tab));
      if (state.currentDetail) renderDetail(state.currentDetail);
    });
  }
}

async function tick() {
  try {
    const data = await fetchState();
    renderBranches(data.branches, data.current_branch);
    const topSha = data.commits.length ? data.commits[0].sha : null;
    const newTop = topSha && topSha !== state.lastTopSha;
    const autoJump = $('auto-jump').checked;
    renderCommitList(data.commits, { pulseTopSha: newTop ? topSha : null });

    if (newTop && (autoJump || state.selectedSha === null)) {
      await selectCommit(topSha);
    } else if (state.selectedSha === null && topSha) {
      await selectCommit(topSha);
    }
    state.lastTopSha = topSha;
  } catch (err) {
    console.error('tick failed:', err);
  }
}

async function main() {
  setupTabs();
  await tick();
  setInterval(tick, 2000);
}

main();
