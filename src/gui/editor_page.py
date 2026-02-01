"""HTML/CSS/JS for the drag-and-drop block editor loaded inside a WKWebView."""

EDITOR_HTML = """\
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Helvetica Neue', sans-serif;
    background: #f0f0f0;
    padding: 12px;
    -webkit-user-select: none;
  }

  h2 {
    font-size: 12px;
    font-weight: 700;
    color: #666;
    text-transform: uppercase;
    letter-spacing: .5px;
    margin: 14px 0 6px 4px;
  }
  h2:first-child { margin-top: 0; }

  /* ---- block cards ---- */
  .block-card {
    background: #fff;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    display: flex;
    align-items: center;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
    transition: box-shadow .15s, opacity .15s;
    cursor: grab;
  }
  .block-card:active { cursor: grabbing; }
  .block-card.dragging { opacity: .4; }
  .block-card.drag-over { box-shadow: 0 -3px 0 0 #007aff; }
  .disabled-card { opacity: .45; }

  .handle { font-size: 18px; color: #aaa; margin-right: 10px; line-height: 1; }
  .block-info { flex:1; }
  .block-name { font-size: 13px; font-weight: 600; color: #222; }
  .block-desc { font-size: 11px; color: #888; margin-top: 1px; }

  .delete-btn {
    background: none; border: none; font-size: 18px;
    color: #ccc; cursor: pointer; padding: 0 6px; line-height: 1;
  }
  .delete-btn:hover { color: #ff3b30; }

  .toggle { position:relative; width:40px; height:22px; flex-shrink:0; margin-left:8px; }
  .toggle input { opacity:0; width:0; height:0; }
  .toggle .slider {
    position:absolute; inset:0;
    background: #ccc; border-radius:11px;
    transition: background .2s; cursor: pointer;
  }
  .toggle .slider::after {
    content:''; position:absolute; left:2px; top:2px;
    width:18px; height:18px; background:#fff; border-radius:50%;
    transition: transform .2s;
  }
  .toggle input:checked + .slider { background:#34c759; }
  .toggle input:checked + .slider::after { transform:translateX(18px); }

  .add-btn {
    display: block; margin: 6px auto 0;
    background: none; border: 1.5px dashed #bbb; border-radius: 10px;
    padding: 8px 0; width: 100%; font-size: 13px;
    color: #888; cursor: pointer; font-family: inherit;
  }
  .add-btn:hover { border-color: #007aff; color: #007aff; }

  /* ---- style controls ---- */
  .style-card {
    background: #fff;
    border-radius: 10px;
    padding: 10px 14px;
    margin-bottom: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,.12);
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .style-card .style-label {
    font-size: 13px; font-weight: 500; color: #222;
    width: 120px; flex-shrink: 0;
  }
  .style-card input[type=range] {
    flex: 1;
    accent-color: #007aff;
  }
  .style-card .style-val {
    font-size: 12px; color: #555;
    width: 52px; text-align: right; flex-shrink: 0;
    font-variant-numeric: tabular-nums;
  }
</style>
</head>
<body>

<h2>Blocks</h2>
<div id="container"></div>
<button class="add-btn" onclick="addSeparator()">+ Add Separator</button>

<h2>Style</h2>
<div id="style-controls"></div>

<script>
let blocks = [];
let sepCounter = 10;

let style = {
  title_size: 34,
  body_size: 15,
  due_date_size: 22,
  render_width: 576,
  print_scale: 2,
  top_margin: 0,
  bottom_margin: 2
};

const STYLE_DEFS = [
  { key:'top_margin',    label:'Top margin',    min:0,  max:15, step:1, unit:' lines' },
  { key:'bottom_margin', label:'Bottom margin', min:0,  max:15, step:1, unit:' lines' },
  { key:'title_size',    label:'Title font',    min:18, max:60, step:1, unit:'px' },
  { key:'body_size',     label:'Body font',     min:10, max:30, step:1, unit:'px' },
  { key:'due_date_size', label:'Due date font', min:14, max:40, step:1, unit:'px' },
  { key:'render_width',  label:'Render width',  min:384, max:1152, step:1, unit:'px' },
  { key:'print_scale',   label:'Print quality', min:1,  max:3,  step:1, unit:'x' },
];

const META = {
  title:     { name:'Task Title',  desc:'{{ task.name }}' },
  project:   { name:'Project',     desc:'{{ task.project }}' },
  due_date:  { name:'Due Date',    desc:'{{ task.due_date }}' },
  tags:      { name:'Tags',        desc:'{{ task.tags }}' },
  notes:     { name:'Notes',       desc:'{{ task.notes }}' },
  separator: { name:'Separator',   desc:'Dashed line' },
};

/* ---- init ---- */

function initEditor(cfg) {
  blocks = cfg.blocks || cfg;
  if (cfg.style) Object.assign(style, cfg.style);
  blocks.forEach(b => {
    if (b.id) {
      const n = parseInt(b.id.split('-')[1]);
      if (n >= sepCounter) sepCounter = n + 1;
    }
  });
  renderBlocks();
  renderStyleControls();
}

/* keep old name working */
function initBlocks(cfg) { initEditor(cfg); }

/* ---- blocks rendering ---- */

function renderBlocks() {
  const c = document.getElementById('container');
  c.innerHTML = '';
  blocks.forEach((b, i) => c.appendChild(makeCard(b, i)));
}

function makeCard(block, idx) {
  const card = document.createElement('div');
  card.className = 'block-card' + (block.enabled ? '' : ' disabled-card');
  card.draggable = true;
  card.dataset.idx = idx;

  const h = document.createElement('span');
  h.className = 'handle'; h.textContent = '\\u2261';
  card.appendChild(h);

  const info = document.createElement('div');
  info.className = 'block-info';
  const m = META[block.type] || { name: block.type, desc: '' };
  info.innerHTML = '<div class="block-name">' + m.name + '</div>'
                 + '<div class="block-desc">' + m.desc + '</div>';
  card.appendChild(info);

  if (block.type === 'separator') {
    const del = document.createElement('button');
    del.className = 'delete-btn'; del.textContent = '\\u00d7';
    del.onclick = function(e) { e.stopPropagation(); blocks.splice(idx,1); renderBlocks(); };
    card.appendChild(del);
  }

  const tog = document.createElement('label');
  tog.className = 'toggle';
  const cb = document.createElement('input');
  cb.type = 'checkbox'; cb.checked = block.enabled;
  cb.onchange = function() { blocks[idx].enabled = cb.checked; renderBlocks(); };
  const sl = document.createElement('span'); sl.className = 'slider';
  tog.appendChild(cb); tog.appendChild(sl);
  card.appendChild(tog);

  card.addEventListener('dragstart', onDragStart);
  card.addEventListener('dragover',  onDragOver);
  card.addEventListener('dragleave', onDragLeave);
  card.addEventListener('drop',      onDrop);
  card.addEventListener('dragend',   onDragEnd);
  return card;
}

/* ---- drag-and-drop ---- */

let dragIdx = null;

function onDragStart(e) {
  dragIdx = +this.dataset.idx;
  this.classList.add('dragging');
  e.dataTransfer.effectAllowed = 'move';
}
function onDragOver(e) {
  e.preventDefault(); e.dataTransfer.dropEffect = 'move';
  this.classList.add('drag-over');
}
function onDragLeave() { this.classList.remove('drag-over'); }
function onDrop(e) {
  e.preventDefault(); this.classList.remove('drag-over');
  const toIdx = +this.dataset.idx;
  if (dragIdx === null || dragIdx === toIdx) return;
  const item = blocks.splice(dragIdx, 1)[0];
  blocks.splice(toIdx, 0, item);
  renderBlocks();
}
function onDragEnd() {
  dragIdx = null;
  document.querySelectorAll('.dragging').forEach(el => el.classList.remove('dragging'));
}

/* ---- style controls ---- */

function renderStyleControls() {
  const c = document.getElementById('style-controls');
  c.innerHTML = '';
  STYLE_DEFS.forEach(def => {
    const row = document.createElement('div');
    row.className = 'style-card';

    const lbl = document.createElement('span');
    lbl.className = 'style-label'; lbl.textContent = def.label;

    const slider = document.createElement('input');
    slider.type = 'range';
    slider.min = def.min; slider.max = def.max; slider.step = def.step;
    slider.value = style[def.key];

    const val = document.createElement('span');
    val.className = 'style-val';
    val.textContent = style[def.key] + def.unit;

    slider.oninput = function() {
      style[def.key] = +this.value;
      val.textContent = this.value + def.unit;
    };

    row.appendChild(lbl);
    row.appendChild(slider);
    row.appendChild(val);
    c.appendChild(row);
  });
}

/* ---- actions ---- */

function addSeparator() {
  blocks.push({ type:'separator', enabled:true, id:'sep-' + sepCounter++ });
  renderBlocks();
}

function getConfig() {
  return JSON.stringify({ blocks: blocks, style: style });
}
</script>
</body>
</html>
"""
