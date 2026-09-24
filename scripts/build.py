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
    "lang": "zh-CN",
    "title": "Deck title",
    "theme": { "colors": ["#0A84FF","#5E5CE6","#30D158"], "accent": "#0A84FF" },  # optional: 3 blob/particle colors + 1 accent
    "slides": [
      { "layout": "cover", "eyebrow": "...", "title": "...", "subtitle": "..." },
      { "layout": "grid-cards", "items": [ {"num":"01","title":"..","desc":".."}, ... ] },
      ...
    ]
  }

Available layouts (templates/single-page/*.html):
  cover, toc, section-divider, bullets, two-column, grid-cards, big-quote,
  stat-highlight, kpi-grid, timeline, comparison, image-frame,
  object-float, closing, chart

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
  { "layout":"cover", "title":"..", "three": { "scene": "field" } }  # field | nebula | object

Snippet placeholders:
  {{field}}            scalar substitution
  {{#items}} ... {{/items}}   repeat block; inside use {{item.x}} and {{i}} (0-based)
  {{#hero}} ... {{/hero}}     optional block; renders once if the field is truthy
"""
import argparse
import base64
import json
import os
import re
import sys

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
# The active slide's scene (field / nebula / object) is swapped via IntersectionObserver,
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
  function objectScene(o){
    o=o||{}; var scene=new THREE.Scene();
    var cam=new THREE.PerspectiveCamera(55,1,0.1,2000); cam.position.set(o.x||2.6,o.y||0,o.camZ||7);
    var makers={
      icosahedron:function(r){ return new THREE.IcosahedronGeometry(r,1); },
      dodecahedron:function(r){ return new THREE.DodecahedronGeometry(r,0); },
      torusKnot:function(r){ return new THREE.TorusKnotGeometry(r*0.72,r*0.24,96,14); },
      torus:function(r){ return new THREE.TorusGeometry(r*0.9,r*0.32,18,44); },
      sphere:function(r){ return new THREE.SphereGeometry(r,32,24); }
    };
    var mk=makers[o.shape]||makers.icosahedron;
    var geo=mk(o.r||2.2);
    var mat=new THREE.MeshStandardMaterial({color:PALETTE[0],transparent:true,opacity:0.22,roughness:0.35,metalness:0.1});
    var mesh=new THREE.Mesh(geo,mat);
    var wire=new THREE.Mesh(geo,new THREE.MeshBasicMaterial({color:PALETTE[0],wireframe:true,transparent:true,opacity:0.22}));
    mesh.add(wire); scene.add(mesh);
    var dl=new THREE.DirectionalLight(0xffffff,1.1); dl.position.set(5,6,8); scene.add(dl);
    scene.add(new THREE.AmbientLight(0xffffff,0.6));
    return {scene:scene,camera:cam,update:function(t){ mesh.rotation.y=t*0.3; mesh.rotation.x=t*0.15;
      var s=1+Math.sin(t*0.8)*0.04; mesh.scale.set(s,s,s); }};
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
  // Glass bubbles: a few large translucent orbs floating slowly — calm and
  // airy; pairs with dreamy, philosophical or festive atmosphere pages.
  function orbsScene(o){
    o=o||{}; var n=o.count||9;
    var scene=new THREE.Scene();
    var cam=new THREE.PerspectiveCamera(55,1,0.1,2000); cam.position.z=o.camZ||16;
    var orbs=[];
    for(var i=0;i<n;i++){
      var r=rand(1.1,3.1);
      var m=new THREE.Mesh(new THREE.SphereGeometry(r,32,24),
        new THREE.MeshStandardMaterial({color:PALETTE[i%PALETTE.length],transparent:true,opacity:0.15,roughness:0.18,metalness:0.05}));
      m.position.set(rand(-11,11),rand(-6,6),rand(-6,4));
      m.userData={by:m.position.y,ph:rand(0,6.28),sp:rand(0.25,0.55)};
      scene.add(m); orbs.push(m);
    }
    var dl=new THREE.DirectionalLight(0xffffff,1.0); dl.position.set(5,6,8); scene.add(dl);
    scene.add(new THREE.AmbientLight(0xffffff,0.75));
    return {scene:scene,camera:cam,update:function(t){
      orbs.forEach(function(m){ m.position.y=m.userData.by+Math.sin(t*m.userData.sp+m.userData.ph)*1.3;
        m.rotation.y=t*0.1; });
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
              'object':function(arg){return objectScene({shape:arg});},
              'network':function(){return networkScene({count:30,spread:15});},
              'petals':function(){return petalsScene({});},
              'orbs':function(){return orbsScene({});},
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
CALM_FALLBACK = 'orbs'
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


# ---------- build ----------
def build(outline_path, out_path, assets_dir, templates_dir):
    with open(outline_path, encoding='utf-8') as f:
        outline = json.load(f)

    with open(os.path.join(assets_dir, 'engine.css'), encoding='utf-8') as f:
        css = f.read()
    with open(os.path.join(assets_dir, 'engine.js'), encoding='utf-8') as f:
        js = f.read()
    with open(os.path.join(templates_dir, 'deck.html'), encoding='utf-8') as f:
        deck = f.read()

    sp_dir = os.path.join(templates_dir, 'single-page')
    slides_out = []
    charts = []
    chart_counter = 0
    three_scenes = []
    auto_ripple_enabled = outline.get('auto_ripple', True) is not False
    for idx, slide in enumerate(outline.get('slides', [])):
        layout = slide.get('layout')
        snippet_path = os.path.join(sp_dir, layout + '.html')
        if not os.path.exists(snippet_path):
            sys.stderr.write('[warn] layout "%s" not found -> skipping slide %d\n' % (layout, idx + 1))
            continue
        with open(snippet_path, encoding='utf-8') as f:
            tmpl = f.read()
        data = dict(slide)
        if layout in ('grid-cards', 'kpi-grid'):
            data['cols'] = choose_cols(len(data.get('items', [])))
        elif layout == 'toc':
            n_items = len(data.get('items', []))
            data['cols'] = 'g2' if n_items <= 4 else 'g3'
        # Collect chart declarations: a slide carrying a "chart" field gets a
        # unique container id; its ECharts option is emitted into the init script.
        if 'chart' in slide and isinstance(slide.get('chart'), dict):
            cid = 'echart-%d' % chart_counter
            chart_counter += 1
            data['chart_id'] = cid
            data['chart_height'] = slide['chart'].get('height', 'min(50vh,440px)')
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
                if base in PARTICLE_STORM:
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
        rendered = re.sub(r'(<section\b)', r'\1 data-idx="%d"' % idx, rendered, count=1)
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

    result = (deck
              .replace('/*__ENGINE_CSS__*/', css)
              .replace('/*__ENGINE_JS__*/', js)
              .replace('<!--__SLIDES__-->', slides_html)
              .replace('<!--__GLYPHS__-->', glyphs_html)
              .replace('{{lang}}', outline.get('lang', 'zh-CN'))
              .replace('{{title}}', outline.get('title', 'Liquid Glass Deck'))
              .replace('{{theme}}', theme_css))
    # Auto-embed: any local relative image path (e.g. images/foo.png) is read and
    # inlined as a base64 data URI, keeping the output a self-contained single file
    # while the original file still lives on disk for the user.
    src_dir = os.path.dirname(os.path.abspath(outline_path))
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
    return result


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    default_assets = os.path.normpath(os.path.join(here, '..', 'assets'))
    default_templates = os.path.normpath(os.path.join(here, '..', 'templates'))

    ap = argparse.ArgumentParser(description='Build a self-contained liquid-glass deck from an outline JSON.')
    ap.add_argument('outline', nargs='?', help='path to outline JSON')
    ap.add_argument('--outline', dest='outline_opt', help='path to outline JSON')
    ap.add_argument('--out', help='output HTML path (default: <outline-name>.html)')
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

    html = build(outline_path, out_path, args.assets, args.templates)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    n_slides = len(re.findall(r'<section\b[^>]*class="[^"]*\bslide\b', html))
    print('OK  ->  %s  (%d slides, %d KB)' % (out_path, n_slides, len(html.encode('utf-8')) // 1024))


if __name__ == '__main__':
    main()
