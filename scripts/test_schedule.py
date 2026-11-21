import copy,json,unittest
from pathlib import Path
from verify_schedule import verify,ROOT
class ScheduleTest(unittest.TestCase):
    def setUp(self):
        self.data=json.loads((ROOT/'raw/data.json').read_text())
        self.pages={p.name:p.read_text() for p in (ROOT/'docs').glob('*.html')}
    def test_current(self):
        self.assertGreater(verify(self.data,self.pages),240)
    def test_stale_views_rejected(self):
        j,m=next((j,m) for j,ms in sorted(self.data['jornadas'].items(),key=lambda x:int(x[0])) for m in ms if m['romeral'] and m['gl']=='')
        current=str(self.data['jornada_actual'])
        current_match=next((m for m in self.data['jornadas'][current] if m['gl']==''),None)
        fixtures=[('index.html',m),(f'jornada-{j}.html',m)]
        if current_match: fixtures.append(('jornadas.html',current_match))
        for target,match in fixtures:
            with self.subTest(target=target):
                pages=dict(self.pages)
                date=match['fecha'].replace('-','/')
                self.assertIn(date,pages[target],f'{target}: stale-date fixture must modify page')
                pages[target]=pages[target].replace(date,'01/01/1900')
                with self.assertRaises(AssertionError):verify(self.data,pages)
    def test_current_round_cards_required(self):
        pages=dict(self.pages)
        pages['jornadas.html']=pages['jornadas.html'].replace('class="mwrap','class="missing-match')
        with self.assertRaises(AssertionError):verify(self.data,pages)
if __name__=='__main__':unittest.main()
