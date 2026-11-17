#!/usr/bin/env python3
"""Block publication when match cards disagree with the canonical schedule."""
import html,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def verify(data, pages):
    checked=0
    for j,matches in data['jornadas'].items():
        targets=[f'jornada-{j}.html']
        if int(j)==int(data['jornada_actual']): targets.append('jornadas.html')
        for target in targets:
            cards=re.split(r'<div class="mwrap(?: rm)?">',pages[target])[1:]
            assert len(cards)==len(matches),f'{target}: incorrect match count'
            for match in matches:
                selected=[c for c in cards if html.escape(match['local']) in c and html.escape(match['visitante']) in c]
                assert len(selected)==1,f'{target}: missing or duplicate match'
                if match['gl']=='':
                    card=selected[0];date=match['fecha'].replace('-','/')
                    assert date in card,f'{target}: wrong date for {match["local"]}'
                    if match['hora']: assert f'>{match["hora"]}<' in card,f'{target}: wrong time for {match["local"]}'
                checked+=1
    next_game=next(((j,m) for j,ms in sorted(data['jornadas'].items(),key=lambda x:int(x[0])) for m in ms if m['romeral'] and m['gl']==''),None)
    if next_game:
        j,m=next_game;block=re.search(r'<a class="bigrow rm"[^>]*>(.*?)</a>',pages['index.html'],re.S)
        assert block,'Missing next-match card'
        block=block.group(1)
        for v in [m['local'],m['visitante'],m['fecha'].replace('-','/'),m['hora'] or 'hora por confirmar']:
            assert html.escape(v) in block,'Next-match card disagrees with schedule'
        checked+=1
    return checked
if __name__=='__main__':
    data=json.loads((ROOT/'raw/data.json').read_text());pages={p.name:p.read_text() for p in (ROOT/'docs').glob('*.html')}
    print(f'Schedule coherence OK: {verify(data,pages)} match cards checked.')
