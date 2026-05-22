import socket
import time
import network

import config

try:
    import ujson as json
except ImportError:
    import json


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>ESP32 Network Radar</title>
  <style>
    :root {
      --bg: #070b10;
      --panel: rgba(15, 23, 32, .88);
      --panel2: rgba(24, 35, 48, .92);
      --line: rgba(126, 231, 255, .18);
      --text: #f4fbff;
      --muted: #91a8b8;
      --cyan: #23d9ff;
      --mint: #29f0b4;
      --blue: #7aa7ff;
      --yellow: #ffd166;
      --red: #ff5c7a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      overflow-x: hidden;
      background:
        radial-gradient(circle at 12% 12%, rgba(35, 217, 255, .18), transparent 28%),
        radial-gradient(circle at 88% 8%, rgba(41, 240, 180, .16), transparent 30%),
        linear-gradient(135deg, #070b10 0%, #0b1118 45%, #070b10 100%);
      color: var(--text);
      font-family: Arial, Helvetica, sans-serif;
    }
    body:before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: .25;
      background-image:
        linear-gradient(rgba(126, 231, 255, .08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(126, 231, 255, .08) 1px, transparent 1px);
      background-size: 44px 44px;
      mask-image: linear-gradient(to bottom, black, transparent 85%);
    }
    main {
      position: relative;
      width: min(1180px, calc(100% - 28px));
      margin: 0 auto;
      padding: 26px 0 42px;
    }
    header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 18px;
      margin-bottom: 18px;
    }
    .tag {
      margin: 0 0 5px;
      color: var(--mint);
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0;
    }
    h1, h2, p { margin: 0; letter-spacing: 0; }
    h1 {
      font-size: clamp(34px, 5vw, 62px);
      line-height: .95;
      text-shadow: 0 0 34px rgba(35, 217, 255, .22);
    }
    .subtitle {
      max-width: 620px;
      margin-top: 12px;
      color: var(--muted);
      font-size: 16px;
      line-height: 1.45;
    }
    .actions { display: flex; gap: 8px; }
    button {
      min-width: 132px;
      min-height: 50px;
      border: 0;
      border-radius: 6px;
      background: linear-gradient(135deg, var(--mint), var(--cyan));
      color: #031211;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 12px 32px rgba(35, 217, 255, .18);
    }
    button.secondary {
      background: linear-gradient(135deg, var(--blue), #b9ceff);
      color: #07101f;
    }
    button:disabled { opacity: .65; cursor: wait; }
    .dashboard {
      display: grid;
      grid-template-columns: minmax(320px, 1.15fr) minmax(320px, .85fr);
      gap: 14px;
      align-items: stretch;
      margin-bottom: 14px;
    }
    .hero, .panel, .box {
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: 0 18px 60px rgba(0, 0, 0, .35);
      backdrop-filter: blur(18px);
    }
    .hero {
      display: grid;
      grid-template-columns: 330px 1fr;
      gap: 18px;
      min-height: 380px;
      padding: 18px;
      border-radius: 8px;
      overflow: hidden;
    }
    .radar {
      position: relative;
      aspect-ratio: 1;
      align-self: center;
      border-radius: 50%;
      border: 1px solid rgba(35, 217, 255, .35);
      background:
        radial-gradient(circle, rgba(41, 240, 180, .18) 0 2px, transparent 3px),
        repeating-radial-gradient(circle, transparent 0 48px, rgba(35, 217, 255, .18) 49px 50px),
        linear-gradient(rgba(35, 217, 255, .18), rgba(35, 217, 255, .02));
      box-shadow: inset 0 0 45px rgba(35, 217, 255, .14), 0 0 42px rgba(41, 240, 180, .12);
    }
    .radar:before {
      content: "";
      position: absolute;
      inset: 50% 0 0 50%;
      transform-origin: 0 0;
      background: linear-gradient(90deg, rgba(41, 240, 180, .52), transparent 70%);
      clip-path: polygon(0 0, 100% 0, 0 100%);
      animation: sweep 3.2s linear infinite;
    }
    .radar:after {
      content: "";
      position: absolute;
      inset: 50%;
      width: 14px;
      height: 14px;
      margin: -7px;
      border-radius: 50%;
      background: var(--mint);
      box-shadow: 0 0 24px var(--mint);
    }
    .ring-line {
      position: absolute;
      inset: 50% 8%;
      height: 1px;
      background: rgba(126, 231, 255, .22);
    }
    .ring-line.v { transform: rotate(90deg); }
    .dot {
      position: absolute;
      width: 13px;
      height: 13px;
      border-radius: 50%;
      background: var(--cyan);
      box-shadow: 0 0 22px var(--cyan);
    }
    .dot.router { left: 65%; top: 32%; background: var(--yellow); box-shadow: 0 0 22px var(--yellow); }
    .dot.node1 { left: 26%; top: 58%; }
    .dot.node2 { left: 72%; top: 68%; background: var(--mint); box-shadow: 0 0 22px var(--mint); }
    @keyframes sweep { to { transform: rotate(360deg); } }
    .hero-info {
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 18px;
      padding: 8px 4px;
    }
    .status-pill {
      width: max-content;
      border: 1px solid rgba(41, 240, 180, .35);
      border-radius: 999px;
      padding: 8px 12px;
      color: var(--mint);
      background: rgba(41, 240, 180, .08);
      font-size: 13px;
      font-weight: 700;
    }
    .hero-copy h2 {
      margin-bottom: 10px;
      font-size: 28px;
    }
    .hero-copy p {
      color: var(--muted);
      line-height: 1.5;
    }
    .legend {
      display: grid;
      gap: 9px;
      color: var(--muted);
      font-size: 14px;
    }
    .legend span {
      display: flex;
      align-items: center;
      gap: 9px;
    }
    .legend i {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: var(--cyan);
      box-shadow: 0 0 12px var(--cyan);
    }
    .legend .router-i { background: var(--yellow); box-shadow: 0 0 12px var(--yellow); }
    .legend .esp-i { background: var(--mint); box-shadow: 0 0 12px var(--mint); }
    .grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 10px;
      margin-bottom: 14px;
    }
    .box {
      min-height: 96px;
      padding: 16px;
      border-radius: 8px;
    }
    .box span, .muted { color: var(--muted); font-size: 13px; }
    .box strong {
      display: block;
      margin-top: 8px;
      font-size: 25px;
      overflow-wrap: anywhere;
    }
    .panel {
      min-height: 380px;
      padding: 18px;
      border-radius: 8px;
    }
    .panel-head {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding-bottom: 12px;
      border-bottom: 1px solid var(--line);
    }
    .panel-head h2 { font-size: 24px; }
    #message {
      margin-top: 14px;
      padding: 14px;
      border-radius: 8px;
      color: var(--muted);
      background: rgba(126, 231, 255, .06);
    }
    #list { display: grid; gap: 8px; padding-top: 12px; }
    .device {
      display: grid;
      grid-template-columns: auto 1fr auto;
      gap: 12px;
      align-items: center;
      min-height: 76px;
      padding: 14px;
      border-radius: 6px;
      background: var(--panel2);
      border: 1px solid rgba(126, 231, 255, .1);
    }
    .icon {
      display: grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 6px;
      background: rgba(35, 217, 255, .1);
      color: var(--cyan);
      font-size: 24px;
    }
    .device h3 { margin: 0 0 5px; font-size: 17px; }
    .badge {
      border-radius: 999px;
      padding: 6px 10px;
      background: rgba(41, 240, 180, .12);
      color: var(--mint);
      font-size: 12px;
      font-weight: 700;
    }
    .scanbar {
      height: 8px;
      margin-top: 14px;
      border-radius: 999px;
      overflow: hidden;
      background: rgba(126, 231, 255, .1);
    }
    .scanbar div {
      width: 0;
      height: 100%;
      background: linear-gradient(90deg, var(--mint), var(--cyan), var(--blue));
      box-shadow: 0 0 22px rgba(35, 217, 255, .5);
    }
    .scanning .scanbar div { animation: loading 1.4s ease-in-out infinite; }
    @keyframes loading {
      0% { width: 10%; transform: translateX(-20%); }
      50% { width: 75%; transform: translateX(20%); }
      100% { width: 10%; transform: translateX(920%); }
    }
    @media (max-width: 720px) {
      header, .panel-head { flex-direction: column; align-items: stretch; }
      .dashboard { grid-template-columns: 1fr; }
      .hero { grid-template-columns: 1fr; }
      .actions { flex-direction: column; }
      button { width: 100%; }
      .grid { grid-template-columns: repeat(2, 1fr); }
      .device { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <p class="tag">ESP32 live cyber lab</p>
        <h1>Network Radar</h1>
        <p class="subtitle">A small ESP32 turns into a local web server and scans the Wi-Fi network for active devices and open services.</p>
      </div>
      <div class="actions">
        <button onclick="scan('fast')">Quick sweep</button>
        <button class="secondary" onclick="scan('deep')">Full scan</button>
      </div>
    </header>

    <section class="dashboard">
      <div class="hero">
        <div class="radar">
          <div class="ring-line"></div>
          <div class="ring-line v"></div>
          <div class="dot router"></div>
          <div class="dot node1"></div>
          <div class="dot node2"></div>
        </div>
        <div class="hero-info">
          <span id="systemStatus" class="status-pill">SYSTEM READY</span>
          <div class="hero-copy">
            <h2>Live Wi-Fi intelligence</h2>
            <p>The ESP32 hosts this dashboard directly from the board. Each scan checks nearby network addresses and shows devices that respond on known service ports.</p>
          </div>
          <div class="legend">
            <span><i class="esp-i"></i> ESP32 scanner node</span>
            <span><i class="router-i"></i> Router / gateway</span>
            <span><i></i> Detected network device</span>
          </div>
        </div>
      </div>

      <section class="panel" id="panel">
        <div class="panel-head">
          <h2>Scan results</h2>
          <span id="ports" class="muted">Ports: -</span>
        </div>
        <div id="message">Choose a scan mode to start the network sweep.</div>
        <div class="scanbar"><div></div></div>
        <div id="list"></div>
      </section>
    </section>

    <section class="grid">
      <div class="box"><span>ESP32 address</span><strong id="ownIp">-</strong></div>
      <div class="box"><span>Router gateway</span><strong id="gateway">-</strong></div>
      <div class="box"><span>Devices found</span><strong id="count">0</strong></div>
      <div class="box"><span>Scan duration</span><strong id="time">-</strong></div>
    </section>
  </main>

  <script>
    const ownIp = document.getElementById("ownIp");
    const gateway = document.getElementById("gateway");
    const count = document.getElementById("count");
    const time = document.getElementById("time");
    const ports = document.getElementById("ports");
    const message = document.getElementById("message");
    const list = document.getElementById("list");
    const panel = document.getElementById("panel");
    const systemStatus = document.getElementById("systemStatus");

    function setButtons(disabled) {
      document.querySelectorAll("button").forEach(button => button.disabled = disabled);
    }

    function showDevices(devices) {
      list.innerHTML = "";
      devices.forEach(device => {
        const item = document.createElement("article");
        item.className = "device";
        const icon = device.name.includes("Router") ? "R" : "N";
        item.innerHTML = `
          <div class="icon">${icon}</div>
          <div>
            <h3>${device.name}</h3>
            <p class="muted">IP ${device.ip} | ${device.type} | open ports: ${device.open_ports.join(", ")}</p>
          </div>
          <span class="badge">ONLINE</span>
        `;
        list.appendChild(item);
      });
    }

    async function scan(mode) {
      setButtons(true);
      panel.classList.add("scanning");
      systemStatus.textContent = "SCANNING NETWORK";
      list.innerHTML = "";
      message.textContent = mode === "deep"
        ? "Full scan is running. The ESP32 is checking the whole local range."
        : "Quick sweep is running. The ESP32 is checking the most common addresses.";

      try {
        const response = await fetch(`/scan?mode=${mode}`);
        const data = await response.json();
        ownIp.textContent = data.own_ip;
        gateway.textContent = data.gateway;
        count.textContent = data.count;
        time.textContent = Math.round(data.elapsed_ms / 1000) + "s";
        ports.textContent = "Ports: " + data.ports.join(", ");

        if (data.devices.length) {
          message.textContent = "Scan complete. Active network nodes are shown below.";
          showDevices(data.devices);
        } else {
          message.textContent = "Scan complete. No devices answered on the checked service ports.";
        }
        systemStatus.textContent = "SCAN COMPLETE";
      } catch (error) {
        message.textContent = "Scan failed: " + error.message;
        systemStatus.textContent = "SCAN ERROR";
      } finally {
        panel.classList.remove("scanning");
        setButtons(false);
      }
    }
  </script>
</body>
</html>"""


def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to Wi-Fi:", config.WIFI_SSID)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        started = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), started) > 20000:
                raise RuntimeError("Wi-Fi connection timeout")
            time.sleep_ms(250)
    print("Wi-Fi connected:", wlan.ifconfig())
    return wlan


def send(client, status, body, content_type):
    if isinstance(body, str):
        body = body.encode("utf-8")
    client.send(("HTTP/1.1 " + status + "\r\n").encode())
    client.send(("Content-Type: " + content_type + "\r\n").encode())
    client.send(("Content-Length: " + str(len(body)) + "\r\n").encode())
    client.send(b"Connection: close\r\n\r\n")
    client.send(body)


def get_path(request):
    try:
        first_line = request.decode().split("\r\n", 1)[0]
        return first_line.split(" ")[1]
    except Exception:
        return "/"


def ip_parts(ip):
    return [int(part) for part in ip.split(".")]


def device_type(open_ports):
    if 80 in open_ports or 443 in open_ports:
        return "Web device"
    if 22 in open_ports:
        return "SSH device"
    if 23 in open_ports:
        return "Telnet device"
    if 8080 in open_ports:
        return "Web device"
    return "Unknown"


def probe(ip, port):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(config.SCAN_TIMEOUT_MS / 1000)
        sock.connect((ip, port))
        return True
    except OSError:
        return False
    finally:
        if sock:
            sock.close()


def hosts_for_scan(wlan, mode):
    own_ip, mask, gateway, dns = wlan.ifconfig()
    base = ".".join(own_ip.split(".")[:3])
    own_last = ip_parts(own_ip)[3]

    if mode == "deep":
        last_numbers = range(1, 255)
    else:
        common = set((1, 2, 3, 4, 5, 10, 20, 30, 50, 100, 101, 102, 103, 104, 105, 150, 200, 240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253, 254))
        for last in range(max(1, own_last - 8), min(254, own_last + 8) + 1):
            common.add(last)
        last_numbers = sorted(common)

    hosts = []
    for host in (gateway, dns):
        if host and host != own_ip and host not in hosts:
            hosts.append(host)
    for last in last_numbers:
        host = base + "." + str(last)
        if host != own_ip and host not in hosts:
            hosts.append(host)
    return hosts


def scan_network(wlan, mode):
    own_ip, mask, gateway, dns = wlan.ifconfig()
    started = time.ticks_ms()
    devices = []

    for ip in hosts_for_scan(wlan, mode):
        open_ports = []
        for port in config.SCAN_PORTS:
            if probe(ip, port):
                open_ports.append(port)
        if open_ports:
            name = "Unknown device"
            if ip == gateway:
                name = "Router / Gateway"
            devices.append({
                "ip": ip,
                "name": name,
                "type": device_type(open_ports),
                "open_ports": open_ports,
            })

    return {
        "own_ip": own_ip,
        "gateway": gateway,
        "ports": list(config.SCAN_PORTS),
        "count": len(devices),
        "elapsed_ms": time.ticks_diff(time.ticks_ms(), started),
        "devices": devices,
    }


def start_server(wlan):
    address = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
    server = socket.socket()
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(address)
    server.listen(1)
    print("Open in browser: http://" + wlan.ifconfig()[0])

    while True:
        client, address = server.accept()
        try:
            request = client.recv(1024)
            path = get_path(request)
            if path == "/":
                send(client, "200 OK", HTML, "text/html; charset=utf-8")
            elif path.startswith("/scan"):
                mode = "deep" if "mode=deep" in path else "fast"
                data = scan_network(wlan, mode)
                send(client, "200 OK", json.dumps(data), "application/json; charset=utf-8")
            else:
                send(client, "404 Not Found", "Not found", "text/plain; charset=utf-8")
        except Exception as error:
            send(client, "500 Internal Server Error", "Error: " + str(error), "text/plain; charset=utf-8")
        finally:
            client.close()


wlan = connect_wifi()
start_server(wlan)
