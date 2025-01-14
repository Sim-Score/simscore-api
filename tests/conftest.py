import sys
from pathlib import Path

# Add project root to Python path
project_root = str(Path(__file__).parent.parent)
sys.path.append(project_root)

# Configure pytest-asyncio
def pytest_configure(config):
    config.inicfg['asyncio_mode'] = 'auto'
    config.inicfg['asyncio_default_fixture_loop_scope'] = 'function'
