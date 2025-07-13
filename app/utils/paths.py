import os
from pathlib import Path

ROOT: Path = Path(os.getcwd().split('MyTube')[0]) / 'MyTube'

TEMP: Path = ROOT / 'temp'
TEMP.mkdir(exist_ok=True)

SERVICE_DATA: Path = ROOT / 'app' / 'services' / 'data'
SERVICE_DATA.mkdir(exist_ok=True)

PROXY: Path = SERVICE_DATA / 'proxy_port.txt'


