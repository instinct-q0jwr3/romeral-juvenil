#!/usr/bin/env python3
"""Fetch RFAF pnfg data for C.D. Futbol Romeral (3a Andaluza Juvenil Malaga G1) and build a static site in docs/."""
from __future__ import annotations
import html,json,re,subprocess,sys,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'raw'; OUT=ROOT/'docs'; ESC=OUT/'escudos'
TEAM='C.D. FUTBOL ROMERAL'
TEAM_SHORT='ROMERAL'
NJ=30
U_CLAS='https://www.rfaf.es/pnfg/NPcd/NFG_VisClasificacion?cod_primaria=1000120&codgrupo=48465932&codcompeticion=48465931'
U_CAL='https://www.rfaf.es/pnfg/NPcd/NFG_VisCalendario_Vis?cod_primaria=1000120&codtemporada=22&codcompeticion=48465931&codgrupo=48465932&CodJornada=1'
U_CMP='https://www.rfaf.es/pnfg/NPcd/NFG_CmpJornada?cod_primaria=1000120&CodTemporada=22&CodGrupo=48465932&CodCompeticion=48465931&CodJornada={}'
D_DEFAULT=[2,5,9,4,1,0,8,6,3,7,1,3,5,7,9,0,2,4,6,8,0,2,4,6,8,1,3,5,7,9,7,5,2,0,9,6,3,8,4,1]

def fetch(name,url,minlen=5000,attempts=4):
    import time
    jar=RAW/'cookies.txt'
    for attempt in range(attempts):
        if attempt: time.sleep(8*attempt)
        subprocess.run(['curl','-sL','--max-time','40','-b',str(jar),'-c',str(jar),url,'-o',str(RAW/f'{name}.html')],check=False)
        p=RAW/f'{name}.html'
        t=p.read_text(encoding='latin-1',errors='replace') if p.exists() else ''
        if len(t)>minlen and 'No se ha aceptado el cookie' not in t:
            time.sleep(1.5)
            return t
    raise SystemExit(f'fetch failed for {name}')

def clean(s):
    s=re.sub(r'<[^>]+>','',s)
    s=html.unescape(s).replace('\xa0',' ')
    return re.sub(r'\s+',' ',s).strip()

def darray(h):
    m=re.search(r'g d=\[([0-9,]+)\]',h)
    if m:
        arr=[int(x) for x in m.group(1).split(',')]
        if len(arr)>=40: return arr
    return D_DEFAULT

def decode_score(region,d):
    """Return (gl, gv) as strings, or None if not played."""
    events=[]
    for m in re.finditer(r'ntype\("idh\d+",(\d+),(\d+),',region):
        n,i=int(m.group(1)),int(m.group(2))
        events.append((m.start(),str(d[i*10+n])))
    for m in re.finditer(r'#idh\d+:(?:before|after)\{content:"(\\[0-9a-fA-F]{4}|\d)"\}',region):
        v=m.group(1)
        events.append((m.start(),chr(int(v[1:],16)) if v.startswith('\\') else v))
    tmp=re.sub(r'<script>.*?</script>','',region,flags=re.S)
    tmp=re.sub(r'<style>.*?</style>','',tmp,flags=re.S)
    tmp=re.sub(r'<span style="display:none;">.*?</span>','',tmp,flags=re.S)
    for m in re.finditer(r'<i class=fa-solid>\s*(\d+)\s*</i>',tmp):
        events.append((m.start(),m.group(1)))
    events.sort()
    digs=[v for _,v in events]
    if len(digs)>=2: return digs[0],digs[1]
    return None

def parse_clasificacion(h):
    rows=re.findall(r'<tr[^>]*>(.*?)</tr>',h,re.S)
    table=[]
    for r in rows:
        cells=[clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)]
        if len(cells)>=12 and cells[1].isdigit():
            def n(i):
                try: return int(cells[i])
                except Exception: return 0
            mc=re.search(r'[Cc]odigo_[Ee]quipo=(\d+)',r) or re.search(r'codequipo=(\d+)',r)
            table.append({'pos':int(cells[1]),'equipo':cells[2],'code':mc.group(1) if mc else '',
                          'pts':cells[3],
                          'j':n(4)+n(8),'g':n(5)+n(9),'e':n(6)+n(10),'p':n(7)+n(11),
                          'gf':cells[12],'gc':cells[13] if len(cells)>13 else '',
                          'romeral':TEAM_SHORT in cells[2].upper()})
    return table

