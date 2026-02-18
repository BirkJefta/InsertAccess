import os
port: 8769
POLL_MS = 1000
API_BASE_URL = f'https://localhost:{7230}/api'

#kopi til låste filer
TEMP_DIR = os.path.join(os.environ.get('TEMP', 'C:\\Temp'), 'BridgeSync')

