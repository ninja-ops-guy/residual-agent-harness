"""Execute base-commit modules in memory, then run the current behavioral tests."""
import subprocess
import pytest
from demo.cloud_gateway import server
from scripts import qualification_active_http_soak

BASE_HEAD='d796f36b75e730a0bab71bdba564206174393719'
for module,path in [(server,'demo/cloud_gateway/server.py'),
                    (qualification_active_http_soak,'scripts/qualification_active_http_soak.py')]:
    source=subprocess.check_output(['git','show',BASE_HEAD+':'+path],text=True)
    exec(compile(source,path,'exec'),module.__dict__)
raise SystemExit(pytest.main(['tests/security/test_r4_01_network_authority.py','-q']))