def parse_jornada(h,d):
    """Parse a NFG_CmpJornada page -> list of match dicts."""
    blocks=re.split(r'<tr><td>\s*<table width="100%">',h)
    matches=[]
    for b in blocks[1:]:
        ml=re.search(r'escudo_widgetL>\s*<img src="([^"]+)"',b)
        nl=re.search(r'font_widgetL.*?Codigo_Equipo=(\d+)">\s*(.*?)\s*</a>',b,re.S)
        mv=re.search(r'font_widgetV.*?Codigo_Equipo=(\d+)">\s*(.*?)\s*</a>',b,re.S)
        vv=re.search(r'escudo_widgetV>\s*<img src="([^"]+)"',b)
        if not (nl and mv): continue
        ms=re.search(r'<h4><strong>(.*?)</strong>\s*</h4>',b,re.S)
        score=decode_score(ms.group(1),d) if ms else None
        hors=[clean(x) for x in re.findall(r'class=horario[^>]*>(.*?)</span>',b,re.S)]
        hors=[x for x in hors if x]
        fecha=hors[0] if hors else ''
        hora=hors[1] if len(hors)>1 else ''
        matches.append({'local':clean(nl.group(2)),'local_code':nl.group(1),
                        'visitante':clean(mv.group(2)),'visitante_code':mv.group(1),
                        'escudo_l':ml.group(1) if ml else '','escudo_v':vv.group(1) if vv else '',
                        'gl':score[0] if score else '','gv':score[1] if score else '',
                        'fecha':fecha,'hora':hora,
                        'romeral':TEAM_SHORT in (nl.group(2)+mv.group(2)).upper()})
    return matches

def norm(s):
    return re.sub(r'\s+',' ',s.upper()).strip()

def parse_jornada_cal(h,j,d):
    """Fallback: jornada J section from the full VisCalendario page."""
    i=h.find(f'fecha_jornada_org_{j}>')
    if i<0: return []
    k=h.find(f'fecha_jornada_org_{j+1}>',i) if j<30 else len(h)
    if k<0: k=len(h)
    seg=h[i:k]
    ms=[]
    for r in re.findall(r'<tr>\s*<td width="47%" align=right>(.*?)</tr>',seg,re.S):
        cells=re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)
        if len(cells)<3: continue
        local,visit=clean(cells[0]),clean(cells[2])
        sc=decode_score(cells[1],d)
        ms.append({'local':local,'local_code':'','visitante':visit,'visitante_code':'',
                   'escudo_l':'','escudo_v':'',
                   'gl':sc[0] if sc else '','gv':sc[1] if sc else '',
                   'fecha':'','hora':'','romeral':TEAM_SHORT in (local+visit).upper()})
    return ms

def dl_crest(url,code):
    if not url or not code: return ''
    ext=url.rsplit('.',1)[-1].lower()
    if ext not in ('png','jpg','jpeg','gif','svg','webp'): ext='png'
    fn=f'escudos/{code}.{ext}'
    p=OUT/fn
    if p.exists() and p.stat().st_size>100: return fn
    r=subprocess.run(['curl','-sL','--max-time','30',url,'-o',str(p)],check=False)
    if r.returncode!=0 or not p.exists() or p.stat().st_size<100:
        p.unlink(missing_ok=True); return ''
    head=p.read_bytes()[:16]
    if head.strip().startswith(b'<'):  # html error page
        p.unlink(missing_ok=True); return ''
    return fn

def crest_img(fn,alt=''):
    if fn: return f'<img class="esc" src="{fn}" alt="" loading="lazy">'
    return '<img class="esc" src="escudos/placeholder.svg" alt="" loading="lazy">'

