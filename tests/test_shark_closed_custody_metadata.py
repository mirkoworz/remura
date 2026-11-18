"""REMURA Track B v0.4 LAB — 18/11/2026. Metadata-only synthetic cases."""
import sqlite3,unittest
from scripts.shark_closed_custody_reconcile import causal_metadata,CAUSAL_COLUMNS,CAUSAL_TRIGGERS

class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
    def fixture(self,*,missing=None,skip_trigger=False,view=False):
        for name,cols in CAUSAL_COLUMNS.items():
            if view and name=="squalincome_history":
                self.db.execute("CREATE VIEW "+name+" AS SELECT 1 AS symbol")
                continue
            names=[c for c in cols if (name,c)!=missing]
            self.db.execute("CREATE TABLE "+name+" ("+",".join(names)+")")
        for name,triggers in CAUSAL_TRIGGERS.items():
            for idx,t in enumerate(triggers):
                if skip_trigger and idx==1:continue
                # Deliberately non-protective: names are NOT semantic proof.
                self.db.execute("CREATE TRIGGER "+t+" AFTER INSERT ON "+name+" BEGIN SELECT 1; END")
        self.db.execute("PRAGMA query_only=ON")
    def test_complete_shape_only(self):
        self.fixture()
        statements=[]
        self.db.set_trace_callback(statements.append)
        self.assertEqual(causal_metadata(self.db),"CAUSAL_QUERY_METADATA_PRESENT")
        self.assertTrue(all("SELECT" not in s.upper() or "SQLITE_MASTER" in s.upper() for s in statements))
    def test_missing_columns(self):
        self.fixture(missing=("research_squalincome_price_evidence","observed_at"))
        self.assertEqual(causal_metadata(self.db),"REQUIRED_COLUMNS_MISSING")
    def test_trigger_names_missing(self):
        self.fixture(skip_trigger=True)
        self.assertEqual(causal_metadata(self.db),"REQUIRED_TRIGGER_NAMES_MISSING")
    def test_view_not_table(self):
        self.fixture(view=True)
        self.assertEqual(causal_metadata(self.db),"REQUIRED_ORDINARY_TABLES_MISSING")
    def test_empty_and_query_only_gate(self):
        with self.assertRaises(ValueError):causal_metadata(self.db)
        self.db.execute("PRAGMA query_only=ON")
        self.assertEqual(causal_metadata(self.db),"REQUIRED_ORDINARY_TABLES_MISSING")
if __name__=="__main__":unittest.main()
