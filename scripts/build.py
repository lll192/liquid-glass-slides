#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
liquid-glass-slides · build.py
================================
Zero-dependency generator: read an outline JSON, compose the matching
single-page layout snippets, inline the engine CSS/JS, and emit ONE
self-contained HTML file (double-click ready, no external assets).

Usage:
  python build.py --outline my-talk.json --out my-talk.html
  python build.py my-talk.json                      # -> ./my-talk.html

Outline schema (see references/outline-schema.md):
  {
    "schema_version": "2.0",
    "deck_id": "my-talk",
    "lang": "zh-CN",
    "title": "Deck title",
    "theme": { "colors": ["#0A84FF","#5E5CE6","#30D158"], "accent": "#0A84FF" },  # optional: 3 blob/particle colors + 1 accent
    "slides": [
      { "slide_id": "opening", "layout": "cover", "eyebrow": "...", "title": "...", "subtitle": "..." },
      { "slide_id": "key-points", "layout": "grid-cards", "items": [ {"num":"01","title":"..","desc":".."}, ... ] },
      ...
    ]
  }

Available layouts (templates/single-page/*.html):
  cover, toc, section-divider, bullets, two-column, grid-cards, big-quote,
  stat-highlight, kpi-grid, timeline, comparison, image-frame,
  object-float, closing, chart, data-table, process-flow, concept-map

A slide with a "chart" field renders the `chart` layout (split: text column on
the left, chart card on the right — text never gets pushed to the edges) and
embeds an ECharts visualization (the library is inlined automatically; see
references/echarts-charts.md):
  { "layout":"chart", "eyebrow":"..", "title":"..", "note":"..",
    "takeaway":"..",                     # optional highlighted key point
    "chart": { "height":"min(50vh,440px)",
               "option": { "xAxis":{...}, "yAxis":{...}, "series":[...] } },
    "caption":".." }

A slide with a "three" field enables a Three.js scene on the shared background
canvas (library inlined automatically only when used; see references/three-3d.md).
The scene renders BEHIND the content and swaps in as the slide becomes visible:
  { "layout":"cover", "title":"..", "three": { "scene": "field" } }  # field | nebula | network | petals | waves

Snippet placeholders:
  {{field}}            scalar substitution
  {{#items}} ... {{/items}}   repeat block; inside use {{item.x}} and {{i}} (0-based)
  {{#hero}} ... {{/hero}}     optional block; renders once if the field is truthy
"""
import argparse
import base64
import binascii
import html
import json
import os
import re
import sys
from urllib.parse import unquote_to_bytes

try:
    from validate_outline import validate_outline
    from migrate_outline import migrate_outline
except ImportError:  # pragma: no cover - module execution fallback
    from scripts.validate_outline import validate_outline
    from scripts.migrate_outline import migrate_outline

# ---------- tiny template engine ----------
BLOCK_RE = re.compile(r'\{\{#(\w+)\}\}(.*?)\{\{/\1\}\}', re.S)
SCALAR_RE = re.compile(r'\{\{(\w+(?:\.\w+)*)\}\}')

# ---------- theme helpers ----------
def _hex_to_rgb(h):
    h = (h or '').lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    h = (h + '000000')[:6]
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def _lighten(h, amt):
    r, g, b = _hex_to_rgb(h)
    r = int(round(r + (255 - r) * amt))
    g = int(round(g + (255 - g) * amt))
    b = int(round(b + (255 - b) * amt))
    return '#%02X%02X%02X' % (r, g, b)

def _rgba(h, a):
    r, g, b = _hex_to_rgb(h)
    return 'rgba(%d,%d,%d,%.2f)' % (r, g, b, a)

_DEFAULT_THEME_COLORS = ['#0A84FF', '#FF375F', '#30D158']

def build_theme(outline):
    """Return (theme_css, theme_colors).

    theme_css is injected into :root and drives the 3 background blobs, the
    accent text color, and every glow/shadow. theme_colors (3 hex strings) is
    forwarded to Three.js so the live particles use the exact same palette.
    If no theme is given, a balanced blue/red/green default is used.
    """
    theme = outline.get('theme')
    colors = list(_DEFAULT_THEME_COLORS)
    accent = colors[0]
    extra = {}
    if isinstance(theme, dict):
        if theme.get('colors'):
            cols = [str(c) for c in theme['colors'] if c]
            while len(cols) < 3:
                cols.append(cols[-1] if cols else '#0A84FF')
            colors = cols[:3]
        if theme.get('accent'):
            accent = str(theme['accent'])
        # legacy / free-form CSS-var overrides (anything other than name/colors/accent)
        for k, v in theme.items():
            if k in ('name', 'colors', 'accent'):
                continue
            extra['--%s' % k] = str(v)
    accent2 = _lighten(accent, 0.34)
    vars = {
        '--accent': accent,
        '--accent-rgb': '%d,%d,%d' % _hex_to_rgb(accent),
        '--accent-2': accent2,
        '--accent2-rgb': '%d,%d,%d' % _hex_to_rgb(accent2),
        '--blob-1': _rgba(colors[0], 0.30),
        '--blob-2': _rgba(colors[1], 0.26),
        '--blob-3': _rgba(colors[2], 0.22),
    }
    vars.update(extra)
    theme_css = ' '.join('%s:%s;' % (k, v) for k, v in vars.items())
    return theme_css, colors

# Liquid-glass ECharts theme + safe init. Applied to every chart so the
# deck stays visually consistent (transparent canvas, iOS palette, frosted
# tooltip, rounded bars, smooth lines) without the author hand-skinning.
CHART_INIT_JS = r'''
var PALETTE=['#0A84FF','#5AC8FA','#30D158','#FF9F0A','#BF5AF2','#FF375F'];
function applyTheme(opt){
  opt=JSON.parse(JSON.stringify(opt));
  opt.backgroundColor=opt.backgroundColor||'transparent';
  opt.color=opt.color||PALETTE;
  opt.textStyle=Object.assign({fontFamily:'-apple-system,"SF Pro Display","PingFang SC","Microsoft YaHei",sans-serif',color:'rgba(29,29,31,.72)',fontSize:13},opt.textStyle||{});
  opt.tooltip=Object.assign({trigger:'item',backgroundColor:'rgba(255,255,255,.62)',borderColor:'rgba(255,255,255,.55)',borderWidth:1,padding:[10,14],textStyle:{color:'#1d1d1f'},extraCssText:'backdrop-filter:blur(14px) saturate(180%);-webkit-backdrop-filter:blur(14px) saturate(180%);border-radius:14px;box-shadow:0 12px 40px rgba(30,60,140,.18);'},opt.tooltip||{});
  ['xAxis','yAxis'].forEach(function(k){
    var a=opt[k]; if(!a) return;
    var arr=Array.isArray(a)?a:[a];
    arr.forEach(function(ax){
      if(ax.type==='category'){ ax.axisTick=ax.axisTick||{}; ax.axisTick.show=false; ax.axisLine=ax.axisLine||{}; ax.axisLine.lineStyle=Object.assign({color:'rgba(29,29,31,.14)'},ax.axisLine.lineStyle||{}); ax.axisLabel=Object.assign({color:'rgba(29,29,31,.55)'},ax.axisLabel||{}); }
      if(ax.type==='value'){ ax.axisLine=ax.axisLine||{}; ax.axisLine.show=false; ax.splitLine=ax.splitLine||{}; if(ax.splitLine.show!==false){ ax.splitLine.lineStyle=Object.assign({color:'rgba(29,29,31,.07)'},ax.splitLine.lineStyle||{}); } ax.axisLabel=Object.assign({color:'rgba(29,29,31,.5)'},ax.axisLabel||{}); }
    });
    opt[k]=Array.isArray(a)?arr:arr[0];
  });
  (opt.series||[]).forEach(function(s){
    if(s.type==='bar'){ s.itemStyle=Object.assign({borderRadius:[6,6,0,0]},s.itemStyle||{}); if(s.barMaxWidth===undefined) s.barMaxWidth=40; }
    if(s.type==='line'){ s.smooth=s.smooth!==undefined?s.smooth:true; s.symbol='circle'; s.symbolSize=s.symbolSize||7; s.lineStyle=Object.assign({width:3},s.lineStyle||{}); if(s.areaStyle){ s.areaStyle=Object.assign({opacity:.20},s.areaStyle); } }
    if(s.type==='pie'){ s.radius=s.radius||['42%','70%']; s.itemStyle=Object.assign({borderColor:'rgba(255,255,255,.92)',borderWidth:2},s.itemStyle||{}); }
  });
  return opt;
}
function initCharts(){
  if(typeof echarts==='undefined') return;
  __LG_CHARTS_RAW__.forEach(function(c){
    var el=document.getElementById(c.id); if(!el||el._ec) return;
    var ch=echarts.init(el); ch.setOption(applyTheme(c.option)); el._ec=ch;
  });
}
if(document.readyState!=='loading') initCharts(); else document.addEventListener('DOMContentLoaded',initCharts);
window.addEventListener('resize',function(){ document.querySelectorAll('.echart').forEach(function(el){ if(el._ec) el._ec.resize(); }); });
window.addEventListener('load',function(){ setTimeout(function(){ document.querySelectorAll('.echart').forEach(function(el){ if(el._ec) el._ec.resize(); }); },60); });
'''

# Liquid-glass Three.js layer: ONE shared WebGL canvas behind all content.
# The active slide's scene is swapped via IntersectionObserver,
# so we never spawn more than one WebGL context. The library + this script are inlined
# ONLY when a slide declares a "three" field (keeps dependency-free decks small).
THREE_INIT_JS = r'''
if(typeof THREE!=='undefined'){ (function(){
  var canvas=document.getElementById('lg-three'); if(!canvas) return;
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var renderer;
  try { renderer=new THREE.WebGLRenderer({canvas:canvas,alpha:true,antialias:true}); }
  catch(e){ return; }   // WebGL unavailable -> keep the static light gradient
  renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));
  var THEME_HEX=window.__LG_THEME_HEX__||['#0A84FF','#FF375F','#30D158'];
  var PALETTE=THEME_HEX.map(function(h){return parseInt(h.replace('#','0x'));});
  function rand(a,b){ return a+Math.random()*(b-a); }
  // Soft round sprite so particles read as bokeh ON A LIGHT background
  // (additive blending would wash them out to white on the light theme).
  function softSprite(){
    var c=document.createElement('canvas'); c.width=c.height=64; var g=c.getContext('2d');
    var grd=g.createRadialGradient(32,32,0,32,32,32);
    grd.addColorStop(0,'rgba(255,255,255,1)'); grd.addColorStop(.35,'rgba(255,255,255,.85)');
    grd.addColorStop(1,'rgba(255,255,255,0)'); g.fillStyle=grd; g.beginPath(); g.arc(32,32,32,0,7); g.fill();
    return new THREE.CanvasTexture(c);
  }
  var SPRITE=softSprite();
  // Elongated soft sprite: reads as a drifting petal / leaf rather than a dot.
  function petalSprite(){
    var c=document.createElement('canvas'); c.width=c.height=64; var g=c.getContext('2d');
    g.translate(32,32); g.scale(1,0.58);
    var grd=g.createRadialGradient(0,0,0,0,0,30);
    grd.addColorStop(0,'rgba(255,255,255,1)'); grd.addColorStop(.4,'rgba(255,255,255,.8)');
    grd.addColorStop(1,'rgba(255,255,255,0)'); g.fillStyle=grd; g.beginPath(); g.arc(0,0,30,0,7); g.fill();
    return new THREE.CanvasTexture(c);
  }
  var PETAL=petalSprite();
  function particleScene(o){
    o=o||{}; var count=o.count||1100, spread=o.spread||80;
    var scene=new THREE.Scene();
    var cam=new THREE.PerspectiveCamera(60,1,0.1,2000); cam.position.z=o.camZ||70;
    var geo=new THREE.BufferGeometry(); var pos=new Float32Array(count*3); var col=new Float32Array(count*3);
    for(var i=0;i<count;i++){ pos[i*3]=rand(-spread,spread); pos[i*3+1]=rand(-spread*0.6,spread*0.6); pos[i*3+2]=rand(-spread,spread);
      var c=new THREE.Color(PALETTE[i%PALETTE.length]); col[i*3]=c.r; col[i*3+1]=c.g; col[i*3+2]=c.b; }
    geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
    geo.setAttribute('color',new THREE.BufferAttribute(col,3));
    var mat=new THREE.PointsMaterial({size:o.size||0.95,map:SPRITE,vertexColors:true,transparent:true,opacity:o.opacity||0.9,depthWrite:false,blending:THREE.NormalBlending});
    var pts=new THREE.Points(geo,mat); scene.add(pts);
    return {scene:scene,camera:cam,update:function(t){ pts.rotation.y=t*0.04*(o.speed||1); pts.rotation.x=Math.sin(t*0.1)*0.08; }};
  }
  // Drifting petals / falling leaves: soft elongated motes sinking slowly with
  // a lateral sway — suits literary, historical and nature topics.
  function petalsScene(o){
    o=o||{}; var count=o.count||420, W=o.spread||55, H=o.H||34;
    var scene=new THREE.Scene();
    var cam=new THREE.PerspectiveCamera(60,1,0.1,2000); cam.position.z=o.camZ||52;
    var pos=new Float32Array(count*3), col=new Float32Array(count*3);
    var baseX=new Float32Array(count), phase=new Float32Array(count), fall=new Float32Array(count);
    for(var i=0;i<count;i++){
      baseX[i]=rand(-W,W); phase[i]=rand(0,6.28); fall[i]=rand(1.4,3.4);
      pos[i*3]=baseX[i]; pos[i*3+1]=rand(-H,H); pos[i*3+2]=rand(-24,14);
      var c=new THREE.Color(PALETTE[i%PALETTE.length]); col[i*3]=c.r; col[i*3+1]=c.g; col[i*3+2]=c.b;
    }
    var geo=new THREE.BufferGeometry();
    geo.setAttribute('position',new THREE.BufferAttribute(pos,3));
    geo.setAttribute('color',new THREE.BufferAttribute(col,3));
    var pts=new THREE.Points(geo,new THREE.PointsMaterial({size:o.size||1.7,map:PETAL,vertexColors:true,transparent:true,opacity:o.opacity||0.8,depthWrite:false,blending:THREE.NormalBlending}));
    scene.add(pts);
    return {scene:scene,camera:cam,update:function(t,dt){
      var p=geo.attributes.position.array;
      for(var i=0;i<count;i++){
        var y=p[i*3+1]-fall[i]*(dt||0.016); if(y<-H) y=H;
        p[i*3+1]=y; p[i*3]=baseX[i]+Math.sin(t*0.55+phase[i])*3.4;
      }
      geo.attributes.position.needsUpdate=true;
    }};
  }
  // Flowing wave lines: layered sine ribbons undulating gently — abstract,
  // elegant; fits flow/narrative/time motifs without literal objects.
  function wavesScene(o){
    o=o||{}; var lines=o.lines||4, N=140, W2=46;
    var scene=new THREE.Scene();
    var cam=new THREE.PerspectiveCamera(55,1,0.1,2000); cam.position.z=o.camZ||34;
    var refs=[]; var y0=[-9,-3,3.2,9];
    for(var li=0;li<lines;li++){
      var pts=[];
      for(var j=0;j<N;j++) pts.push(new THREE.Vector3(-W2+2*W2*j/(N-1), y0[li%4], 0));
      var g=new THREE.BufferGeometry().setFromPoints(pts);
      var ln=new THREE.Line(g,new THREE.LineBasicMaterial({color:PALETTE[li%PALETTE.length],transparent:true,opacity:0.34}));
      scene.add(ln); refs.push({g:g,y0:y0[li%4],ph:li*1.7,sp:0.5+li*0.14});
    }
    return {scene:scene,camera:cam,update:function(t){
      refs.forEach(function(r){
        var p=r.g.attributes.position.array;
        for(var j=0;j<N;j++){ var x=p[j*3]; p[j*3+1]=r.y0+Math.sin(x*0.085+t*r.sp+r.ph)*2.7; }
        r.g.attributes.position.needsUpdate=true;
      });
    }};
  }
  function networkScene(o){
    o=o||{}; var n=o.count||30, spread=o.spread||15;
    var scene=new THREE.Scene();
    var cam=new THREE.PerspectiveCamera(55,1,0.1,2000); cam.position.z=o.camZ||26;
    var nodes=[]; for(var i=0;i<n;i++){ nodes.push(new THREE.Vector3(rand(-spread,spread),rand(-spread*0.6,spread*0.6),rand(-spread*0.6,spread*0.6))); }
    var g=new THREE.BufferGeometry().setFromPoints(nodes);
    var pts=new THREE.Points(g,new THREE.PointsMaterial({size:0.95,map:SPRITE,color:PALETTE[0],transparent:true,opacity:0.95,depthWrite:false,blending:THREE.NormalBlending}));
    scene.add(pts);
    var seg=[]; for(var a=0;a<n;a++){ for(var b=a+1;b<n;b++){ if(nodes[a].distanceTo(nodes[b])<spread*0.62){ seg.push(nodes[a],nodes[b]); } } }
    var lg=new THREE.BufferGeometry().setFromPoints(seg);
    var lines=new THREE.LineSegments(lg,new THREE.LineBasicMaterial({color:(PALETTE[1]||PALETTE[0]),transparent:true,opacity:0.32}));
    scene.add(lines);
    return {scene:scene,camera:cam,update:function(t){ scene.rotation.y=t*0.12; }};
  }
  // Procedural water material. It renders a transparent light field behind the
  // slide content; the DOM ripple layer remains as the static/print fallback.
  // Arguments are encoded in the scene name for deterministic builds:
  // ripple:<rings|flow|caustic>:<bottom|bottom-right|edge|full>:<subtle|hero>:<seed>
  function rippleScene(pattern,zone,intensity,seed){
    var scene=new THREE.Scene();
    var cam=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
    var patternMap={rings:0,flow:1,caustic:2};
    var zoneMap={bottom:0,'bottom-right':1,edge:2,full:3};
    var strength=intensity==='hero'?0.68:0.38;
    var mat=new THREE.ShaderMaterial({
      transparent:true,depthWrite:false,depthTest:false,
      uniforms:{
        uTime:{value:0},uResolution:{value:new THREE.Vector2(1,1)},
        uPattern:{value:patternMap[pattern]===undefined?0:patternMap[pattern]},
        uZone:{value:zoneMap[zone]===undefined?0:zoneMap[zone]},
        uIntensity:{value:strength},uSeed:{value:parseFloat(seed)||0},
        uColorA:{value:new THREE.Color(PALETTE[0])},
        uColorB:{value:new THREE.Color(PALETTE[1]||PALETTE[0])}
      },
      vertexShader:'varying vec2 vUv;void main(){vUv=uv;gl_Position=vec4(position.xy,0.0,1.0);}',
      fragmentShader:[
        'precision highp float;',
        'varying vec2 vUv;',
        'uniform float uTime,uPattern,uZone,uIntensity,uSeed;',
        'uniform vec2 uResolution;',
        'uniform vec3 uColorA,uColorB;',
        'float ringAt(vec2 uv,vec2 c,float phase){',
        '  float aspect=uResolution.x/max(uResolution.y,1.0);',
        '  vec2 p=(uv-c)*vec2(aspect,1.0);',
        '  float w=.5+.5*sin(length(p)*74.0-phase);',
        '  return pow(max(w,0.0),12.0);',
        '}',
        'float zoneMask(vec2 uv){',
        '  if(uZone<.5) return smoothstep(.28,.82,1.0-uv.y);',
        '  if(uZone<1.5) return 1.0-smoothstep(.16,.78,distance(uv,vec2(.82,.20)));',
        '  if(uZone<2.5) return smoothstep(.32,.72,length((uv-.5)*vec2(1.18,1.0)));',
        '  return 1.0;',
        '}',
        'void main(){',
        '  vec2 uv=vUv;float t=uTime*.34+uSeed*.173;float v=0.0;',
        '  if(uPattern<.5){',
        '    v=ringAt(uv,vec2(.78,.24),t*2.0);',
        '    v+=.72*ringAt(uv,vec2(.24,.72),t*1.65+2.1);',
        '    v+=.48*ringAt(uv,vec2(.52,.42),t*1.3+4.2);',
        '  }else if(uPattern<1.5){',
        '    float y=uv.y+sin(uv.x*8.0+t)*.028+sin(uv.x*17.0-t*.7)*.012;',
        '    float bands=.5+.5*sin(y*76.0-t*2.2);',
        '    v=pow(max(bands,0.0),13.0)+.35*pow(.5+.5*sin(y*38.0+t),10.0);',
        '  }else{',
        '    vec2 q=uv*vec2(12.0,9.0);',
        '    float a=sin(q.x+sin(q.y*1.21+t)+uSeed);',
        '    float b=sin(q.y*1.37+sin(q.x*.83-t*.8));',
        '    float c=sin((q.x+q.y)*.74+sin(q.x-q.y+t*.6));',
        '    v=pow(clamp(abs((a+b+c)/3.0),0.0,1.0),7.0)*1.65;',
        '  }',
        '  float mask=zoneMask(uv);',
        '  vec3 col=mix(uColorA,uColorB,clamp(uv.x+v*.18,0.0,1.0));',
        '  col=mix(col,vec3(1.0),clamp(v*.72,0.0,.82));',
        '  float alpha=clamp(v,0.0,1.0)*mask*uIntensity*.42;',
        '  gl_FragColor=vec4(col,alpha);',
        '}'
      ].join('')
    });
    var quad=new THREE.Mesh(new THREE.PlaneGeometry(2,2),mat); scene.add(quad);
    return {scene:scene,camera:cam,update:function(t){mat.uniforms.uTime.value=t;},
      resize:function(w,h){mat.uniforms.uResolution.value.set(w,h);}};
  }
  var FACTORY={'field':function(){return particleScene({count:1100,spread:80,size:0.95,opacity:0.9,speed:1,camZ:72});},
              'nebula':function(){return particleScene({count:1700,spread:54,size:1.15,opacity:0.95,speed:1.7,camZ:62});},
              'network':function(){return networkScene({count:30,spread:15});},
              'petals':function(){return petalsScene({});},
              'waves':function(){return wavesScene({});},
              'ripple':function(pattern,zone,intensity,seed){return rippleScene(pattern,zone,intensity,seed);}};
  // Scene name may carry an argument: "object:torusKnot" -> FACTORY.object('torusKnot')
  var built={}; function get(n){ if(!n||built[n]) return built[n];
    var parts=n.split(':'); var f=FACTORY[parts[0]];
    if(f) built[n]=f.apply(null,parts.slice(1));
    return built[n]; }
  var used = window.__LG_THREE_USED__||[]; used.forEach(get);
  var slides=Array.prototype.slice.call(document.querySelectorAll('.slide'));
  var vis={}, active=null;
  function pick(){ var best=null,br=0; slides.forEach(function(s){ var r=vis[s.getAttribute('data-idx')]||0; if(r>br){br=r;best=s;} });
    active=(best&&br>0)?(best.getAttribute('data-three')||null):null; }
  var io=new IntersectionObserver(function(es){ es.forEach(function(e){ vis[e.target.getAttribute('data-idx')]=e.intersectionRatio; }); pick(); },{threshold:[0,0.25,0.5,0.75,1]});
  slides.forEach(function(s){ io.observe(s); });
  var clock=new THREE.Clock(); var last=null;
  function frame(){ requestAnimationFrame(frame); var et=clock.getElapsedTime();
    var dt=(last===null||et<last)?0.016:Math.min(et-last,0.05); last=et;
    var a=get(active); if(a){ a.update(et,dt); renderer.render(a.scene,a.camera); } else renderer.clear(); }
  function resize(){ var w=window.innerWidth,h=window.innerHeight; renderer.setSize(w,h,false);
    Object.keys(built).forEach(function(k){ var s=built[k]; if(s.camera.isPerspectiveCamera){ s.camera.aspect=w/h; s.camera.updateProjectionMatrix(); }
      if(s.resize) s.resize(w,h); }); }
  window.addEventListener('resize',resize); resize();
  if(reduce){ var a=get(active)||get(used[0]); if(a) renderer.render(a.scene,a.camera); return; }
  frame();
})(); }
'''


# Particle-storm presets (dense drifting point clouds: field / nebula) read as
# "busy" and clutter content pages. They are reserved for the COVER slide only;
# on every other slide build.py remaps them to a calm preset so the deck stays
# clean. The cover is guaranteed to carry the storm (auto-added if missing).
PARTICLE_STORM = {'field', 'nebula'}
COVER_STORM = 'field'
CALM_FALLBACK = None
REMOVED_THREE_SCENES = {'object', 'orbs'}
RIPPLE_PATTERNS = {'rings', 'flow', 'caustic'}
RIPPLE_ZONES = {'bottom', 'bottom-right', 'edge', 'full'}
RIPPLE_INTENSITIES = {'subtle', 'hero'}
RIPPLE_MOTIONS = {'static', 'drift', 'pulse'}
AUTO_RIPPLE_DENSE_LAYOUTS = {
    'bullets', 'grid-cards', 'kpi-grid', 'comparison', 'two-column',
    'timeline', 'toc',
}
IMAGE_FIELDS = {'hero', 'image'}


def normalize_ripple(surface, slide_number):
    """Validate an optional surface.kind=ripple declaration.

    The normalized values are encoded in CSS classes and (when dynamic) in the
    Three.js scene key. Keeping the seed in the outline makes repeated builds
    byte-for-byte deterministic.
    """
    if not isinstance(surface, dict) or surface.get('kind') != 'ripple':
        return None

    def choice(key, allowed, default):
        value = str(surface.get(key, default))
        if value not in allowed:
            sys.stderr.write('[warn] ripple.%s "%s" invalid on slide %d -> %s\n' %
                             (key, value, slide_number, default))
            return default
        return value

    seed = surface.get('seed', slide_number)
    try:
        seed = int(seed)
    except (TypeError, ValueError):
        sys.stderr.write('[warn] ripple.seed "%s" invalid on slide %d -> %d\n' %
                         (seed, slide_number, slide_number))
        seed = slide_number
    return {
        'pattern': choice('pattern', RIPPLE_PATTERNS, 'rings'),
        'zone': choice('zone', RIPPLE_ZONES, 'bottom'),
        'intensity': choice('intensity', RIPPLE_INTENSITIES, 'subtle'),
        'motion': choice('motion', RIPPLE_MOTIONS, 'drift'),
        'seed': seed,
    }


def slide_has_image(slide):
    """Return True when a slide already carries image-based visual content."""
    for key in IMAGE_FIELDS:
        value = slide.get(key)
        if isinstance(value, str) and value.strip():
            return True

    def contains_img(value):
        if isinstance(value, str):
            return bool(re.search(r'<img\b', value, re.I))
        if isinstance(value, dict):
            return any(contains_img(v) for v in value.values())
        if isinstance(value, list):
            return any(contains_img(v) for v in value)
        return False

    return contains_img(slide)


def slide_image_source(slide):
    """Return the primary image source declared by a stock layout."""
    for key in ('hero', 'image'):
        value = slide.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), key
    return None, None


def _local_or_data_bytes(src, src_dir):
    if not src:
        return None, 'none'
    if src.startswith('data:'):
        try:
            header, payload = src.split(',', 1)
            if ';base64' in header:
                return base64.b64decode(payload), 'data'
            return unquote_to_bytes(payload), 'data'
        except (ValueError, binascii.Error):
            return None, 'invalid'
    if src.startswith(('http://', 'https://')):
        return None, 'external'
    path = os.path.normpath(os.path.join(src_dir, src))
    if not os.path.exists(path):
        return None, 'missing'
    with open(path, 'rb') as fh:
        return fh.read(512 * 1024), 'local'


def image_profile(src, src_dir):
    """Return (shape, status, width, height) using only standard-library parsing."""
    data, status = _local_or_data_bytes(src, src_dir)
    if not data:
        return 'unknown', status, None, None
    width = height = None
    if data.startswith(b'\x89PNG\r\n\x1a\n') and len(data) >= 24:
        width = int.from_bytes(data[16:20], 'big')
        height = int.from_bytes(data[20:24], 'big')
    elif data[:6] in (b'GIF87a', b'GIF89a') and len(data) >= 10:
        width = int.from_bytes(data[6:8], 'little')
        height = int.from_bytes(data[8:10], 'little')
    elif data.startswith(b'\xff\xd8'):
        i = 2
        sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
        while i + 8 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            i += 2
            if marker in (0xD8, 0xD9):
                continue
            if i + 2 > len(data):
                break
            length = int.from_bytes(data[i:i + 2], 'big')
            if marker in sof and i + 7 < len(data):
                height = int.from_bytes(data[i + 3:i + 5], 'big')
                width = int.from_bytes(data[i + 5:i + 7], 'big')
                break
            i += max(2, length)
    elif data.startswith(b'RIFF') and data[8:12] == b'WEBP' and data[12:16] == b'VP8X' and len(data) >= 30:
        width = 1 + int.from_bytes(data[24:27], 'little')
        height = 1 + int.from_bytes(data[27:30], 'little')
    elif b'<svg' in data[:4096].lower():
        head = data[:4096].decode('utf-8', errors='ignore')
        viewbox = re.search(r'viewBox=["\']\s*[\d.-]+\s+[\d.-]+\s+([\d.]+)\s+([\d.]+)', head, re.I)
        if viewbox:
            width, height = float(viewbox.group(1)), float(viewbox.group(2))
        else:
            width_match = re.search(r'\bwidth=["\']\s*([\d.]+)', head, re.I)
            height_match = re.search(r'\bheight=["\']\s*([\d.]+)', head, re.I)
            if width_match and height_match:
                width, height = float(width_match.group(1)), float(height_match.group(1))
    if not width or not height:
        return 'unknown', status, width, height
    ratio = float(width) / float(height)
    shape = 'landscape' if ratio >= 1.3 else ('portrait' if ratio <= .78 else 'square')
    return shape, status, width, height


def chart_profile(chart):
    """Return (semantic chart family, data density) from a pure-JSON option."""
    if not isinstance(chart, dict):
        return 'none', 'normal'
    option = chart.get('option') if isinstance(chart.get('option'), dict) else {}
    series = option.get('series') if isinstance(option.get('series'), list) else []
    types = {str(s.get('type', '')).lower() for s in series if isinstance(s, dict)}
    if 'pie' in types:
        family = 'proportion'
    elif 'radar' in types:
        family = 'radar'
    elif 'scatter' in types or 'effectscatter' in types:
        family = 'distribution'
    elif 'line' in types:
        family = 'trend'
    elif 'bar' in types:
        family = 'comparison'
    else:
        family = 'generic'
    points = 0
    for series_item in series:
        if isinstance(series_item, dict) and isinstance(series_item.get('data'), list):
            points += len(series_item['data'])
    density = 'dense' if len(series) >= 4 or points >= 28 else 'normal'
    return family, density


def auto_ripple_surface(slide, slide_number):
    """Create a deterministic, reading-safe ripple fallback.

    Dense layouts receive a subtle static texture localized away from the main
    reading zone. Sparse layouts may drift gently. Explicit surface settings
    always win.
    """
    layout = slide.get('layout', '')
    even = slide_number % 2 == 0
    return {
        'kind': 'ripple',
        'pattern': 'rings' if even else 'flow',
        'zone': 'bottom-right' if even else 'bottom',
        'intensity': 'subtle',
        'motion': 'static' if layout in AUTO_RIPPLE_DENSE_LAYOUTS else 'drift',
        'seed': 1000 + slide_number * 97,
    }

def render_scalar(text, data):
    def repl(m):
        val = data
        for p in m.group(1).split('.'):
            if isinstance(val, dict) and p in val:
                val = val[p]
            else:
                return ''
        return '' if val is None else str(val)
    return SCALAR_RE.sub(repl, text)


def render(template, data):
    def block_repl(m):
        key = m.group(1)
        inner = m.group(2)
        items = data.get(key, [])
        if isinstance(items, list):
            parts = []
            for i, it in enumerate(items):
                ctx = dict(data)
                ctx['item'] = it if isinstance(it, dict) else {'value': it}
                ctx['i'] = i
                ctx['n'] = i + 1
                parts.append(render_scalar(inner, ctx))
            return ''.join(parts)
        if items:  # truthy scalar (e.g. an image data URI or a caption string)
            return render_scalar(inner, dict(data))
        return ''
    text = BLOCK_RE.sub(block_repl, template)
    return render_scalar(text, data)


def choose_cols(n):
    if n <= 2:
        return 'g2'
    if n == 3:
        return 'g3'
    if n == 4:
        return 'g4'
    return 'g3'


def data_table_markup(slide):
    """Return escaped table header/body markup from structured JSON cells."""
    columns = slide.get('columns') if isinstance(slide.get('columns'), list) else []
    rows = slide.get('rows') if isinstance(slide.get('rows'), list) else []
    highlights = {int(value) for value in slide.get('highlight_rows', [])
                  if isinstance(value, int) or str(value).isdigit()}
    head = ''.join('<th scope="col">%s</th>' % html.escape(_plain_text(cell)) for cell in columns)
    body = []
    for row_index, row in enumerate(rows):
        cells = row.get('cells', []) if isinstance(row, dict) else row
        if not isinstance(cells, list):
            cells = [cells]
        row_class = ' class="is-highlight"' if row_index in highlights or (
            isinstance(row, dict) and row.get('highlight')) else ''
        rendered_cells = []
        for cell_index, cell in enumerate(cells):
            tag = 'th scope="row"' if cell_index == 0 else 'td'
            rendered_cells.append('<%s>%s</%s>' % (
                tag, html.escape(_plain_text(cell)), tag.split()[0]))
        body.append('<tr%s>%s</tr>' % (row_class, ''.join(rendered_cells)))
    return head, ''.join(body)


# ---------- layout intelligence ----------
_TAG_RE = re.compile(r'<[^>]+>')
_SPACE_RE = re.compile(r'\s+')
_CJK_RE = re.compile(r'[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]')
_LATIN_RE = re.compile(r'[A-Za-z]')
_TEXT_FIELDS = (
    'eyebrow', 'title', 'subtitle', 'left', 'right', 'quote', 'by', 'desc',
    'note', 'takeaway', 'caption', 'items', 'left_items', 'right_items',
    'columns', 'rows', 'center',
)
_DENSITY_LIMITS = {
    'cover': (85, 150), 'toc': (210, 340), 'section-divider': (100, 170),
    'bullets': (270, 430), 'two-column': (340, 540),
    'grid-cards': (300, 470), 'big-quote': (110, 185),
    'stat-highlight': (145, 230), 'kpi-grid': (175, 290),
    'timeline': (310, 480), 'comparison': (300, 470),
    'image-frame': (125, 210), 'object-float': (145, 240),
    'closing': (105, 185), 'chart': (210, 340),
    'data-table': (250, 390), 'process-flow': (260, 420),
    'concept-map': (230, 370),
}
_LAYOUT_VARIANTS = {
    'toc': {'index-quadrant', 'index-matrix'},
    'bullets': {'list-spread', 'list-vertical', 'list-compact'},
    'two-column': {'split-left', 'split-right', 'split-balanced'},
    'grid-cards': {'feature-first', 'mosaic', 'matrix'},
    'kpi-grid': {'feature-first', 'kpi-strip', 'matrix'},
    'timeline': {'line-spacious', 'line-compact'},
    'comparison': {'compare-left', 'compare-right', 'compare-balanced'},
    'stat-highlight': {'number-left', 'number-right'},
    'image-frame': {'visual-left', 'visual-right'},
    'chart': {'visual-left', 'visual-right'},
    'data-table': {'table-balanced', 'table-compact'},
    'process-flow': {'flow-horizontal', 'flow-compact'},
    'concept-map': {'map-radial', 'map-bilateral'},
}

_RHYTHM_FAMILIES = {
    'cover': 'opening', 'toc': 'navigation', 'section-divider': 'break',
    'big-quote': 'break', 'closing': 'closing',
    'image-frame': 'visual', 'object-float': 'visual', 'chart': 'evidence',
    'stat-highlight': 'emphasis', 'kpi-grid': 'evidence',
    'grid-cards': 'structure', 'timeline': 'structure',
    'data-table': 'evidence', 'process-flow': 'explain', 'concept-map': 'synthesis',
    'bullets': 'explain', 'two-column': 'explain', 'comparison': 'explain',
}

_STORY_ROLES = {
    'hook', 'orient', 'question', 'context', 'conflict', 'explain', 'example',
    'evidence', 'contrast', 'reveal', 'synthesis', 'transition', 'resolution', 'pause',
}
_NARRATIVE_ROLE_BY_LAYOUT = {
    'cover': 'hook', 'toc': 'orient', 'section-divider': 'transition',
    'big-quote': 'pause', 'closing': 'resolution', 'chart': 'evidence',
    'data-table': 'evidence', 'stat-highlight': 'reveal', 'kpi-grid': 'evidence',
    'comparison': 'contrast', 'process-flow': 'explain', 'concept-map': 'synthesis',
    'image-frame': 'example', 'object-float': 'example',
}
_EMOTION_BY_ROLE = {
    'hook': 'curiosity', 'orient': 'clarity', 'question': 'curiosity',
    'context': 'clarity', 'conflict': 'tension', 'explain': 'clarity',
    'example': 'recognition', 'evidence': 'confidence', 'contrast': 'tension',
    'reveal': 'surprise', 'synthesis': 'confidence', 'transition': 'reset',
    'resolution': 'closure', 'pause': 'reflection',
}
_MEANINGFUL_VISUALS = {
    'image', 'chart', 'data-table', 'process-flow', 'concept-map',
    'comparison', 'kpi', 'stat', 'timeline', 'structured-grid',
}

_GENERIC_TITLES = {
    '介绍', '基本介绍', '相关介绍', '概述', '基本概念', '研究背景', '现状分析',
    '问题分析', '案例分析', '数据分析', '核心内容', '主要内容', '解决方案',
    '发展趋势', '未来展望', '总结', '结论',
    'introduction', 'overview', 'background', 'analysis', 'case study',
    'key points', 'solution', 'future outlook', 'summary', 'conclusion',
}
_NON_CLAIM_LAYOUTS = {'cover', 'toc', 'section-divider', 'big-quote', 'closing'}
_SCREEN_BLOCK_LIMITS = {
    'subtitle': 90, 'desc': 100, 'note': 120, 'takeaway': 90,
    'left': 220, 'right': 220, 'caption': 120,
}


def _plain_text(value):
    if value is None:
        return ''
    if isinstance(value, dict):
        return ' '.join(_plain_text(v) for v in value.values())
    if isinstance(value, list):
        return ' '.join(_plain_text(v) for v in value)
    text = html.unescape(_TAG_RE.sub(' ', str(value)))
    return _SPACE_RE.sub(' ', text).strip()


def _text_len(value):
    return len(_plain_text(value))


def title_profile(value):
    """Return visual-length and script classes for display typography."""
    text = _plain_text(value)
    cjk = len(_CJK_RE.findall(text))
    latin = len(_LATIN_RE.findall(text))
    digits = sum(ch.isdigit() for ch in text)
    visual_units = cjk + (latin + digits) * .56 + max(0, len(text) - cjk - latin - digits) * .35
    if visual_units <= 9:
        size = 'short'
    elif visual_units <= 17:
        size = 'medium'
    elif visual_units <= 27:
        size = 'long'
    else:
        size = 'xlong'
    if cjk and latin:
        script = 'mixed'
    elif cjk:
        script = 'cjk'
    else:
        script = 'latin'
    return size, script, visual_units


def _normalized_title(value):
    text = _plain_text(value).strip().lower()
    return re.sub(r'[\s\-—_:：·•,.，。!?！？()（）]+', ' ', text).strip()


def speaker_notes_html(value):
    """Render notes as inert escaped HTML; never treat notes as slide markup."""
    if isinstance(value, list):
        parts = [_plain_text(item) for item in value if _plain_text(item)]
    else:
        text = _plain_text(value)
        parts = [text] if text else []
    return ''.join('<p>%s</p>' % html.escape(part) for part in parts)


def content_profile(slide):
    """Inspect display copy while preserving user wording and source fidelity."""
    layout = slide.get('layout', '')
    title = _plain_text(slide.get('title'))
    normalized = _normalized_title(title)
    title_quality = 'not-applicable' if layout in _NON_CLAIM_LAYOUTS else (
        'missing' if not title else ('generic' if normalized in _GENERIC_TITLES else 'claim')
    )
    long_blocks = []
    for field, limit in _SCREEN_BLOCK_LIMITS.items():
        length = _text_len(slide.get(field))
        if length > limit:
            long_blocks.append({'field': field, 'length': length, 'limit': limit})
    for field in ('items', 'left_items', 'right_items'):
        values = slide.get(field)
        if not isinstance(values, list):
            continue
        for item_index, item in enumerate(values):
            if not isinstance(item, dict):
                continue
            for key in ('desc', 'text'):
                length = _text_len(item.get(key))
                limit = 82 if key == 'desc' else 72
                if length > limit:
                    long_blocks.append({
                        'field': '%s[%d].%s' % (field, item_index, key),
                        'length': length, 'limit': limit,
                    })
    notes = slide.get('speaker_notes', slide.get('notes'))
    notes_length = _text_len(notes)
    main_point = _plain_text(slide.get('main_point'))
    main_point_source = 'explicit' if main_point else (
        'title' if title_quality == 'claim' else 'missing'
    )
    return {
        'titleQuality': title_quality,
        'mainPointSource': main_point_source,
        'mainPoint': main_point or (title if title_quality == 'claim' else ''),
        'screenCharacters': sum(_text_len(slide.get(key)) for key in _TEXT_FIELDS),
        'speakerNotesCharacters': notes_length,
        'longBlocks': long_blocks,
    }


def narrative_profile(slide, slide_index, slide_count):
    """Resolve narrative intent while keeping authored prose under agent control."""
    layout = slide.get('layout', '')
    requested_role = _normalized_title(slide.get('story_role')).replace(' ', '-')
    inferred_role = _NARRATIVE_ROLE_BY_LAYOUT.get(layout, 'explain')
    if slide_index == 0 and layout != 'cover':
        inferred_role = 'hook'
    elif slide_index == slide_count - 1 and layout != 'closing':
        inferred_role = 'resolution'
    role = requested_role if requested_role in _STORY_ROLES else inferred_role
    role_source = 'explicit' if requested_role in _STORY_ROLES else 'inferred'
    emotion_raw = _normalized_title(slide.get('emotion')).replace(' ', '-') or _EMOTION_BY_ROLE.get(role, 'clarity')
    emotion = re.sub(r'[^a-z0-9\-]+', '-', emotion_raw).strip('-') or 'clarity'
    copy = content_profile(slide)
    return {
        'storyRole': role,
        'storyRoleSource': role_source,
        'invalidStoryRole': requested_role if requested_role and requested_role not in _STORY_ROLES else '',
        'audienceQuestion': _plain_text(slide.get('audience_question')),
        'speakerIntent': _plain_text(slide.get('speaker_intent')),
        'transition': _plain_text(slide.get('transition')),
        'emotion': emotion,
        'mainPoint': copy['mainPoint'],
        'explicitCueCount': sum(bool(_plain_text(slide.get(key))) for key in (
            'story_role', 'audience_question', 'speaker_intent', 'transition', 'emotion', 'main_point')),
    }


def audit_narrative(slides):
    profiles = [narrative_profile(slide, idx, len(slides)) for idx, slide in enumerate(slides)]
    warnings = []
    for idx, profile in enumerate(profiles):
        if profile['invalidStoryRole']:
            warnings.append({
                'code': 'invalid-story-role', 'slides': [idx + 1, idx + 1],
                'message': 'slide %d story_role "%s" is unsupported; inferred "%s"'
                           % (idx + 1, profile['invalidStoryRole'], profile['storyRole']),
            })
    start = 0
    while start < len(profiles):
        end = start + 1
        while end < len(profiles) and profiles[end]['storyRole'] == profiles[start]['storyRole']:
            end += 1
        if end - start >= 4:
            warnings.append({
                'code': 'flat-story-role', 'slides': [start + 1, end],
                'message': 'slides %d-%d repeat story role "%s"; add evidence, example, contrast, or a reset'
                           % (start + 1, end, profiles[start]['storyRole']),
            })
        start = end
    n = len(profiles)
    roles = {profile['storyRole'] for profile in profiles}
    if n >= 8 and not roles.intersection({'evidence', 'example', 'contrast', 'reveal'}):
        warnings.append({
            'code': 'flat-story-arc', 'slides': [1, n],
            'message': 'long deck lacks an evidence, example, contrast, or reveal beat',
        })
    return {'slides': profiles, 'warnings': warnings}


def narrative_cues_html(profile, lang='en'):
    if str(lang).lower().startswith('zh'):
        labels = (
            ('核心结论', profile.get('mainPoint')),
            ('转场提示', profile.get('transition')),
        )
    else:
        labels = (
            ('Main point', profile.get('mainPoint')),
            ('Transition', profile.get('transition')),
        )
    return ''.join(
        '<p><strong>%s</strong>%s</p>' % (html.escape(label), html.escape(value))
        for label, value in labels if value
    )


def _actual_visual_type(slide):
    layout = slide.get('layout', '')
    if isinstance(slide.get('chart'), dict):
        return 'chart'
    if slide_has_image(slide):
        return 'image'
    return {
        'data-table': 'data-table', 'process-flow': 'process-flow',
        'concept-map': 'concept-map', 'comparison': 'comparison',
        'kpi-grid': 'kpi', 'stat-highlight': 'stat', 'timeline': 'timeline',
        'grid-cards': 'structured-grid',
    }.get(layout, 'decorative' if isinstance(slide.get('three'), dict) or slide.get('surface') else 'text')


def visual_plan_profile(slide):
    plan = slide.get('visual_plan') if isinstance(slide.get('visual_plan'), dict) else {}
    planned = str(plan.get('type', 'auto')).strip().lower().replace('_', '-') or 'auto'
    actual = _actual_visual_type(slide)
    priority = str(plan.get('priority', 'optional')).strip().lower() or 'optional'
    matches = planned in ('auto', actual)
    if planned == 'table':
        matches = actual == 'data-table'
    elif planned in ('diagram', 'relationship'):
        matches = actual in ('process-flow', 'concept-map')
    elif planned == 'data-visualization':
        matches = actual in ('chart', 'data-table', 'kpi', 'stat')
    return {
        'plannedType': planned,
        'actualType': actual,
        'purpose': _plain_text(plan.get('purpose')),
        'priority': priority,
        'source': _plain_text(plan.get('source')),
        'meaningful': actual in _MEANINGFUL_VISUALS,
        'matchesPlan': matches,
    }


def audit_visual_coverage(slides):
    profiles = []
    warnings = []
    eligible = []
    structural = {'cover', 'toc', 'section-divider', 'big-quote', 'closing'}
    for idx, slide in enumerate(slides):
        profile = dict({'slide': idx + 1, 'layout': slide.get('layout', '')}, **visual_plan_profile(slide))
        profiles.append(profile)
        if slide.get('layout') not in structural:
            eligible.append(profile)
        if profile['priority'] == 'required' and not profile['matchesPlan']:
            warnings.append({
                'code': 'required-visual-missing', 'slides': [idx + 1, idx + 1],
                'message': 'slide %d requires visual "%s" but renders "%s"'
                           % (idx + 1, profile['plannedType'], profile['actualType']),
            })
        if profile['actualType'] in ('chart', 'data-table') and not (
                profile['source'] or _plain_text(slide.get('caption')) or _plain_text(slide.get('source'))):
            warnings.append({
                'code': 'visual-source-missing', 'slides': [idx + 1, idx + 1],
                'message': 'slide %d %s has no source/caption; label scope and provenance'
                           % (idx + 1, profile['actualType']),
            })

    meaningful_count = sum(profile['meaningful'] for profile in eligible)
    coverage = meaningful_count / len(eligible) if eligible else 0
    if len(eligible) >= 6 and coverage < .4:
        warnings.append({
            'code': 'low-visual-coverage', 'slides': [1, len(slides)],
            'message': 'meaningful visual coverage is %d%%; target roughly 40-65%% when content supports it'
                       % round(coverage * 100),
        })
    run = []
    for profile in profiles:
        if profile['layout'] not in structural and not profile['meaningful']:
            run.append(profile['slide'])
        else:
            if len(run) >= 3:
                warnings.append({
                    'code': 'text-only-run', 'slides': [run[0], run[-1]],
                    'message': 'slides %d-%d are consecutive text-only content pages; consider a diagram, table, image, or evidence view'
                               % (run[0], run[-1]),
                })
            run = []
    if len(run) >= 3:
        warnings.append({
            'code': 'text-only-run', 'slides': [run[0], run[-1]],
            'message': 'slides %d-%d are consecutive text-only content pages; consider a diagram, table, image, or evidence view'
                       % (run[0], run[-1]),
        })
    return {
        'slides': profiles,
        'eligibleSlides': len(eligible),
        'meaningfulSlides': meaningful_count,
        'coverage': round(coverage, 3),
        'warnings': warnings,
    }


def slide_density(slide):
    """Return (density_class, score) without rewriting user-authored copy.

    The deterministic builder can change composition safely, but semantic
    shortening/splitting belongs to the planning agent. Severe density emits an
    actionable warning instead of silently deleting or shrinking content.
    """
    layout = slide.get('layout', '')
    score = sum(_text_len(slide.get(key)) for key in _TEXT_FIELDS)
    item_count = sum(len(slide.get(key, [])) for key in ('items', 'left_items', 'right_items', 'rows')
                     if isinstance(slide.get(key), list))
    score += max(0, item_count - 4) * 24
    dense_at, overfull_at = _DENSITY_LIMITS.get(layout, (240, 390))
    if score > overfull_at:
        return 'overfull', score
    if score > dense_at:
        return 'dense', score
    if score < dense_at * .42:
        return 'sparse', score
    return 'standard', score


def slide_rhythm_profile(slide):
    """Return a semantic family and visual weight for deck-level pacing."""
    layout = slide.get('layout', '')
    family = _RHYTHM_FAMILIES.get(layout, 'content')
    density, score = slide_density(slide)
    if family in ('opening', 'break', 'emphasis', 'closing'):
        weight = 'light'
    elif density in ('dense', 'overfull'):
        weight = 'heavy'
    elif layout in ('grid-cards', 'kpi-grid', 'timeline', 'comparison'):
        items = sum(len(slide.get(key, [])) for key in ('items', 'left_items', 'right_items')
                    if isinstance(slide.get(key), list))
        weight = 'heavy' if items >= 5 else 'medium'
    else:
        weight = 'medium'
    return family, weight, density, score


def audit_deck_rhythm(slides):
    """Analyze cross-slide pacing without rewriting authored content."""
    profiles = []
    warnings = []
    for idx, slide in enumerate(slides):
        family, weight, density, score = slide_rhythm_profile(slide)
        profiles.append({
            'slide': idx + 1,
            'layout': slide.get('layout', ''),
            'family': family,
            'weight': weight,
            'density': density,
            'score': score,
        })

    def warn_runs(field, minimum, label):
        start = 0
        while start < len(profiles):
            end = start + 1
            while end < len(profiles) and profiles[end][field] == profiles[start][field]:
                end += 1
            if end - start >= minimum:
                warnings.append({
                    'code': 'repeated-' + field,
                    'slides': [start + 1, end],
                    'message': 'slides %d-%d repeat %s "%s"; vary the page rhythm'
                               % (start + 1, end, label, profiles[start][field]),
                })
            start = end

    warn_runs('layout', 3, 'layout')
    warn_runs('family', 4, 'content family')
    warn_runs('weight', 4, 'visual weight')
    start = 0
    while start < len(profiles):
        end = start + 1
        while end < len(profiles) and profiles[end]['weight'] == profiles[start]['weight']:
            end += 1
        if profiles[start]['weight'] == 'heavy' and end - start >= 3:
            warnings.append({
                'code': 'heavy-run', 'slides': [start + 1, end],
                'message': 'slides %d-%d are all heavy; insert a purposeful breathing beat or split content'
                           % (start + 1, end),
            })
        start = end

    n = len(profiles)
    if n >= 6 and profiles and profiles[0]['layout'] != 'cover':
        warnings.append({'code': 'missing-cover', 'slides': [1, 1],
                         'message': 'deck has no cover in the opening position'})
    if n >= 6 and profiles and profiles[-1]['layout'] != 'closing':
        warnings.append({'code': 'missing-closing', 'slides': [n, n],
                         'message': 'deck has no deliberate closing page'})
    if n >= 8 and not any(p['family'] in ('visual', 'evidence', 'emphasis') for p in profiles):
        warnings.append({'code': 'no-visual-evidence', 'slides': [1, n],
                         'message': 'long deck has no visual, evidence, or emphasis page'})
    if n >= 10 and not any(p['family'] == 'break' for p in profiles[2:-1]):
        warnings.append({'code': 'no-breathing-page', 'slides': [2, n - 1],
                         'message': 'long deck has no section or breathing page in the middle'})
    return {'slides': profiles, 'warnings': warnings}


def resolve_variant(slide, slide_index, media_shape='unknown', chart_family='none'):
    """Choose a deterministic composition variant from content shape."""
    layout = slide.get('layout', '')
    allowed = _LAYOUT_VARIANTS.get(layout)
    requested = str(slide.get('variant', 'auto')).strip().lower()
    if requested and requested != 'auto':
        if not allowed or requested in allowed:
            return re.sub(r'[^a-z0-9-]+', '-', requested).strip('-') or 'default'
        sys.stderr.write('[warn] slide %d variant "%s" is invalid for %s; using auto\n'
                         % (slide_index + 1, requested, layout))

    items = slide.get('items') if isinstance(slide.get('items'), list) else []
    n = len(items)
    if layout == 'toc':
        return 'index-quadrant' if n <= 4 else 'index-matrix'
    if layout == 'bullets':
        return 'list-spread' if n <= 3 else ('list-compact' if n >= 6 else 'list-vertical')
    if layout == 'two-column':
        left, right = _text_len(slide.get('left')), _text_len(slide.get('right'))
        if right > max(24, left * 1.25):
            return 'split-right'
        if left > max(24, right * 1.45):
            return 'split-left'
        return 'split-balanced'
    if layout == 'grid-cards':
        return 'feature-first' if n == 3 else ('mosaic' if n == 4 else 'matrix')
    if layout == 'kpi-grid':
        return 'feature-first' if n == 3 else ('kpi-strip' if n == 4 else 'matrix')
    if layout == 'timeline':
        return 'line-spacious' if n <= 4 else 'line-compact'
    if layout == 'data-table':
        rows = slide.get('rows') if isinstance(slide.get('rows'), list) else []
        return 'table-compact' if len(rows) >= 6 else 'table-balanced'
    if layout == 'process-flow':
        return 'flow-compact' if n >= 6 else 'flow-horizontal'
    if layout == 'concept-map':
        return 'map-bilateral' if n <= 4 else 'map-radial'
    if layout == 'comparison':
        left = _text_len(slide.get('left_items'))
        right = _text_len(slide.get('right_items'))
        if left > right * 1.35:
            return 'compare-left'
        if right > left * 1.35:
            return 'compare-right'
        return 'compare-balanced'
    if layout == 'stat-highlight':
        return 'number-left' if slide_index % 2 == 0 else 'number-right'
    if layout == 'image-frame' and media_shape == 'portrait':
        return 'visual-right'
    if layout == 'chart' and chart_family in ('proportion', 'radar'):
        return 'visual-right'
    if layout in ('image-frame', 'chart'):
        return 'visual-left' if slide_index % 2 == 0 else 'visual-right'
    return 'default'


# ---------- build ----------
def build(outline_path, out_path, assets_dir, templates_dir, return_report=False):
    with open(outline_path, encoding='utf-8') as f:
        outline = json.load(f)
    schema_version = outline.get('schema_version') if isinstance(outline, dict) else None
    if schema_version in (None, '1.0'):
        sys.stderr.write('[schema] legacy outline detected; run migrate_outline.py to persist stable IDs\n')
        outline, _migration_changes = migrate_outline(
            outline, os.path.splitext(os.path.basename(outline_path))[0]
        )
    elif schema_version == '2.0':
        schema_errors = validate_outline(outline)
        if schema_errors:
            raise ValueError('invalid v2 outline:\n- ' + '\n- '.join(schema_errors))
    else:
        raise ValueError('unsupported schema_version: %s' % schema_version)
    src_dir = os.path.dirname(os.path.abspath(outline_path))

    with open(os.path.join(assets_dir, 'engine.css'), encoding='utf-8') as f:
        css = f.read()
    with open(os.path.join(assets_dir, 'engine.js'), encoding='utf-8') as f:
        js = f.read()
    with open(os.path.join(templates_dir, 'deck.html'), encoding='utf-8') as f:
        deck = f.read()

    composition = str(outline.get('composition', 'constructivist')).strip().lower()
    if composition not in ('constructivist', 'classic'):
        sys.stderr.write('[warn] composition "%s" is invalid; using constructivist\n' % composition)
        composition = 'constructivist'
    typography = str(outline.get('typography', 'editorial')).strip().lower()
    if typography not in ('editorial', 'classic'):
        sys.stderr.write('[warn] typography "%s" is invalid; using editorial\n' % typography)
        typography = 'editorial'
    layout_intelligence = outline.get('layout_intelligence', True) is not False
    visual_intelligence = outline.get('visual_intelligence', True) is not False
    quality_intelligence = outline.get('quality_intelligence', True) is not False
    content_intelligence = outline.get('content_intelligence', True) is not False
    narrative_director = outline.get('narrative_director', True) is not False
    visual_coverage_planner = outline.get('visual_coverage_planner', True) is not False
    rhythm_report = (audit_deck_rhythm(outline.get('slides', []))
                     if quality_intelligence else {'slides': [], 'warnings': []})
    narrative_report = (audit_narrative(outline.get('slides', []))
                        if narrative_director else {'slides': [], 'warnings': []})
    coverage_report = (audit_visual_coverage(outline.get('slides', []))
                       if visual_coverage_planner else {
                           'slides': [], 'eligibleSlides': 0, 'meaningfulSlides': 0,
                           'coverage': 0, 'warnings': [],
                       })
    rhythm_by_slide = {item['slide']: item for item in rhythm_report['slides']}
    narrative_by_slide = {idx + 1: item for idx, item in enumerate(narrative_report['slides'])}
    coverage_by_slide = {item['slide']: item for item in coverage_report['slides']}
    for issue in rhythm_report['warnings']:
        sys.stderr.write('[rhythm] %s\n' % issue['message'])
    for issue in narrative_report['warnings']:
        sys.stderr.write('[narrative] %s\n' % issue['message'])
    for issue in coverage_report['warnings']:
        sys.stderr.write('[coverage] %s\n' % issue['message'])

    sp_dir = os.path.join(templates_dir, 'single-page')
    slides_out = []
    charts = []
    chart_counter = 0
    three_scenes = []
    content_profiles = []
    slide_identities = []
    auto_ripple_enabled = outline.get('auto_ripple', True) is not False
    for idx, slide in enumerate(outline.get('slides', [])):
        layout = slide.get('layout')
        slide_id = slide.get('slide_id')
        snippet_path = os.path.join(sp_dir, layout + '.html')
        if not os.path.exists(snippet_path):
            sys.stderr.write('[warn] layout "%s" not found -> skipping slide %d\n' % (layout, idx + 1))
            continue
        with open(snippet_path, encoding='utf-8') as f:
            tmpl = f.read()
        data = dict(slide)
        image_src, image_field = slide_image_source(slide)
        media_shape, media_status, _media_width, _media_height = (
            image_profile(image_src, src_dir) if visual_intelligence and image_src
            else ('none', 'none', None, None)
        )
        chart_family, chart_data_density = (
            chart_profile(slide.get('chart')) if visual_intelligence
            else ('none', 'normal')
        )
        density, density_score = slide_density(slide) if layout_intelligence else ('standard', 0)
        rhythm = rhythm_by_slide.get(idx + 1, {
            'family': 'content', 'weight': 'medium', 'density': density, 'score': density_score,
        })
        copy_profile = content_profile(slide) if content_intelligence else {
            'titleQuality': 'unchecked', 'mainPointSource': 'unchecked',
            'mainPoint': '',
            'screenCharacters': 0, 'speakerNotesCharacters': 0, 'longBlocks': [],
        }
        narrative = narrative_by_slide.get(idx + 1, {
            'storyRole': 'unchecked', 'storyRoleSource': 'unchecked', 'invalidStoryRole': '',
            'audienceQuestion': '', 'speakerIntent': '', 'transition': '',
            'emotion': 'clarity', 'mainPoint': copy_profile['mainPoint'], 'explicitCueCount': 0,
        })
        coverage = coverage_by_slide.get(idx + 1, {
            'plannedType': 'unchecked', 'actualType': 'text', 'purpose': '',
            'priority': 'optional', 'source': '', 'meaningful': False, 'matchesPlan': True,
        })
        content_profiles.append(dict({'slide': idx + 1, 'slideId': slide_id, 'layout': layout}, **copy_profile))
        slide_identities.append({
            'slide': idx + 1, 'slideId': slide_id, 'layout': layout,
            'title': _plain_text(slide.get('title')),
        })
        variant = (resolve_variant(slide, idx, media_shape, chart_family)
                   if layout_intelligence else 'default')
        title_size, title_script, title_units = title_profile(slide.get('title'))
        title_long = title_size in ('long', 'xlong')
        if title_size == 'xlong':
            sys.stderr.write('[type] slide %d (%s) has an extra-long title (%.1f units); '
                             'rewrite to one claim when source fidelity allows\n'
                             % (idx + 1, layout, title_units))
        if density == 'overfull':
            sys.stderr.write('[layout] slide %d (%s) is overfull (score=%d); '
                             'shorten copy or split the slide\n' % (idx + 1, layout, density_score))
        if content_intelligence and copy_profile['titleQuality'] in ('missing', 'generic'):
            sys.stderr.write('[copy] slide %d (%s) has a %s title; rewrite it as one audience-facing claim\n'
                             % (idx + 1, layout, copy_profile['titleQuality']))
        if content_intelligence:
            for block in copy_profile['longBlocks']:
                sys.stderr.write('[copy] slide %d %s is long (%d>%d chars); move detail to speaker_notes or split it\n'
                                 % (idx + 1, block['field'], block['length'], block['limit']))
        if visual_intelligence and image_src:
            alt_key = 'hero_alt' if image_field == 'hero' else 'alt'
            if not str(slide.get(alt_key, '')).strip():
                sys.stderr.write('[visual] slide %d (%s) is missing %s text\n'
                                 % (idx + 1, layout, alt_key))
            if media_status == 'missing':
                sys.stderr.write('[visual] slide %d image not found: %s\n' % (idx + 1, image_src))
        if visual_intelligence and chart_family != 'none' and not (
                str(slide.get('takeaway', '')).strip() or str(slide.get('note', '')).strip()):
            sys.stderr.write('[visual] slide %d chart has no takeaway; add one factual sentence\n'
                             % (idx + 1))
        if layout in ('grid-cards', 'kpi-grid'):
            data['cols'] = choose_cols(len(data.get('items', [])))
        elif layout == 'toc':
            n_items = len(data.get('items', []))
            data['cols'] = 'g2' if n_items <= 4 else 'g3'
        elif layout == 'data-table':
            data['table_head'], data['table_rows'] = data_table_markup(slide)
            if len(data.get('columns', [])) > 5 or len(data.get('rows', [])) > 7:
                sys.stderr.write('[visual] slide %d data-table is large; split it or move detail to an appendix\n'
                                 % (idx + 1))
        # Collect chart declarations: a slide carrying a "chart" field gets a
        # unique container id; its ECharts option is emitted into the init script.
        if 'chart' in slide and isinstance(slide.get('chart'), dict):
            cid = 'echart-%d' % chart_counter
            chart_counter += 1
            data['chart_id'] = cid
            default_chart_height = ('min(55vh,500px)' if chart_data_density == 'dense'
                                    else ('min(48vh,420px)' if chart_family in ('proportion', 'radar')
                                          else 'min(52vh,460px)'))
            data['chart_height'] = slide['chart'].get('height', default_chart_height)
            charts.append({'id': cid, 'option': slide['chart'].get('option', {})})
        # Material layer. Explicit surface settings always win. Otherwise, a
        # slide with no Three.js, ECharts, or image receives a restrained ripple
        # fallback so information pages do not collapse into a flat background.
        surface = slide.get('surface')
        auto_ripple = False
        has_chart = isinstance(slide.get('chart'), dict)
        three_cfg = slide.get('three')
        has_three = isinstance(three_cfg, dict) and bool(three_cfg.get('scene'))
        has_image = slide_has_image(slide)
        if (surface is None and auto_ripple_enabled
                and slide.get('auto_ripple', True) is not False
                and not has_chart and not has_three and not has_image):
            surface = auto_ripple_surface(slide, idx + 1)
            auto_ripple = True
        ripple = normalize_ripple(surface, idx + 1)
        ripple_dynamic = bool(ripple and ripple['motion'] != 'static')

        # Collect 3D scene declarations: a slide carrying a "three" field gets its
        # preset name stamped onto <section data-three="...">; the shared canvas
        # swaps to it when the slide becomes visible.
        # Rule: particle storms (field / nebula) are COVER-ONLY. On any other
        # slide they are remapped to a calm preset; the cover is auto-given the
        # storm when it declares no 3D scene at all.
        three_scene = None
        if 'three' in slide and isinstance(slide.get('three'), dict):
            sc = slide['three'].get('scene')
            if sc:
                if ripple_dynamic:
                    sys.stderr.write('[warn] slide %d has both three and dynamic ripple; '
                                     'using three + static ripple fallback\n' % (idx + 1))
                    ripple_dynamic = False
                base = sc.split(':')[0]
                if base in REMOVED_THREE_SCENES:
                    sys.stderr.write('[three] slide %d scene "%s" is retired; rendering no 3D scene\n'
                                     % (idx + 1, base))
                    three_scene = None
                elif base in PARTICLE_STORM:
                    three_scene = COVER_STORM if layout == 'cover' else CALM_FALLBACK
                else:
                    three_scene = sc
        elif ripple_dynamic:
            three_scene = 'ripple:%s:%s:%s:%s' % (
                ripple['pattern'], ripple['zone'], ripple['intensity'], ripple['seed'])
        elif layout == 'cover' and not ripple:
            three_scene = COVER_STORM
        if three_scene:
            three_scenes.append(three_scene)
        rendered = render(tmpl, data)
        rendered = re.sub(
            r'(<section\b)',
            r'\1 data-idx="%d" data-slide-id="%s"' % (idx, slide_id),
            rendered,
            count=1,
        )
        intelligence_classes = [
            'variant-' + variant, 'density-' + density,
            'title-size-' + title_size, 'script-' + title_script,
            'rhythm-' + rhythm['family'], 'weight-' + rhythm['weight'],
            'copy-title-' + copy_profile['titleQuality'],
            'story-' + narrative['storyRole'], 'emotion-' + narrative['emotion'],
            'visual-type-' + coverage['actualType'],
        ]
        if media_shape != 'none':
            intelligence_classes.append('media-' + media_shape)
        if chart_family != 'none':
            intelligence_classes.extend(['chart-' + chart_family, 'chart-data-' + chart_data_density])
        if title_long:
            intelligence_classes.append('title-long')
        rendered = re.sub(
            r'(<section\b[^>]*class=")([^"]*)(")',
            lambda m: m.group(1) + m.group(2) + ' ' + ' '.join(intelligence_classes) + m.group(3),
            rendered, count=1)
        rendered = re.sub(
            r'(<section\b[^>]*>)',
            lambda m: m.group(1).rstrip('>') +
            ' data-variant="%s" data-density="%s" data-media="%s" data-chart-profile="%s" data-rhythm="%s" data-weight="%s" data-title-quality="%s" data-story-role="%s" data-emotion="%s" data-visual-type="%s">'
            % (variant, density, media_shape, chart_family, rhythm['family'], rhythm['weight'],
               copy_profile['titleQuality'], narrative['storyRole'], narrative['emotion'], coverage['actualType']),
            rendered, count=1)
        cues_markup = narrative_cues_html(narrative, outline.get('lang', 'zh-CN'))
        if cues_markup:
            rendered = re.sub(
                r'</section>',
                '<aside class="narrative-cues" hidden aria-label="Narrative cues">%s</aside></section>' % cues_markup,
                rendered, count=1)
        notes_markup = speaker_notes_html(slide.get('speaker_notes', slide.get('notes')))
        if notes_markup:
            rendered = re.sub(
                r'</section>',
                '<aside class="speaker-notes" hidden aria-label="Speaker notes">%s</aside></section>' % notes_markup,
                rendered, count=1)
        if ripple:
            ripple_classes = ' '.join([
                'ripple-material',
                'ripple-auto' if auto_ripple else 'ripple-explicit',
                'ripple-' + ripple['pattern'],
                'ripple-zone-' + ripple['zone'],
                'ripple-' + ripple['intensity'],
                'ripple-dynamic' if ripple_dynamic else 'ripple-static',
            ])
            rendered = re.sub(
                r'(<section\b[^>]*class=")([^"]*)(")',
                lambda m: m.group(1) + m.group(2) + ' ' + ripple_classes + m.group(3),
                rendered, count=1)
        if three_scene:
            rendered = re.sub(r'(<section\b[^>]*>)',
                              lambda m: m.group(1).rstrip('>') + ' data-three="%s">' % three_scene,
                              rendered, count=1)
        if ripple:
            rendered = re.sub(r'(<section\b[^>]*>)',
                              r'\1\n  <div class="ripple-surface" aria-hidden="true"></div>',
                              rendered, count=1)
        slides_out.append(rendered)

    slides_html = '\n\n  '.join(slides_out)

    theme_css, theme_colors = build_theme(outline)

    # Topic glyphs: the floating background characters are DECK-SPECIFIC, never
    # hardcoded. outline "glyphs": ["夢","玉","詩"] renders up to 3 spans in the
    # fixed backdrop slots; omit the field and the slots stay empty.
    glyphs = [str(g)[:1] for g in (outline.get('glyphs') or []) if str(g).strip()][:3]
    glyphs_html = ''.join('<span class="g%d">%s</span>' % (i + 1, g)
                          for i, g in enumerate(glyphs))

    build_report = {
        'version': 4,
        'schemaVersion': outline.get('schema_version'),
        'deckId': outline.get('deck_id'),
        'slides': slide_identities,
        'qualityIntelligence': quality_intelligence,
        'contentIntelligence': content_intelligence,
        'narrativeDirector': narrative_director,
        'visualCoveragePlanner': visual_coverage_planner,
        'rhythm': rhythm_report,
        'content': {'slides': content_profiles},
        'narrative': narrative_report,
        'visualCoverage': coverage_report,
    }
    report_js = 'window.__LG_BUILD_REPORT__=' + json.dumps(build_report, ensure_ascii=False) + ';\n'
    result = (deck
              .replace('/*__ENGINE_CSS__*/', css)
              .replace('/*__ENGINE_JS__*/', report_js + js)
              .replace('<!--__SLIDES__-->', slides_html)
              .replace('<!--__GLYPHS__-->', glyphs_html)
              .replace('{{lang}}', outline.get('lang', 'zh-CN'))
              .replace('{{title}}', outline.get('title', 'Liquid Glass Deck'))
              .replace('{{deck_id}}', outline.get('deck_id', 'liquid-glass-deck'))
              .replace('{{schema_version}}', outline.get('schema_version', '2.0'))
              .replace('{{composition}}', composition)
              .replace('{{typography}}', typography)
              .replace('{{theme}}', theme_css))
    # Auto-embed: any local relative image path (e.g. images/foo.png) is read and
    # inlined as a base64 data URI, keeping the output a self-contained single file
    # while the original file still lives on disk for the user.
    mime_map = {'png': 'image/png', 'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
                'webp': 'image/webp', 'gif': 'image/gif', 'svg': 'image/svg+xml'}

    def _embed(m):
        src = m.group(1)
        if src.startswith(('data:', 'http://', 'https://', '#')):
            return m.group(0)
        p = os.path.normpath(os.path.join(src_dir, src))
        if not os.path.exists(p):
            return m.group(0)
        ext = os.path.splitext(p)[1].lstrip('.').lower()
        mime = mime_map.get(ext, 'application/octet-stream')
        with open(p, 'rb') as fh:
            b64 = base64.b64encode(fh.read()).decode('ascii')
        return 'src="data:%s;base64,%s"' % (mime, b64)

    result = re.sub(r'src="([^"]+)"', _embed, result)
    # ECharts: inline the library + a theme-aware init script ONLY when charts
    # are declared. When none are used, the deck stays dependency-free and small.
    if charts:
        with open(os.path.join(assets_dir, 'echarts.min.js'), encoding='utf-8') as f:
            echarts_js = f.read()
        charts_json = json.dumps(charts, ensure_ascii=False)
        chart_scripts = (
            '<script>' + echarts_js + '</script>\n'
            '<script>(function(){var __LG_CHARTS_RAW__=' + charts_json + ';'
            + CHART_INIT_JS + '})();</script>'
        )
    else:
        chart_scripts = ''
    result = result.replace('/*__CHART_SCRIPTS__*/', chart_scripts)
    # Three.js: inline the library + the shared-canvas init script ONLY when a
    # slide declares a "three" field. Unused decks stay dependency-free.
    if three_scenes:
        with open(os.path.join(assets_dir, 'three.min.js'), encoding='utf-8') as f:
            three_js = f.read()
        used_json = json.dumps(sorted(set(three_scenes)), ensure_ascii=False)
        three_scripts = (
            '<script>' + three_js + '</script>\n'
            '<script>window.__LG_THREE_USED__=' + used_json + ';'
            'window.__LG_THEME_HEX__=' + json.dumps(theme_colors, ensure_ascii=False) + ';'
            + THREE_INIT_JS + '</script>'
        )
    else:
        three_scripts = ''
    result = result.replace('<!--__THREE_SCRIPTS__-->', three_scripts)
    # strip any unresolved placeholders for a clean output
    result = re.sub(r'\{\{[^}]*\}\}', '', result)
    return (result, build_report) if return_report else result


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_assets = os.path.normpath(os.path.join(here, '..', 'assets'))
    default_templates = os.path.normpath(os.path.join(here, '..', 'templates'))

    ap = argparse.ArgumentParser(description='Build a self-contained liquid-glass deck from an outline JSON.')
    ap.add_argument('outline', nargs='?', help='path to outline JSON')
    ap.add_argument('--outline', dest='outline_opt', help='path to outline JSON')
    ap.add_argument('--out', help='output HTML path (default: <outline-name>.html)')
    ap.add_argument('--report', help='optional build-report JSON path')
    ap.add_argument('--assets', default=default_assets, help='engine assets dir')
    ap.add_argument('--templates', default=default_templates, help='templates dir')
    args = ap.parse_args()

    outline_path = args.outline or args.outline_opt
    if not outline_path:
        ap.error('an outline JSON is required (positional or --outline)')
    if not os.path.exists(outline_path):
        ap.error('outline not found: %s' % outline_path)

    out_path = args.out or (os.path.splitext(os.path.basename(outline_path))[0] + '.html')
    out_path = os.path.abspath(out_path)

    try:
        html, report = build(
            outline_path, out_path, args.assets, args.templates, return_report=True
        )
    except (ValueError, json.JSONDecodeError) as exc:
        print('ERROR: %s' % exc, file=sys.stderr)
        raise SystemExit(2)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)
    if args.report:
        report_path = os.path.abspath(args.report)
        with open(report_path, 'w', encoding='utf-8', newline='\n') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
            f.write('\n')

    n_slides = len(re.findall(r'<section\b[^>]*class="[^"]*\bslide\b', html))
    print('OK  ->  %s  (%d slides, %d KB)' % (out_path, n_slides, len(html.encode('utf-8')) // 1024))


if __name__ == '__main__':
    main()