def main():
    RAW.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True); ESC.mkdir(exist_ok=True)
    now=datetime.datetime.now(ZoneInfo('Europe/Madrid'))
    stamp=now.strftime('%d/%m/%Y, %H:%M')+' CEST' if now.dst() else now.strftime('%d/%m/%Y, %H:%M')+' CET'

    h_clas=fetch('clasificacion',U_CLAS)
    tabla=parse_clasificacion(h_clas)

    h_cal=fetch('calendario_full',U_CAL)
    fechas_org={int(m.group(1)):m.group(2) for m in re.finditer(r'fecha_jornada_org_(\d+)>\((\d{2}-\d{2}-\d{4})\)',h_cal)}

    prev={}
    try: prev=json.loads((RAW/'data.json').read_text(encoding='utf-8'))
    except Exception: pass
    ultima_prev=int(prev.get('ultima_jugada') or 0)
    jornadas={}
    crests={}
    d_cal=darray(h_cal)
    name2code={}
    for j in range(1,NJ+1):
        ms=[]
        cached=RAW/f'cmp_j{j}.html'
        ct=cached.read_text(encoding='latin-1',errors='replace') if cached.exists() else ''
        in_window=abs(j-ultima_prev)<=1 or j==ultima_prev+2
        if len(ct)>20000 and not in_window:
            ms=parse_jornada(ct,darray(ct))
        if not ms:
            try:
                h=fetch(f'cmp_j{j}',U_CMP.format(j),minlen=20000,attempts=2)
                ms=parse_jornada(h,darray(h))
            except SystemExit:
                ms=[]
        if not ms:
            ms=parse_jornada_cal(h_cal,j,d_cal)
            for m in ms:
                m['local_code']=name2code.get(norm(m['local']),'')
                m['visitante_code']=name2code.get(norm(m['visitante']),'')
        else:
            for m in ms:
                name2code.setdefault(norm(m['local']),m['local_code'])
                name2code.setdefault(norm(m['visitante']),m['visitante_code'])
        jornadas[j]=ms
        for m in ms:
            for code,url in ((m['local_code'],m['escudo_l']),(m['visitante_code'],m['escudo_v'])):
                if code and url and code not in crests: crests[code]=url
    escudo_file={code:dl_crest(url,code) for code,url in crests.items()}

    jugadas=[j for j in jornadas if any(m['gl']!='' for m in jornadas[j])]
    ultima=max(jugadas) if jugadas else 0
    actual=ultima+1 if ultima<NJ else ultima
    jugados=sum(1 for j in jornadas for m in jornadas[j] if m['gl']!='')
    total=sum(len(v) for v in jornadas.values())

    data={'actualizado':stamp,'clasificacion':tabla,
          'jornadas':{str(j):jornadas[j] for j in jornadas},'fechas_org':fechas_org,
          'ultima_jugada':ultima,'jornada_actual':actual}
    (RAW/'data.json').write_text(json.dumps(data,ensure_ascii=False,indent=1),encoding='utf-8')

    render(tabla,jornadas,fechas_org,ultima,actual,escudo_file,stamp)
    print(f'Built site: {len(tabla)} equipos, {total} partidos ({jugados} jugados), jornada actual {actual}, escudos {sum(1 for v in escudo_file.values() if v)}/{len(crests)}, actualizado {stamp}')

NAV=[('index.html','Inicio'),('clasificacion.html','Clasificación'),('calendario.html','Calendario y resultados')]
def page(title,active,body):
    nav=''.join(f'<a href="{u}" class="{"on" if u==active else ""}">{t}</a>' for u,t in NAV)
    return f'''<!DOCTYPE html>
<html lang="es"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · C.D. Fútbol Romeral</title>
<link rel="stylesheet" href="style.css">
</head><body>
<header><div class="wrap nav"><span class="brand">C.D. Fútbol Romeral</span><nav>{nav}</nav></div></header>
<main class="wrap">
{body}
</main>
<footer><div class="wrap">Datos: Real Federación Andaluza de Fútbol (rfaf.es) · 3ª Andaluza Juvenil Málaga · Grupo 1</div></footer>
</body></html>'''

def fdate(dd):
    if not dd: return ''
    try:
        d=datetime.datetime.strptime(dd,'%d-%m-%Y')
        return d.strftime('%d/%m/%Y')
    except Exception: return dd

def match_row(m,escudo_file):
    rm=' rm' if m['romeral'] else ''
    el=crest_img(escudo_file.get(m['local_code'],''))
    ev=crest_img(escudo_file.get(m['visitante_code'],''))
    if m['gl']!='':
        mid=f'<span class="sc">{m["gl"]} - {m["gv"]}</span>'
    else:
        hora=m['hora'] if m['hora'] else 'hora por confirmar'
        mid=f'<span class="hr">{fdate(m["fecha"])} · {hora}</span>'
    sub=''
    if m['gl']!='' and m['fecha']:
        sub=f'<div class="sub">{fdate(m["fecha"])}</div>'
    return f'''<div class="mrow{rm}">
<div class="mt home">{el}<span>{html.escape(m["local"])}</span></div>
<div class="mm">{mid}{sub}</div>
<div class="mt away">{ev}<span>{html.escape(m["visitante"])}</span></div>
</div>'''

