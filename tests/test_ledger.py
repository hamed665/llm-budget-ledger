import unittest
import tempfile
from concurrent.futures import ThreadPoolExecutor
from tokenledger.core import Ledger, estimate, microdollars, BudgetExceeded

class LedgerTests(unittest.TestCase):
    def setUp(self): self.l = Ledger(); self.l.configure('t','1')
    def tearDown(self): self.l.close()
    def test_exact_conversion(self): self.assertEqual(microdollars('0.000001'),1)
    def test_estimate_ceil(self): self.assertEqual(estimate(1,0,'0.25','0'),1)
    def test_invalid_amount(self):
        for v in ('NaN','-1','0.0000001'):
            with self.assertRaises(ValueError): microdollars(v)
    def test_reserve_settle_refund(self):
        self.l.reserve('t','r',800000); self.l.finish('t','r',300000)
        self.assertEqual(self.l.balance('t')['available_micro_usd'],700000)
    def test_idempotency(self):
        self.l.reserve('t','r',1); self.l.reserve('t','r',1)
        with self.assertRaises(ValueError): self.l.reserve('t','r',2)
        self.l.finish('t','r',1); self.l.finish('t','r',1)
    def test_overrun_is_recorded(self):
        self.l.reserve('t','r',100); self.l.finish('t','r',1100000)
        self.assertEqual(self.l.balance('t')['available_micro_usd'],-100000)
        with self.assertRaises(BudgetExceeded): self.l.reserve('t','s',1)
    def test_release(self):
        self.l.reserve('t','r',1000000); self.l.finish('t','r')
        self.assertEqual(self.l.balance('t')['available_micro_usd'],1000000)
    def test_tenant_isolation(self):
        with self.assertRaises(ValueError): self.l.reserve('other','r',1)
    def test_concurrent_reservation(self):
        with tempfile.TemporaryDirectory() as d:
            path=d+'/ledger.db'; seed=Ledger(path); seed.configure('t','1'); seed.close()
            def reserve(key):
                ledger=Ledger(path)
                try: ledger.reserve('t',key,700000); return True
                except BudgetExceeded: return False
                finally: ledger.close()
            with ThreadPoolExecutor(2) as pool:
                self.assertEqual(sum(pool.map(reserve,['a','b'])),1)
