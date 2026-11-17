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
        for target in ['index.html',f'jornada-{j}.html','jornadas.html']:
            with self.subTest(target=target):
                pages=dict(self.pages);pages[target]=pages[target].replace(m['fecha'].replace('-','/'),'01/01/1900')
                with self.assertRaises(AssertionError):verify(self.data,pages)
if __name__=='__main__':unittest.main()
