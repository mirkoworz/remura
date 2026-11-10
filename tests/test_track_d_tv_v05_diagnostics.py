"""Offline D0.5 diagnostic source contract and syntactic delimiter checks.

This is NOT a Pine compiler. User must compile/observe on TradingView.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / "experiments" / "tradingview"
PATHS = [ROOT / "remura_shark_cvd_fx_v04.pine", ROOT / "remura_shark_cvd_fx_v05.pine"]


def balance_pine_delimiters(source):
    """Check (), [], {} outside quoted Pine strings and // comments."""
    stack = []
    matching = {")": "(", "]": "[", "}": "{"}
    for lineno, line in enumerate(source.splitlines(), 1):
        in_string = None
        escaped = False
        for col, char in enumerate(line, 1):
            if in_string is not None:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == in_string:
                    in_string = None
            elif char == '"' or char == "'":
                in_string = char
            elif line[col - 1:].startswith("//"):
                break
            elif char in "([{":
                stack.append((char, lineno, col))
            elif char in ")]}":
                if not stack or stack[-1][0] != matching[char]:
                    return f"unexpected {char} at {lineno}:{col}"
                stack.pop()
        if in_string is not None:
            return f"unterminated string on line {lineno}"
    return f"unclosed {stack[-1]}" if stack else None


class TestD05(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pine = PATHS[-1].read_text(encoding="utf8")

    def test_balanced_delimiters_prevents_ce10015_regression(self):
        for path in PATHS:
            text = path.read_text(encoding="utf8")
            self.assertIsNone(balance_pine_delimiters(text), path.name)

    def test_explicit_source_and_strict_gate(self):
        p = self.pine
        self.assertIn('const string FEED = "FX:EURUSD"', p)
        self.assertIn('request.security_lower_tf(FEED, "1"', p)
        self.assertIn('request.security(FEED, "5"', p)
        self.assertIn('fxT != time', p)  # fail-closed mismatch branch
        self.assertIn('validSession := false', p)
        self.assertIn('if validSession', p)
        self.assertIn('if chartOk and researchAlerts and barstate.isrealtime and barstate.isconfirmed and (bullish or bearish)', p)
        self.assertIn('input.bool(false, "Alert SOLO RICERCA', p)
        self.assertIn('barstate.isconfirmed and validSession', p)

    def test_partial_plot_separate_from_daily_and_no_trade(self):
        p = self.pine
        self.assertIn('plot(chartOk ? cvd : na, "CVD GIORNALIERO', p)
        self.assertIn('plot(chartOk and not validSession ? partialPlot : na, "CVD PARZIALE (NO SIGNAL)"', p)
        self.assertIn('partialPlot := segmentBars >= 2 ? segmentCvd : na', p)
        self.assertIn('segmentBars := 0', p)
        self.assertIn('lastQualityReason := reason', p)
        self.assertIn('1M_PRESENTI_', p)
        self.assertIn('ORARI_1M_NON_CONTIGUI', p)
        self.assertIn('Barre 1m ultima 5m chiusa:', p)
        self.assertIn('const string MODEL = "remura_fx_1m_cvd_d0.5"', p)
        for bad in ('strategy.entry(', 'strategy.order(', 'runtime.error('):
            self.assertNotIn(bad, p)

    def test_test_helper_rejects_exact_old_missing_parenthesis(self):
        good = 'table.cell(diag, 0, 2, "a", bgcolor=color.new(color.black, 15))'
        bad = good[:-1]
        self.assertIsNone(balance_pine_delimiters(good))
        self.assertIsNotNone(balance_pine_delimiters(bad))


if __name__ == "__main__":
    unittest.main()