def render(tabla,jornadas,fechas_org,ultima,actual,escudo_file,stamp):
    # --- index
    rom=next((t for t in tabla if t['romeral']),None)
    rm_next=None; rm_last=None
    for j in sorted(jornadas):
        for m in jornadas[j]:
            if not m['romeral']: continue
            if m['gl']!='' : rm_last=(j,m)
            elif rm_next is None: rm_next=(j,m)
    stats=''
    if rom:
        stats=f'<div class="stats"><span><b>{rom["pos"]}º</b> clasificado</span><span><b>{rom["pts"]}</b> puntos</span><span><b>{rom["gf"]}-{rom["gc"]}</b> goles</span><span><b>{rom["j"]}</b> jugados</span></div>'
    blocks=''
    if rm_next:
        j,m=rm_next
        hora=m['hora'] if m['hora'] else 'hora por confirmar'
        blocks+=f'''<h3 class="lbl">Próximo partido</h3>
<a class="bigrow rm" href="jornada-{j}.html"><span class="tag">J{j} · {fdate(m["fecha"])} · {hora}</span>
<span class="bigt">{html.escape(m["local"])} vs {html.escape(m["visitante"])}</span></a>'''
    if rm_last:
        j,m=rm_last
        est='G' if False else ''
        blocks+=f'''<h3 class="lbl">Último resultado</h3>
<a class="bigrow" href="jornada-{j}.html"><span class="tag">J{j} · {fdate(m["fecha"])}</span>
<span class="bigt">{html.escape(m["local"])} {m["gl"]} - {m["gv"]} {html.escape(m["visitante"])}</span></a>'''
    home=f'''<div class="kicker">3ª ANDALUZA JUVENIL MÁLAGA · GRUPO 1</div>
<h1>C.D. Fútbol Romeral · Temporada 2026/27</h1>
<p class="lede">Clasificación, resultados y calendario del grupo.</p>
<p class="upd">Actualizado: {stamp}</p>
{stats}
{blocks}
<p class="src">Fuente: <a href="https://www.rfaf.es/pnfg/NPcd/NFG_VisClasificacion?cod_primaria=1000120&amp;codgrupo=48465932&amp;codcompeticion=48465931">rfaf.es</a></p>'''
    (OUT/'index.html').write_text(page('Inicio','index.html',home),encoding='utf-8')

    # --- clasificacion
    rows=''
    for t in tabla:
        cls=' class="rm"' if t['romeral'] else ''
        rows+=f'''<tr{cls}><td class="pos">{t["pos"]}</td><td class="eq">{crest_img(escudo_file.get(t["code"],""))}<span>{html.escape(t["equipo"])}</span></td><td class="num pts">{t["pts"]}</td><td class="num">{t["j"]}</td><td class="num">{t["g"]}</td><td class="num">{t["e"]}</td><td class="num">{t["p"]}</td><td class="num">{t["gf"]}</td><td class="num">{t["gc"]}</td></tr>\n'''
    body=f'''<div class="kicker">GRUPO 1</div>
<h1>Clasificación</h1>
<p class="upd">Actualizado: {stamp}</p>
<table class="tabla"><thead><tr><th>#</th><th>Equipo</th><th>Pts</th><th>J</th><th>G</th><th>E</th><th>P</th><th>GF</th><th>GC</th></tr></thead>
<tbody>{rows}</tbody></table>'''
    (OUT/'clasificacion.html').write_text(page('Clasificación','clasificacion.html',body),encoding='utf-8')

    # --- jornadas
    for j in range(1,NJ+1):
        ms=jornadas.get(j,[])
        fo=fechas_org.get(j,'')
        prevl=f'<a class="pj" href="jornada-{j-1}.html">‹ J{j-1}</a>' if j>1 else '<span class="pj off"></span>'
        nextl=f'<a class="pj" href="jornada-{j+1}.html">J{j+1} ›</a>' if j<NJ else '<span class="pj off"></span>'
        rows='\n'.join(match_row(m,escudo_file) for m in ms)
        body=f'''<div class="jnav">{prevl}<span class="jt">Jornada {j}{f" · {fdate(fo)}" if fo else ""}</span>{nextl}</div>
{rows}'''
        (OUT/f'jornada-{j}.html').write_text(page(f'Jornada {j}','calendario.html',body),encoding='utf-8')
    # calendario.html = jornada actual
    ms=jornadas.get(actual,[])
    fo=fechas_org.get(actual,'')
    prevl=f'<a class="pj" href="jornada-{actual-1}.html">‹ J{actual-1}</a>' if actual>1 else '<span class="pj off"></span>'
    nextl=f'<a class="pj" href="jornada-{actual+1}.html">J{actual+1} ›</a>' if actual<NJ else '<span class="pj off"></span>'
    rows='\n'.join(match_row(m,escudo_file) for m in ms)
    body=f'''<div class="kicker">CALENDARIO Y RESULTADOS</div>
<div class="jnav">{prevl}<span class="jt">Jornada {actual}{f" · {fdate(fo)}" if fo else ""}</span>{nextl}</div>
{rows}
<p class="upd">Actualizado: {stamp}</p>'''
    (OUT/'calendario.html').write_text(page('Calendario y resultados','calendario.html',body),encoding='utf-8')

if __name__=='__main__':
    main()
