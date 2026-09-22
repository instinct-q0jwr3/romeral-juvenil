#!/usr/bin/env python3
"""Fetch RFAF pnfg pages for C.D. Futbol Romeral (3a Andaluza Juvenil Malaga G1) and build a static site in docs/."""
from __future__ import annotations
import html,json,re,subprocess,sys,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'raw'; OUT=ROOT/'docs'
TEAM='C.D. FUTBOL ROMERAL'
TEAM_SHORT='ROMERAL'
URLS={
 'clasificacion':'https://www.rfaf.es/pnfg/NPcd/NFG_VisClasificacion?cod_primaria=1000120&codgrupo=48465932&codcompeticion=48465931',
 'grupo':'https://www.rfaf.es/pnfg/NPcd/NFG_VisCompeticiones_Grupo?cod_primaria=1000123&codequipo=2064582&codgrupo=48465932',
}
def fetch(name,url):
    jar=RAW/'cookies.txt'
    # pnfg requires the cookie gate: first request sets the cookie, second returns content
    for attempt in range(3):
        subprocess.run(['curl','-sL','--max-time','40','-b',str(jar),'-c',str(jar),url,'-o',str(RAW/f'{name}.html')],check=False)
        t=(RAW/f'{name}.html').read_text(encoding='latin-1',errors='replace') if (RAW/f'{name}.html').exists() else ''
        if len(t)>5000 and 'No se ha aceptado el cookie' not in t:
            return t
    raise SystemExit(f'fetch failed for {name}')

def clean(s):
    s=re.sub(r'<[^>]+>','',s)
    s=html.unescape(s).replace('\xa0',' ')
    return re.sub(r'\s+',' ',s).strip()

def parse_clasificacion(h):
    rows=re.findall(r'<tr[^>]*>(.*?)</tr>',h,re.S)
    table=[]
    for r in rows:
        cells=[clean(c) for c in re.findall(r'<td[^>]*>(.*?)</td>',r,re.S)]
        if len(cells)>=12 and cells[1].isdigit():
            def n(i):
                try: return int(cells[i])
                except Exception: return 0
            table.append({'pos':int(cells[1]),'equipo':cells[2],'pts':cells[3],
                          'j':n(4)+n(8),'g':n(5)+n(9),'e':n(6)+n(10),'p':n(7)+n(11),
                          'gf':cells[12],'gc':cells[13] if len(cells)>13 else '',
                          'romeral':TEAM_SHORT in cells[2].upper()})
    return table

def parse_partidos(h):
    rows=re.findall(r'<tr>\s*<td class=font_responsive align=center style="vertical-align: middle;"><h5>(\d+)</h5></td>(.*?)</tr>',h,re.S)
    partidos=[]
    for j,body in rows:
        hs=re.findall(r'<h5[^>]*>(.*?)</h5>',body,re.S)
        if len(hs)<3: continue
        local,visitante,fecha=clean(hs[0]),clean(hs[1]),clean(hs[2])
        m=re.search(r'<b>(\d+)</b>\s*-\s*<b>\s*(\d+)</b>',body)
        res=f'{m.group(1)} - {m.group(2)}' if m else ''
        badge=re.search(r'title=(Ganado|Empatado|Perdido)',body)
        estado={'Ganado':'G','Empatado':'E','Perdido':'P'}.get(badge.group(1),'') if badge else ''
        fm=re.match(r'(\d{2}-\d{2}-\d{4})\s*(.*)',fecha)
        partidos.append({'jornada':int(j),'local':local,'visitante':visitante,
                         'fecha':fm.group(1) if fm else fecha,'hora':(fm.group(2).strip() if fm and fm.group(2).strip() else 'hora por confirmar'),
                         'resultado':res,'estado':estado,'casa':TEAM_SHORT in local.upper()})
    return partidos

