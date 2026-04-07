import json
from kg_config import D3_LOCAL_PATH


# ─────────────────────────────────────────────────────────────────────────────
# RENDER HTML
# ─────────────────────────────────────────────────────────────────────────────
def render_html(graph: dict, course_code: str = "") -> str:
    title    = graph.get("title", "Knowledge Graph")
    subject  = graph.get("subject", "")
    summary  = graph.get("summary", "")
    clusters = graph.get("clusters", [])
    nodes    = graph.get("nodes", [])
    edges    = graph.get("edges", [])
    subtitle = f"{course_code} · Knowledge Graph" if course_code else "Knowledge Graph"

    def he(t): return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    def safe_json(obj): return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    clusters_js = safe_json(clusters)
    nodes_js    = safe_json(nodes)
    edges_js    = safe_json(edges)

    if D3_LOCAL_PATH.exists():
        d3_tag = f"<script>\n{D3_LOCAL_PATH.read_text(encoding='utf-8', errors='ignore')}\n</script>"
    else:
        d3_tag = '<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{he(title)} · Knowledge Graph</title>
{d3_tag}
<link href="https://fonts.googleapis.com/css2?family=Sora:wght@400;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{margin:0;padding:0;box-sizing:border-box;}}
:root{{
  --bg:#f7f8fc;--surface:#fff;--surface2:#eef1f8;
  --border:rgba(0,0,0,0.07);--border2:rgba(0,0,0,0.13);
  --text:#1a1f35;--muted:#8896b0;--muted2:#6b7a99;
  --accent:#3873ff;
  --panel-w:330px;--topbar-h:52px;
  --font-body:'Sora',sans-serif;--font-mono:'IBM Plex Mono',monospace;
}}
body{{background:var(--bg);color:var(--text);font-family:var(--font-body);width:100vw;height:100vh;overflow:hidden;}}

