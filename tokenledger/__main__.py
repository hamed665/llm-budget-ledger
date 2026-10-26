import json
from .core import Ledger, estimate
ledger = Ledger()
ledger.configure('demo-agency','1.00')
# Illustrative rates, not a provider's current price sheet.
hold = estimate(2000,1000,'2.50','10.00')
ledger.reserve('demo-agency','request-1',hold)
print(json.dumps({'reserved_micro_usd':hold,'settlement':ledger.finish('demo-agency','request-1',9000)},indent=2))
ledger.close()