CSS=''':root{--bg:#0b0d0f;--panel:#111418;--line:#242a30;--text:#e8edf2;--muted:#8c98a4;--cyan:#74c7e8;--green:#8ad6b1;--red:#e88a8a;--max:960px}*{box-sizing:border-box}html{background:var(--bg);color:var(--text);font-family:Inter,ui-sans-serif,system-ui,-apple-system,sans-serif}body{margin:0}a{color:var(--cyan);text-decoration:none}a:hover{color:#b8e8fb}header{min-height:58px;border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 28px;gap:30px;flex-wrap:wrap}main{max-width:var(--max);margin:0 auto;padding:40px 28px 80px}.brand{font-weight:750;color:var(--text);font-size:17px;letter-spacing:-.02em}.brand span{color:var(--cyan)}nav{display:flex;gap:22px;flex:1}nav a{font-size:13px;color:var(--muted)}nav a:hover{color:var(--text)}nav a.active{color:var(--text);font-weight:700;border-bottom:2px solid var(--cyan);padding-bottom:2px}.page-title{margin-bottom:26px}.page-title h1{font-size:clamp(24px,3.2vw,30px);margin:8px 0 6px;letter-spacing:-.02em}.page-title p{color:var(--muted);margin:0;font-size:13px}.eyebrow{text-transform:uppercase;letter-spacing:.13em;color:var(--green);font-size:11px;font-weight:700}.meta{color:var(--muted);font:12px ui-monospace,monospace}table{border-collapse:collapse;width:100%;font-size:14px}th{font:11px ui-monospace,monospace;color:var(--muted);text-transform:uppercase;letter-spacing:.06em;text-align:left;padding:6px 10px;border-bottom:1px solid var(--line)}td{padding:8px 10px;border-bottom:1px solid #1c2126}tr.romeral td{background:#12202a;color:var(--text);font-weight:650}tr.romeral td:first-child{border-left:3px solid var(--cyan)}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}.next{display:flex;gap:18px;align-items:baseline;flex-wrap:wrap;border:1px solid var(--line);border-left:3px solid var(--green);padding:14px 18px;margin:0 0 34px;background:var(--panel)}.next .eq{font-size:17px;font-weight:700}.next .cuando{font:12px ui-monospace,monospace;color:var(--green)}.next .donde{font:12px ui-monospace,monospace;color:var(--muted)}.stats{display:flex;gap:20px;margin-bottom:26px;font:12px ui-monospace,monospace;color:var(--muted)}.stats b{color:var(--text)}.badge{display:inline-block;min-width:16px;text-align:center;font:700 10px ui-monospace,monospace;border-radius:3px;padding:1px 4px;color:#06222e}.badge.G{background:var(--green)}.badge.E{background:var(--cyan)}.badge.P{background:var(--red)}.res{font:13px ui-monospace,monospace;white-space:nowrap}.pend{color:var(--muted)}h2.sec{font-size:12px;text-transform:uppercase;letter-spacing:.12em;color:#c3cbd3;border-bottom:1px solid var(--line);padding-bottom:8px;margin:38px 0 0}footer{border-top:1px solid var(--line);padding:22px;text-align:center;color:#5f6972;font-size:12px}@media(max-width:640px){main{padding:26px 14px 60px}header{padding:10px 16px;gap:8px 16px}.hide-m{display:none}.next .eq{font-size:15px}}'''

def shell(title,content,active):
    nav=[('index.html','Inicio'),('clasificacion.html','Clasificación'),('calendario.html','Calendario y resultados')]
    links=''.join(f'<a href="{u}"'+((' class="active" aria-current="page"') if k==active else '')+f'>{l}</a>' for u,l in [(u,l) for u,l in nav] for k in [u.replace('.html','').replace('index','inicio')])
    return f'''<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)} · C.D. Fútbol Romeral</title><link rel="stylesheet" href="style.css"></head><body><header><a class="brand" href="index.html"><span>C.D.</span> Fútbol Romeral</a><nav>{links}</nav></header><main>{content}</main><footer>Datos: Real Federación Andaluza de Fútbol (rfaf.es) · 3ª Andaluza Juvenil Málaga · Grupo 1</footer></body></html>'''

def fmt_fecha(f):
    try:
        d=datetime.datetime.strptime(f,'%d-%m-%Y')
        return d.strftime('%d/%m/%Y')
    except Exception: return f

