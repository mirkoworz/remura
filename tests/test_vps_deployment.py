"""Deployment contract tests: no network, no root actions, no account secrets."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class VpsDeploymentTests(unittest.TestCase):
    def test_loopback_server_unit_never_opens_public_port(self):
        unit=(ROOT/"deploy"/"remura-private.service").read_text()
        app=(ROOT/"scripts"/"private_server.py").read_text()
        self.assertIn('SERVER_HOST="127.0.0.1"',app)
        self.assertIn("User=remura",unit)
        self.assertIn("ProtectSystem=strict",unit)
        self.assertIn("ReadWritePaths=/opt/remura/private",unit)
        self.assertIn("NoNewPrivileges=true",unit)
        self.assertNotIn("0.0.0.0",unit)

    def test_setup_never_wipes_private_token_directory_on_upgrades(self):
        for name in ("bootstrap-ubuntu.sh","update-ubuntu.sh"):
            script=(ROOT/"deploy"/name).read_text()
            self.assertIn("--exclude='private/'",script)
            self.assertIn("--exclude='.env'",script)
            self.assertIn("--chown=root:root",script)
            self.assertNotIn("chown -R root:root /opt/remura",script)
            self.assertNotIn("tailscale funnel",script.lower())

    def test_shipped_env_disables_credentials_and_collectors(self):
        template=(ROOT/"deploy"/"remura.env.example").read_text()
        self.assertIn("REMURA_COLLECTOR_ENABLED=0",template)
        self.assertIn("REMURA_RETAIL_ENABLED=0",template)
        self.assertFalse(any(line.startswith(("CTRADER_CLIENT_SECRET=",
            "CTRADER_REFRESH_TOKEN=","MYFXBOOK_PASSWORD=")) for line in template.splitlines()))

    def test_private_website_rejects_sensitive_files(self):
        import sys
        sys.path.insert(0,str(ROOT/"scripts"))
        from private_server import resolve_asset
        self.assertIsNone(resolve_asset("/.env"))
        self.assertIsNone(resolve_asset("/private/ctrader-tokens.json"))
        self.assertIsNone(resolve_asset("/deploy/remura.env.example"))
        self.assertIsNotNone(resolve_asset("/index.html"))

if __name__=="__main__":
    unittest.main()