/* TOP BAR */
#topbar{{position:fixed;top:0;left:0;right:0;height:var(--topbar-h);background:rgba(255,255,255,.97);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 18px;gap:0;z-index:300;}}
.tb-brand{{display:flex;align-items:center;gap:9px;padding-right:16px;border-right:1px solid var(--border);margin-right:16px;flex-shrink:0;}}
.gem{{width:30px;height:30px;background:linear-gradient(135deg,#3873ff,#9b59ff);border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:15px;}}
.brand-title{{font-size:0.8rem;font-weight:700;letter-spacing:-.3px;}}
.brand-sub{{font-size:0.53rem;color:var(--muted2);font-family:var(--font-mono);letter-spacing:.8px;text-transform:uppercase;}}
.tb-stats{{display:flex;gap:20px;flex:1;}}
.sv{{font-size:0.88rem;font-weight:700;font-family:var(--font-mono);color:var(--accent);line-height:1;}}
.sl{{font-size:0.49rem;color:var(--muted2);text-transform:uppercase;letter-spacing:1px;margin-top:2px;}}
.tb-progress{{flex:1;max-width:170px;display:flex;align-items:center;gap:8px;margin:0 14px;}}
.prog-track{{flex:1;height:3px;background:rgba(0,0,0,.07);border-radius:2px;overflow:hidden;}}
.prog-fill{{height:100%;background:linear-gradient(90deg,#3873ff,#9b59ff);width:0%;border-radius:2px;transition:width .5s ease;}}
.prog-pct{{font-size:0.57rem;font-family:var(--font-mono);color:var(--muted2);min-width:26px;}}
.tb-div{{width:1px;height:26px;background:var(--border);margin:0 10px;}}
.tb-btn{{padding:5px 11px;border-radius:5px;font-size:0.62rem;font-weight:600;cursor:pointer;border:1px solid var(--border);background:transparent;color:var(--muted2);font-family:var(--font-mono);transition:all .15s;white-space:nowrap;}}
.tb-btn:hover{{border-color:rgba(56,115,255,.4);color:#3873ff;background:rgba(56,115,255,.04);}}

/* CANVAS — full page */
#canvas-wrap{{position:fixed;top:var(--topbar-h);left:0;right:0;bottom:0;z-index:1;transition:right .3s ease;}}
#canvas-wrap.panel-open{{right:var(--panel-w);}}
#canvas-wrap svg{{width:100%;height:100%;display:block;}}

/* PANEL */
#panel{{position:fixed;top:var(--topbar-h);right:0;width:var(--panel-w);bottom:0;background:var(--surface);border-left:1px solid var(--border);display:flex;flex-direction:column;z-index:200;transform:translateX(100%);transition:transform .3s ease;}}
#panel.open{{transform:translateX(0);}}
.panel-tab{{position:absolute;top:16px;left:-30px;width:26px;height:26px;background:var(--surface);border:1px solid var(--border);border-right:none;border-radius:6px 0 0 6px;display:flex;align-items:center;justify-content:center;cursor:pointer;font-size:11px;color:var(--muted2);transition:color .15s;}}
.panel-tab:hover{{color:var(--accent);}}
.panel-scroll{{flex:1;overflow-y:auto;}}
.panel-scroll::-webkit-scrollbar{{width:3px;}}
.panel-scroll::-webkit-scrollbar-thumb{{background:var(--border2);border-radius:2px;}}
.node-card{{padding:18px;border-bottom:1px solid var(--border);}}
.node-type-row{{display:flex;align-items:center;gap:7px;margin-bottom:9px;}}
.ndot{{width:9px;height:9px;border-radius:50%;flex-shrink:0;}}
.ntype{{font-size:0.53rem;font-family:var(--font-mono);letter-spacing:1.5px;text-transform:uppercase;color:var(--muted2);}}
.nbadge{{margin-left:auto;font-size:0.52rem;font-family:var(--font-mono);padding:2px 7px;border-radius:4px;}}
.ntitle{{font-size:1.05rem;font-weight:800;letter-spacing:-.4px;line-height:1.2;margin-bottom:8px;}}
.ndesc{{font-size:0.71rem;color:var(--muted2);line-height:1.68;}}
.conn-section{{padding:12px 14px;}}
.conn-head{{font-size:0.52rem;font-family:var(--font-mono);letter-spacing:1.4px;text-transform:uppercase;color:var(--muted);margin-bottom:7px;}}
.conn-card{{display:flex;align-items:flex-start;gap:9px;padding:9px 10px;background:var(--surface2);border:1px solid var(--border);border-radius:8px;margin-bottom:5px;cursor:pointer;transition:all .16s;animation:connIn .18s ease both;}}
.conn-card:hover{{border-color:var(--border2);background:rgba(56,115,255,.05);transform:translateX(2px);}}
@keyframes connIn{{from{{opacity:0;transform:translateX(5px)}}to{{opacity:1;transform:translateX(0)}}}}
.cdot{{width:8px;height:8px;border-radius:50%;margin-top:5px;flex-shrink:0;}}
.cbody{{flex:1;min-width:0;}}
.crel{{font-size:0.57rem;font-family:var(--font-mono);color:var(--muted2);margin-bottom:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.carr{{color:#3873ff;margin:0 3px;}}
.cname{{font-size:0.72rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;}}
.badge-new{{font-size:0.49rem;font-family:var(--font-mono);padding:2px 5px;border-radius:4px;flex-shrink:0;margin-top:3px;background:rgba(56,115,255,.1);color:#3873ff;}}
.badge-seen{{font-size:0.49rem;font-family:var(--font-mono);padding:2px 5px;border-radius:4px;flex-shrink:0;margin-top:3px;background:rgba(0,0,0,.04);color:var(--muted);}}

/* LEGEND */
#legend{{position:fixed;bottom:18px;left:16px;z-index:50;pointer-events:none;background:rgba(255,255,255,.92);backdrop-filter:blur(8px);border:1px solid var(--border);border-radius:9px;padding:8px 12px;display:flex;flex-direction:column;gap:4px;}}
.leg-item{{display:flex;align-items:center;gap:6px;font-size:0.56rem;font-family:var(--font-mono);color:var(--muted2);}}
.leg-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0;}}

/* HINT TOAST */
#hint-toast{{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:rgba(255,255,255,.96);backdrop-filter:blur(12px);border:1px solid var(--border2);border-radius:24px;padding:7px 16px;font-size:0.6rem;font-family:var(--font-mono);color:var(--muted2);z-index:400;pointer-events:none;transition:opacity .5s,transform .5s;white-space:nowrap;}}
#hint-toast.hide{{opacity:0;transform:translateX(-50%) translateY(6px);}}

/* INTRO */
#intro{{position:fixed;inset:0;background:#f7f8fc;display:flex;align-items:center;justify-content:center;flex-direction:column;gap:22px;z-index:999;}}
.intro-badge{{display:flex;align-items:center;gap:8px;padding:5px 14px;border-radius:20px;border:1px solid rgba(56,115,255,.25);background:rgba(56,115,255,.06);font-size:0.6rem;font-family:var(--font-mono);color:#3873ff;letter-spacing:1px;text-transform:uppercase;}}
.intro-title{{font-size:clamp(1.4rem,3vw,2rem);font-weight:800;text-align:center;letter-spacing:-1.5px;line-height:1.1;max-width:520px;}}
.intro-title em{{font-style:normal;color:#3873ff;}}
.intro-summary{{font-size:0.79rem;color:var(--muted2);text-align:center;max-width:430px;line-height:1.7;}}
.intro-counters{{display:flex;gap:36px;}}
.intro-ctr{{text-align:center;}}
.intro-num{{font-size:1.8rem;font-weight:800;font-family:var(--font-mono);background:linear-gradient(135deg,#3873ff,#9b59ff);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.intro-lbl{{font-size:0.55rem;color:var(--muted2);letter-spacing:1.5px;text-transform:uppercase;font-family:var(--font-mono);margin-top:2px;}}
.intro-steps{{display:flex;gap:10px;flex-wrap:wrap;justify-content:center;}}
.intro-step{{display:flex;align-items:center;gap:8px;padding:8px 13px;border-radius:8px;border:1px solid var(--border);background:var(--surface);font-size:0.64rem;color:var(--muted2);}}
.step-num{{width:20px;height:20px;border-radius:50%;background:rgba(56,115,255,.1);border:1px solid rgba(56,115,255,.25);color:#3873ff;font-size:0.58rem;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0;}}
.btn-explore{{padding:12px 44px;background:linear-gradient(135deg,rgba(56,115,255,.12),rgba(155,89,255,.12));border:1px solid rgba(56,115,255,.4);border-radius:10px;color:#3873ff;font-size:0.88rem;font-weight:700;cursor:pointer;font-family:var(--font-body);letter-spacing:-.3px;transition:all .2s;}}
.btn-explore:hover{{transform:translateY(-2px);box-shadow:0 10px 30px rgba(56,115,255,.15);}}

/* SVG */
.edge-line{{fill:none;stroke-width:1.8;stroke-opacity:0;transition:stroke-opacity .35s ease;pointer-events:none;}}
.edge-line.visible{{stroke-opacity:0.25;}}
.edge-line.active{{stroke-opacity:.95!important;stroke-width:2.5!important;}}
.edge-label{{
  font-family: var(--font-mono);
  font-size: 12px;
  pointer-events: none;
  transition: fill-opacity .3s;

  paint-order: stroke;
  stroke: rgba(255,255,255,0.95);
  stroke-width: 3px;
  stroke-linejoin: round;

  fill: #1a1f35;
  fill-opacity: 0;
}}

.edge-label.visible{{ fill-opacity: .55; }}
.edge-label.active{{ fill-opacity: 1; }}

.node-g{{cursor:pointer;}}
.node-body{{transition:filter .25s;}}
.node-g.revealed .node-body{{filter:drop-shadow(0 0 10px currentColor);}}
.node-g:hover .node-body{{filter:drop-shadow(0 0 18px currentColor) brightness(.85);}}
.node-g.selected .node-body{{filter:drop-shadow(0 0 22px currentColor) brightness(.80)!important;}}
.node-glow{{fill:none;stroke-width:1.5;opacity:0;transition:opacity .5s ease;}}
.node-g.revealed .node-glow{{opacity:.45;}}
.node-pulse{{fill:none;stroke-width:2;opacity:0;}}
.node-g.selected .node-pulse{{animation:pulse-circ 2s cubic-bezier(.4,0,.6,1) infinite;}}
@keyframes pulse-circ{{0%{{opacity:.6;r:20px;}}100%{{opacity:0;r:80px;}}}}
.node-label{{font-family:var(--font-body);font-weight:700;font-size:11px;fill:#1a2030;text-anchor:middle;dominant-baseline:central;pointer-events:none;opacity:0;transition:opacity .35s ease;}}
.node-g.revealed .node-label{{opacity:1;}}
</style>
</head>
<body>

<!-- INTRO -->
<div id="intro">
  <div class="intro-badge">📚 {he(subtitle)}</div>
  <div class="intro-title">{he(title)}<br><em>{he(subject)}</em></div>
  <div class="intro-summary">{he(summary[:190])}{'…' if len(summary)>190 else ''}</div>
  <div class="intro-counters">
    <div class="intro-ctr"><div class="intro-num">{len(nodes)}</div><div class="intro-lbl">Concepts</div></div>
    <div class="intro-ctr"><div class="intro-num">{len(edges)}</div><div class="intro-lbl">Connections</div></div>
    <div class="intro-ctr"><div class="intro-num">{len(clusters)}</div><div class="intro-lbl">Topics</div></div>
  </div>
  <div class="intro-steps">
    <div class="intro-step"><div class="step-num">1</div>Click a node to reveal it</div>
    <div class="intro-step"><div class="step-num">2</div>Connections animate in</div>
    <div class="intro-step"><div class="step-num">3</div>Drag · Zoom · Explore</div>
  </div>
  <button class="btn-explore" onclick="closeIntro()">Begin Exploring →</button>
</div>

<!-- TOP BAR -->
<div id="topbar">
  <div class="tb-brand">
    <div class="gem">📚</div>
    <div><div class="brand-title">{he(title[:42])}</div><div class="brand-sub">{he(subtitle)}</div></div>
  </div>
  <div class="tb-stats">
    <div><div class="sv" id="s-rev">0</div><div class="sl">Revealed</div></div>
    <div><div class="sv" id="s-conn">0</div><div class="sl">Links</div></div>
    <div><div class="sv" id="s-tot">{len(nodes)}</div><div class="sl">Total</div></div>
  </div>
  <div class="tb-progress">
    <div class="prog-track"><div class="prog-fill" id="prog-fill"></div></div>
    <div class="prog-pct" id="prog-pct">0%</div>
  </div>
  <div class="tb-div"></div>
  <div style="display:flex;gap:5px;">
    <button class="tb-btn" onclick="resetGraph()">↺ Reset</button>
    <button class="tb-btn" onclick="revealAll()">⊞ All</button>
    <button class="tb-btn" onclick="recenter()">⊙ Center</button>
  </div>
</div>

<!-- CANVAS (full page) -->
<div id="canvas-wrap"></div>

<!-- PANEL -->
<div id="panel">
  <div class="panel-tab" onclick="closePanel()">✕</div>
  <div class="panel-scroll" id="panel-scroll">
    <div id="panel-node-card" class="node-card" style="display:none;"></div>
    <div id="panel-conns" class="conn-section"></div>
  </div>
</div>

<!-- LEGEND -->
<div id="legend"></div>

<!-- HINT -->
<div id="hint-toast">Click the glowing center node · Drag to pan · Scroll to zoom</div>

<script>
const CLUSTERS = {clusters_js};
const NODES    = {nodes_js};
const EDGES    = {edges_js};

const clMap = Object.fromEntries(CLUSTERS.map(c=>[c.id,c]));
const nMap  = Object.fromEntries(NODES.map(n=>[n.id,n]));
const adj   = {{}};
NODES.forEach(n=>adj[n.id]=[]);
EDGES.forEach(e=>{{
  if(adj[e.s]) adj[e.s].push({{peer:e.t,rel:e.r,dir:'out'}});
  if(adj[e.t]) adj[e.t].push({{peer:e.s,rel:e.r,dir:'in'}});
}});

const revealed=new Set();
let selected=null,simNodes=null;
let simulation,zoomBeh,linkSel,eLabelSel,nodeGSel,currentTransform=d3.zoomIdentity;
let connCount=0;

const nodeColor=id=>{{const n=nMap[id];return(n&&clMap[n.c])?clMap[n.c].color:'#3873ff';}};
const hexRgb=hex=>parseInt(hex.slice(1,3),16)+','+parseInt(hex.slice(3,5),16)+','+parseInt(hex.slice(5,7),16);
const esc=t=>String(t??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

/* ── NODE SIZE: radius big enough to contain the label text ── */
function nodeSize(id) {{
  const label = (nMap[id]?.label || '').replace(/\\n/g,' ');
  const isCenter = id===NODES[0]?.id;
  const charW = 3.6;
  const minR  = isCenter ? 52 : 38;
  const r = Math.max(label.length * charW + 14, minR);
  return {{r, w: r*2, h: r*2}};
}}

function revealNode(id,delay){{
  if(!id||revealed.has(id)) return false;
  revealed.add(id);
  const ng=d3.select('#ng-'+id);
  ng.transition().delay(delay||0).duration(380).style('opacity',1);
  ng.classed('revealed',true);
  ng.selectAll('.node-label').transition().delay((delay||0)+120).duration(300).attr('opacity',1);
  updateStats(); return true;
}}

function selectNode(d){{
  if(!d) return;
  if(selected){{
    d3.select('#ng-'+selected.id).classed('selected',false);
    linkSel.classed('active',false);
    eLabelSel.classed('active',false);
  }}
  selected=d;
  d3.select('#ng-'+d.id).classed('selected',true);
  revealNode(d.id,0);
  const nbrs=adj[d.id]||[];
  let delay=0;
  nbrs.forEach(nb=>{{const isNew=revealNode(nb.peer,delay);if(isNew){{connCount++;delay+=50;}}}});
  EDGES.forEach(e=>{{
    const touches=(e.s===d.id||e.t===d.id),both=revealed.has(e.s)&&revealed.has(e.t);
    const mc=nMap[e.s]?nMap[e.s].c:'C1';
    if(touches&&both){{
      d3.select('#el-'+e.s+'-'+e.t).classed('visible',true).classed('active',true)
        .attr('marker-end','url(#arr-'+mc+')');
      d3.select('#elbl-'+e.s+'-'+e.t).classed('visible',true).classed('active',true);
    }}
  }});
  EDGES.forEach(e=>{{
    if(revealed.has(e.s)&&revealed.has(e.t)){{
      const mc=nMap[e.s]?nMap[e.s].c:'C1';
      d3.select('#el-'+e.s+'-'+e.t).classed('visible',true).attr('marker-end','url(#arr-'+mc+')');
    }}
  }});
  updateStats(); renderPanel(d,nbrs);
  document.getElementById('panel').classList.add('open');
  document.getElementById('canvas-wrap').classList.add('panel-open');
  document.getElementById('hint-toast').classList.add('hide');
}}

function closePanel(){{
  document.getElementById('panel').classList.remove('open');
  document.getElementById('canvas-wrap').classList.remove('panel-open');
}}

function renderPanel(d,nbrs){{
  const cl=clMap[d.c]||{{}},c=cl.color||'#3873ff',rgb=hexRgb(c);
  const card=document.getElementById('panel-node-card');
  card.style.display='block';
  card.innerHTML=`
    <div class="node-type-row">
      <div class="ndot" style="background:${{c}}"></div>
      <span class="ntype">${{esc(d.type||'node')}}</span>
      <span class="nbadge" style="background:rgba(${{rgb}},0.1);border:1px solid rgba(${{rgb}},0.22);color:${{c}}">${{esc(cl.name||'')}}</span>
    </div>
    <div class="ntitle">${{esc((d.label||'').replace(/\\n/g,' '))}}</div>
    <div class="ndesc">${{esc(d.desc||'')}}</div>`;
  const out=nbrs.filter(n=>n.dir==='out'),inc=nbrs.filter(n=>n.dir==='in');
  let html='';
  const mkCard=(nb,i,fromLabel,fromColor)=>{{
    const tn=nMap[nb.peer]||{{}},tc=nodeColor(nb.peer),isNew=!revealed.has(nb.peer);
    return `<div class="conn-card" style="animation-delay:${{i*35}}ms" onclick="selectNode(nMap['${{nb.peer}}'])">
      <div class="cdot" style="background:${{tc}}"></div>
      <div class="cbody">
        <div class="crel"><span style="color:${{fromColor}}">${{esc(fromLabel)}}</span><span class="carr">→</span><span style="color:var(--muted2)">${{esc(nb.rel)}}</span></div>
        <div class="cname">${{esc((tn.label||'').replace(/\\n/g,' '))}}</div>
      </div>
      <span class="${{isNew?'badge-new':'badge-seen'}}">${{isNew?'new':'shown'}}</span>
    </div>`;
  }};
  if(out.length){{html+=`<div class="conn-head">Connects to (${{out.length}})</div>`;out.forEach((nb,i)=>html+=mkCard(nb,i,(d.label||''),c));}}
  if(inc.length){{
    html+=`<div class="conn-head" style="margin-top:10px">Referenced by (${{inc.length}})</div>`;
    inc.forEach((nb,i)=>{{
      const tn=nMap[nb.peer]||{{}},tc=nodeColor(nb.peer),isNew=!revealed.has(nb.peer);
      html+=`<div class="conn-card" style="animation-delay:${{(out.length+i)*35}}ms" onclick="selectNode(nMap['${{nb.peer}}'])">
        <div class="cdot" style="background:${{tc}}"></div>
        <div class="cbody">
          <div class="crel"><span style="color:${{tc}}">${{esc((tn.label||'').replace(/\\n/g,' '))}}</span><span class="carr">→</span><span style="color:var(--muted2)">${{esc(nb.rel)}}</span></div>
          <div class="cname">${{esc((d.label||'').replace(/\\n/g,' '))}}</div>
        </div>
        <span class="${{isNew?'badge-new':'badge-seen'}}">${{isNew?'new':'shown'}}</span>
      </div>`;
    }});
  }}
  document.getElementById('panel-conns').innerHTML=html;
  document.getElementById('panel-scroll').scrollTop=0;
}}

function updateStats(){{
  const r=revealed.size,t=NODES.length;
  document.getElementById('s-rev').textContent=r;
  document.getElementById('s-conn').textContent=connCount;
  document.getElementById('prog-fill').style.width=(r/t*100)+'%';
  document.getElementById('prog-pct').textContent=Math.round(r/t*100)+'%';
}}

function resetGraph(){{
  revealed.clear();connCount=0;selected=null;
  if(nodeGSel)nodeGSel.classed('revealed',false).classed('selected',false).style('opacity',0);
  if(linkSel)linkSel.classed('visible',false).classed('active',false).attr('marker-end',null);
  if(eLabelSel)eLabelSel.classed('visible',false).classed('active',false);
  closePanel();
  document.getElementById('hint-toast').classList.remove('hide');
  updateStats();
  setTimeout(()=>revealNode(NODES[0]?.id,0),300);
}}

function revealAll(){{
  NODES.forEach(n=>revealNode(n.id,0));
  EDGES.forEach(e=>{{
    const mc=nMap[e.s]?nMap[e.s].c:'C1';
    d3.select('#el-'+e.s+'-'+e.t).classed('visible',true).attr('marker-end','url(#arr-'+mc+')');
  }});
  updateStats();
}}

function recenter(){{
  const el=document.getElementById('canvas-wrap');
  const W=el.clientWidth,H=el.clientHeight;
  const c=simNodes&&simNodes.find(n=>n.id===NODES[0]?.id);
  const tx=c?W/2-c.x:W/2,ty=c?H/2-c.y:H/2;
  d3.select('#canvas-wrap svg').transition().duration(700).ease(d3.easeCubicOut)
    .call(zoomBeh.transform,d3.zoomIdentity.translate(tx,ty).scale(1));
}}

function closeIntro(){{
  const el=document.getElementById('intro');
  el.style.transition='opacity .4s ease';el.style.opacity='0';
  setTimeout(()=>el.style.display='none',420);
}}

window.closeIntro=closeIntro;window.resetGraph=resetGraph;
window.revealAll=revealAll;window.recenter=recenter;window.closePanel=closePanel;

document.addEventListener('keydown',ev=>{{
  if(ev.target.tagName==='INPUT') return;
  if(ev.key==='r'||ev.key==='R') resetGraph();
  if(ev.key==='a'||ev.key==='A') revealAll();
  if(ev.key==='f'||ev.key==='F') recenter();
  if(ev.key==='Escape')closePanel();
}});

function initD3(){{
  const wrap=document.getElementById('canvas-wrap');
  const W=wrap.clientWidth,H=wrap.clientHeight;

  const legEl=document.getElementById('legend');
  CLUSTERS.forEach(c=>{{legEl.innerHTML+=`<div class="leg-item"><div class="leg-dot" style="background:${{c.color}}"></div>${{esc(c.name)}}</div>`;}});

  const svg=d3.select('#canvas-wrap').append('svg').attr('width','100%').attr('height','100%');
  const defs=svg.append('defs');

  CLUSTERS.forEach(c=>{{
    defs.append('marker').attr('id','arr-'+c.id)
      .attr('viewBox','0 -4 9 8').attr('refX',9).attr('refY',0)
      .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto')
      .append('path').attr('d','M0,-4L9,0L0,4')
      .attr('fill',c.color).attr('fill-opacity','0.85');
  }});

  const g=svg.append('g');
  zoomBeh=d3.zoom().scaleExtent([0.05,8])
    .filter(ev=>!ev.target.closest||!ev.target.closest('.node-g'))
    .on('zoom',ev=>{{currentTransform=ev.transform;g.attr('transform',ev.transform);}});
  svg.call(zoomBeh);

  simNodes=NODES.map(n=>({{...n}}));
  const nById=Object.fromEntries(simNodes.map(n=>[n.id,n]));

  const sizeCache={{}};
  simNodes.forEach(n=>{{sizeCache[n.id]=nodeSize(n.id);}});

  const simEdges=EDGES.map(e=>({{...e,source:nById[e.s],target:nById[e.t]}}))
                      .filter(e=>e.source&&e.target);

  simulation = d3.forceSimulation(simNodes)
    .force('link', d3.forceLink(simEdges).id(d=>d.id)
      .distance(e=>{{
        const sr = sizeCache[e.source.id]?.r || 40;
        const tr = sizeCache[e.target.id]?.r || 40;
        return sr + tr + 120;
      }})
      .strength(0.18))
    .force('charge', d3.forceManyBody()
      .strength(d=> -1*(sizeCache[d.id]?.r || 40)*40)
      .distanceMax(1200))
    .force('center', d3.forceCenter(W/2, H/2))
    .force('collide', d3.forceCollide()
      .radius(d => (sizeCache[d.id]?.r || 40) + 18)
      .strength(1.0).iterations(4))
    .force('cluster', clusterForce(0.045))
    .alphaDecay(0.010)
    .velocityDecay(0.35);

  linkSel=g.append('g').selectAll('line')
    .data(simEdges).enter().append('line')
    .attr('class','edge-line')
    .attr('id',d=>'el-'+d.s+'-'+d.t)
    .attr('stroke',d=>nodeColor(d.s))
    .attr('marker-end',null);

  eLabelSel=g.append('g').selectAll('text')
    .data(simEdges).enter().append('text')
    .attr('class','edge-label')
    .attr('id',d=>'elbl-'+d.s+'-'+d.t)
    .attr('fill',d=>nodeColor(d.s))
    .text(d=>d.r);

  nodeGSel=g.append('g').selectAll('.node-g')
    .data(simNodes).enter().append('g')
    .attr('class','node-g').attr('id',d=>'ng-'+d.id)
    .style('opacity',0)
    .on('click',(ev,d)=>{{ev.stopPropagation();selectNode(d);}})
    .call(d3.drag()
      .on('start',(ev,d)=>{{if(!ev.active)simulation.alphaTarget(0.3).restart();d.fx=d.x;d.fy=d.y;}})
      .on('drag', (ev,d)=>{{d.fx=ev.x;d.fy=ev.y;}})
      .on('end',  (ev,d)=>{{if(!ev.active)simulation.alphaTarget(0);d.fx=null;d.fy=null;}}));

  nodeGSel.append('circle').attr('class','node-pulse')
    .each(function(d){{
      const s=sizeCache[d.id];
      d3.select(this).attr('r',s.r).attr('stroke',nodeColor(d.id));
    }});

  nodeGSel.append('circle').attr('class','node-glow')
    .each(function(d){{
      const s=sizeCache[d.id];
      d3.select(this).attr('r',s.r+6).attr('stroke',nodeColor(d.id));
    }});

  nodeGSel.append('circle').attr('class','node-body')
    .each(function(d){{
      const s=sizeCache[d.id],c=nodeColor(d.id),rgb=hexRgb(c);
      const isCenter=d.id===NODES[0]?.id;
      d3.select(this)
        .attr('r',s.r)
        .attr('fill', isCenter ? c : 'rgba('+rgb+',.18)')
        .attr('stroke',c).attr('stroke-width',isCenter?2.5:2);
    }});

  nodeGSel.each(function(d){{
    const label=(d.label||'').replace(/\\n/g,' ');
    const words=label.split(' ');
    const isCenter=d.id===NODES[0]?.id;
    const c=nodeColor(d.id),rgb=hexRgb(c);
    const fs=isCenter?12:11;
    const fill=isCenter?'#fff':'rgba('+rgb+',1)';
    const fw=isCenter?'800':'700';
    const el=d3.select(this);

    let lines;
    if(words.length>=3){{
      const mid=Math.ceil(words.length/2);
      lines=[words.slice(0,mid).join(' '), words.slice(mid).join(' ')];
    }} else {{
      lines=[label];
    }}
    const lineH=fs+3;
    lines.forEach((line,i)=>{{
      el.append('text').attr('class','node-label')
        .attr('dy', ((i-(lines.length-1)/2)*lineH)+'px')
        .attr('text-anchor','middle')
        .attr('dominant-baseline','central')
        .attr('font-size',fs+'px')
        .attr('fill',fill)
        .attr('font-weight',fw)
        .attr('pointer-events','none')
        .attr('opacity',0)
        .text(line);
    }});
  }});

  simulation.on('tick',()=>{{
    linkSel.each(function(d){{
      const src=d.source,tgt=d.target;
      const sr=sizeCache[src.id]?.r||38;
      const tr=sizeCache[tgt.id]?.r||38;
      const dx=tgt.x-src.x, dy=tgt.y-src.y;
      const len=Math.sqrt(dx*dx+dy*dy)||1;
      const ux=dx/len, uy=dy/len;
      d3.select(this)
        .attr('x1',src.x+ux*sr).attr('y1',src.y+uy*sr)
        .attr('x2',tgt.x-ux*(tr+2)).attr('y2',tgt.y-uy*(tr+2));
    }});
    eLabelSel.attr('x',d=>(d.source.x+d.target.x)/2).attr('y',d=>(d.source.y+d.target.y)/2);
    nodeGSel.attr('transform',d=>'translate('+d.x+','+d.y+')');
  }});

  setTimeout(()=>revealNode(NODES[0]?.id,0),500);
  setTimeout(()=>recenter(),2800);
  updateStats();
}}

function clusterForce(strength){{
  return function(alpha){{
    if(!simNodes) return;
    const centroids={{}};
    simNodes.forEach(n=>{{
      if(!centroids[n.c])centroids[n.c]={{x:0,y:0,n:0}};
      centroids[n.c].x+=(n.x||0);centroids[n.c].y+=(n.y||0);centroids[n.c].n++;
    }});
    Object.values(centroids).forEach(c=>{{c.x/=c.n;c.y/=c.n;}});
    simNodes.forEach(n=>{{
      const c=centroids[n.c];if(!c)return;
      n.vx=(n.vx||0)+(c.x-n.x)*strength*alpha;
      n.vy=(n.vy||0)+(c.y-n.y)*strength*alpha;
    }});
  }};
}}

window.addEventListener('load',()=>{{
  if(typeof d3==='undefined'){{console.error('D3 not loaded');return;}}
  if(!NODES.length){{console.error('No nodes');return;}}
  initD3();
}});
window.addEventListener('resize',()=>{{
  if(!simulation)return;
  const el=document.getElementById('canvas-wrap');
  simulation.force('center',d3.forceCenter(el.clientWidth/2,el.clientHeight/2));
  simulation.alpha(0.05).restart();
}});
</script>
</body>
</html>"""