def main():
    h_clasi=fetch('clasificacion',URLS['clasificacion'])
    h_grupo=fetch('grupo',URLS['grupo'])
    tabla=parse_clasificacion(h_clasi)
    partidos=parse_partidos(h_grupo)
    if not tabla or not partidos: raise SystemExit('parse failed')
    now=datetime.datetime.now(ZoneInfo('Europe/Madrid')).strftime('%d/%m/%Y, %H:%M %Z')
    jugados=[p for p in partidos if p['resultado']]
    prox=[p for p in partidos if not p['resultado']]
    r=[t for t in tabla if t['romeral']]
    pos=r[0] if r else None
    (RAW/'data.json').write_text(json.dumps({'tabla':tabla,'partidos':partidos,'actualizado':now},ensure_ascii=False,indent=1))
    OUT.mkdir(exist_ok=True)
    (OUT/'.nojekyll').write_text('')
    (OUT/'style.css').write_text(CSS)
    # --- Inicio
    next_html=''
    if prox:
        p=prox[0]
        donde='Casa' if p['casa'] else 'Fuera'
        next_html=f'''<h2 class="sec">Próximo partido</h2><div class="next"><span class="cuando">J{p["jornada"]} · {fmt_fecha(p["fecha"])} · {p["hora"]}</span><span class="eq">{html.escape(p["local"])} vs {html.escape(p["visitante"])}</span><span class="donde">{donde}</span></div>'''
    ultimo=''
    if jugados:
        p=jugados[-1]
        ultimo=f'''<h2 class="sec">Último resultado</h2><div class="next" style="border-left-color:var(--cyan)"><span class="cuando">J{p["jornada"]} · {fmt_fecha(p["fecha"])}</span><span class="eq">{html.escape(p["local"])} {p["resultado"]} {html.escape(p["visitante"])}</span><span class="badge {p["estado"]}">{p["estado"]}</span></div>'''
    pos_html=f'<div class="stats"><span><b>{pos["pos"]}º</b> clasificado</span><span><b>{pos["pts"]}</b> puntos</span><span><b>{pos["gf"]}-{pos["gc"]}</b> goles</span><span><b>{len(jugados)}</b> jugados</span></div>' if pos else ''
    body=f'''<div class="page-title"><span class="eyebrow">3ª Andaluza Juvenil Málaga · Grupo 1</span><h1>C.D. Fútbol Romeral · Temporada 2026/27</h1><p>Clasificación, resultados y calendario del grupo.</p></div><div class="stats"><span class="meta">Actualizado: {now}</span></div>{pos_html}{next_html}{ultimo}<p class="meta" style="margin-top:34px">Fuente: <a href="{URLS['grupo']}">rfaf.es</a></p>'''
    (OUT/'index.html').write_text(shell('Inicio',body,'inicio'))
    # --- Clasificacion
    rows=''.join(f'<tr class="{"romeral" if t["romeral"] else ""}"><td class="num">{t["pos"]}</td><td>{html.escape(t["equipo"])}</td><td class="num"><b>{t["pts"]}</b></td><td class="num">{t["j"]}</td><td class="num hide-m">{t["g"]}</td><td class="num hide-m">{t["e"]}</td><td class="num hide-m">{t["p"]}</td><td class="num hide-m">{t["gf"]}</td><td class="num hide-m">{t["gc"]}</td></tr>' for t in tabla)
    body=f'''<div class="page-title"><span class="eyebrow">Grupo 1</span><h1>Clasificación</h1><p class="meta">Actualizado: {now}</p></div><table><thead><tr><th class="num">#</th><th>Equipo</th><th class="num">Pts</th><th class="num">J</th><th class="num hide-m">G</th><th class="num hide-m">E</th><th class="num hide-m">P</th><th class="num hide-m">GF</th><th class="num hide-m">GC</th></tr></thead><tbody>{rows}</tbody></table>'''
    (OUT/'clasificacion.html').write_text(shell('Clasificación',body,'clasificacion'))
    # --- Calendario
    rows=''
    for p in partidos:
        rom=' class="romeral"' if p['casa'] else ''
        if p['resultado']:
            res=f'<span class="res">{p["resultado"]}</span> <span class="badge {p["estado"]}">{p["estado"]}</span>'
        else:
            res='<span class="res pend">-</span>'
        rows+=f'<tr{rom}><td class="num">{p["jornada"]}</td><td>{html.escape(p["local"])}</td><td>{html.escape(p["visitante"])}</td><td class="num">{res}</td><td class="num">{fmt_fecha(p["fecha"])}</td><td class="num hide-m">{p["hora"]}</td></tr>'
    body=f'''<div class="page-title"><span class="eyebrow">Temporada 2026/27</span><h1>Calendario y resultados</h1><p class="meta">Partidos del Romeral · Actualizado: {now}</p></div><table><thead><tr><th class="num">Jor.</th><th>Local</th><th>Visitante</th><th class="num">Resultado</th><th class="num">Fecha</th><th class="num hide-m">Hora</th></tr></thead><tbody>{rows}</tbody></table>'''
    (OUT/'calendario.html').write_text(shell('Calendario y resultados',body,'calendario'))
    print(f'Built site: {len(tabla)} equipos, {len(partidos)} partidos ({len(jugados)} jugados), actualizado {now}')

if __name__=='__main__': main()
