import tempfile,unittest
from pathlib import Path
from app import Record,PipelineError,parse_csv,rank,select_zero_loss,subscription_line
class Tests(unittest.TestCase):
 def test_ratio_and_chinese_columns(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"a.csv"; p.write_text("IP 地址,已发送,已接收,丢包率,平均延迟,下载速度(MB/s)\n1.1.1.1,10,10,0,80,10.123\n1.0.0.1,10,9,0.1,70,20\n")
   x=parse_csv(p,443); self.assertEqual(x[1].loss_ratio,.1); self.assertEqual(x[0].speed_mbps,10.123)
 def test_invalid_loss_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"a.csv"; p.write_text("IP,Loss\n1.1.1.1,33\n")
   with self.assertRaises(PipelineError): parse_csv(p,443)
 def test_missing_rows_not_inferred(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/"a.csv"; p.write_text("IP,Loss\n1.1.1.1,0\n")
   self.assertEqual(len(parse_csv(p,443)),1)
 def test_sort_full_precision(self):
  a=Record("1.1.1.1",443,10,10,0,80,10.001); b=Record("1.1.1.2",443,10,10,0,80,10.002)
  self.assertEqual(rank([a,b])[0],b)
 def test_top80_then_retest_top50_policy(self):
  rows=[Record(f"10.0.{i//256}.{i%256}",443,10,10,0,100,100.0-i) for i in range(100)]
  top80=select_zero_loss(rows,80)
  retest=top80[:50]
  self.assertEqual(len(top80),80)
  self.assertEqual(len(retest),50)
  self.assertEqual(retest[0].speed_mbps,100.0)
  self.assertEqual(retest[-1].speed_mbps,51.0)
 def test_loss_and_missing_measurements_excluded(self):
  rows=[Record("1.1.1.1",443,10,10,0,10,99),Record("1.1.1.2",443,10,10,.01,10,100),Record("1.1.1.3",443,10,10,None,10,101)]
  self.assertEqual([r.ip for r in select_zero_loss(rows,80)],["1.1.1.1"])
 def test_subscription_name(self):
  x=Record("1.1.1.1",443,10,10,0,94,63.21,"JP","Tokyo")
  self.assertEqual(subscription_line(x),"1.1.1.1:443#JP-63.21MB/s-94ms-Tokyo")
  with self.assertRaises(PipelineError): subscription_line(Record("1.1.1.1",443,10,10,0,94,63.21))
if __name__=="__main__": unittest.main()
