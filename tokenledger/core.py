"""Exact micro-dollar accounting with reserve/settle/release lifecycle."""
from decimal import Decimal, ROUND_CEILING
import sqlite3

def microdollars(amount):
    value = Decimal(str(amount))
    if not value.is_finite() or value < 0:
        raise ValueError('finite nonnegative amount required')
    result = value * 1_000_000
    if result != result.to_integral_value():
        raise ValueError('at most six decimal places')
    return int(result)

def estimate(input_tokens, output_tokens, input_per_million, output_per_million):
    if any(type(v) is not int or v < 0 for v in (input_tokens,output_tokens)):
        raise ValueError('nonnegative integer token counts required')
    rates = [Decimal(str(v)) for v in (input_per_million,output_per_million)]
    if any(not r.is_finite() or r < 0 for r in rates): raise ValueError('invalid rate')
    # USD / million tokens * tokens * microUSD / USD cancels the million.
    return int((input_tokens*rates[0] + output_tokens*rates[1]).to_integral_value(rounding=ROUND_CEILING))

class BudgetExceeded(ValueError): pass

class Ledger:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path, isolation_level=None, timeout=5)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS budgets(tenant TEXT PRIMARY KEY, ceiling INTEGER NOT NULL CHECK(ceiling>=0));
        CREATE TABLE IF NOT EXISTS requests(tenant TEXT, request_id TEXT, reserved INTEGER NOT NULL,
          actual INTEGER, state TEXT NOT NULL CHECK(state IN ('held','settled','released')),
          PRIMARY KEY(tenant,request_id));
        """)

    def configure(self, tenant, usd):
        if not tenant: raise ValueError('tenant required')
        limit = microdollars(usd)
        self.db.execute('BEGIN IMMEDIATE')
        try:
            used = self.balance(tenant)['committed_micro_usd']
            if limit < used: raise BudgetExceeded('limit below committed funds')
            self.db.execute('INSERT INTO budgets VALUES(?,?) ON CONFLICT(tenant) DO UPDATE SET ceiling=excluded.ceiling',(tenant,limit))
            self.db.commit()
        except BaseException:
            self.db.rollback(); raise

    def balance(self, tenant):
        row = self.db.execute('SELECT ceiling FROM budgets WHERE tenant=?',(tenant,)).fetchone()
        committed = self.db.execute("SELECT COALESCE(SUM(CASE WHEN state='held' THEN reserved WHEN state='settled' THEN actual ELSE 0 END),0) FROM requests WHERE tenant=?",(tenant,)).fetchone()[0]
        return {'limit_micro_usd': row[0] if row else 0, 'committed_micro_usd': committed,
                'available_micro_usd': (row[0] if row else 0)-committed}

    def reserve(self, tenant, request_id, amount_micro):
        if not tenant or not request_id or type(amount_micro) is not int or amount_micro < 0:
            raise ValueError('valid identifiers and nonnegative integer microUSD required')
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT * FROM requests WHERE tenant=? AND request_id=?',(tenant,request_id)).fetchone()
            if old:
                if old['reserved'] != amount_micro: raise ValueError('idempotency payload mismatch')
                self.db.commit(); return dict(old)
            if not self.db.execute('SELECT 1 FROM budgets WHERE tenant=?',(tenant,)).fetchone():
                raise ValueError('configure tenant first')
            if amount_micro > self.balance(tenant)['available_micro_usd']: raise BudgetExceeded('budget exhausted')
            self.db.execute("INSERT INTO requests VALUES(?,?,?,NULL,'held')",(tenant,request_id,amount_micro))
            self.db.commit()
            return {'tenant':tenant,'request_id':request_id,'reserved':amount_micro,'actual':None,'state':'held'}
        except BaseException:
            self.db.rollback(); raise

    def finish(self, tenant, request_id, actual_micro=None):
        if actual_micro is not None and (type(actual_micro) is not int or actual_micro < 0): raise ValueError('invalid actual usage')
        state = 'released' if actual_micro is None else 'settled'
        self.db.execute('BEGIN IMMEDIATE')
        try:
            old = self.db.execute('SELECT * FROM requests WHERE tenant=? AND request_id=?',(tenant,request_id)).fetchone()
            if not old: raise KeyError(request_id)
            if old['state'] != 'held':
                if (old['state'],old['actual']) != (state,actual_micro): raise ValueError('already finalized')
            else:
                # Actual usage is recorded even when it exceeds the estimate.
                self.db.execute('UPDATE requests SET state=?,actual=? WHERE tenant=? AND request_id=?',(state,actual_micro,tenant,request_id))
            self.db.commit()
            return self.balance(tenant)
        except BaseException:
            self.db.rollback(); raise

    def close(self): self.db.close()
