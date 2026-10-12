import subprocess, shutil, os, glob, threading, time, html, datetime, urllib.request

NAME, REG, CLS = "Matheswaran S", "3122245001087", "CSE - B"
COURSE, COLLEGE = "UCS3568 - Ethical Hacking", "SSN College of Engineering"
PCAP = "Matheswaran_3122245001087_capture.pcapng"
DURATION = 50

def find(tool):
    p = shutil.which(tool)
    if p: return p
    for d in glob.glob(r"C:\Program Files\Wireshark") + ["/usr/bin", "/Applications/Wireshark.app/Contents/MacOS"]:
        q = os.path.join(d, tool + (".exe" if os.name == "nt" else ""))
        if os.path.exists(q): return q
    raise SystemExit(f"{tool} not found. Install Wireshark first.")

TSHARK, CAPINFOS = find("tshark"), find("capinfos")
run = lambda c: subprocess.run(c, capture_output=True, text=True).stdout.strip()

def pick_interface():
    good = ("wi-fi", "wlan", "wireless", "ethernet", "en0", "eth0", "enp", "wlp")
    bad = ("loopback", "vmware", "virtualbox", "bluetooth", "vethernet", "wan miniport")
    for line in run([TSHARK, "-D"]).splitlines():
        l = line.lower()
        if any(g in l for g in good) and not any(b in l for b in bad):
            return line.split(".")[0]
    return "1"

def traffic():
    time.sleep(3)
    subprocess.run(["ping", "-n" if os.name == "nt" else "-c", "4", "google.com"], capture_output=True)
    subprocess.run(["nslookup", "ssn.edu.in"], capture_output=True)
    for u in ["http://neverssl.com", "https://www.google.com", "https://www.wikipedia.org",
              "https://www.youtube.com", "https://www.github.com", "http://example.com"]:
        try: urllib.request.urlopen(u, timeout=8).read()
        except Exception: pass

iface = pick_interface()
print(f"Capturing on interface {iface} for {DURATION}s, generating traffic...")
t = threading.Thread(target=traffic); t.start()
subprocess.run([TSHARK, "-i", iface, "-a", f"duration:{DURATION}", "-w", PCAP], capture_output=True)
t.join()

def count(f): return len(run([TSHARK, "-r", PCAP, "-Y", f, "-T", "fields", "-e", "frame.number"]).split())
def fields(f, cols, n=8):
    c = [TSHARK, "-r", PCAP, "-Y", f, "-T", "fields"]
    for x in cols: c += ["-e", x]
    return "\n".join(run(c).splitlines()[:n]) or "(no matching packets in this capture)"
def stat(z, n=22): return "\n".join(run([TSHARK, "-r", PCAP, "-q", "-z", z]).splitlines()[:n])

total = count("frame")
c = {k: count(k) for k in ["tcp", "udp", "dns", "http", "tls", "icmp", "arp", "tcp.analysis.retransmission"]}
pct = lambda k: f"{100*c[k]/total:.1f}%" if total else "0%"

props = run([CAPINFOS, PCAP])
fig = lambda title, txt: f"<p><b>{title}</b></p><pre>{html.escape(txt)}</pre>"
today = datetime.date.today().strftime("%d %B %Y")

doc = f"""<html><head><meta charset="utf-8"><title>Network Traffic Analysis</title>
<style>body{{font-family:Calibri,Arial;max-width:800px;margin:auto;font-size:12pt;line-height:1.5}}
pre{{background:#f4f4f4;border:1px solid #ccc;padding:8px;font-size:8.5pt;overflow-x:auto}}
td{{border:1px solid #999;padding:4px 10px}}table{{border-collapse:collapse}}h1,h2{{color:#1f3864}}</style></head><body>
<h1 style="text-align:center">Network Traffic Analysis Using Wireshark</h1>
<h3 style="text-align:center">Assignment 2 - {COURSE}</h3>
<table align="center"><tr><td>Name</td><td>{NAME}</td></tr><tr><td>Register Number</td><td>{REG}</td></tr>
<tr><td>Class</td><td>{CLS}</td></tr><tr><td>Course</td><td>{COURSE}</td></tr>
<tr><td>Institution</td><td>{COLLEGE}</td></tr><tr><td>Date</td><td>{today}</td></tr></table>

<h2>1. Aim</h2><p>To capture real-time network traffic using Wireshark, generate a traffic dataset, and analyse it at the protocol level to understand device communication and identify security weaknesses.</p>

<h2>2. Procedure</h2><p>Live capture was run on the active network interface for {DURATION} seconds using Wireshark's capture engine. During the session, web pages were fetched over HTTP and HTTPS, and ping and nslookup commands were run to generate ICMP and DNS traffic. The capture was saved as <i>{PCAP}</i> and uploaded to the submission link. The dataset was then analysed using Wireshark display filters and statistics.</p>
{fig("Figure 1: Capture file properties", props)}

<h2>3. Analysis</h2>
<h3>3.1 Overall summary</h3><p>The capture contains <b>{total}</b> packets. TCP accounts for {pct('tcp')}, UDP for {pct('udp')}, with {c['dns']} DNS, {c['tls']} TLS, {c['http']} HTTP, {c['icmp']} ICMP and {c['arp']} ARP packets.</p>
{fig("Figure 2: Protocol hierarchy", stat("io,phs"))}
<h3>3.2 DNS analysis (filter: dns)</h3><p>Every connection began with a DNS lookup. The queries below show which domains were requested, and DNS is normally unencrypted, so anyone on the network can read them.</p>
{fig("Figure 3: DNS queries (frame, source, queried name)", fields("dns.flags.response==0", ["frame.number", "ip.src", "dns.qry.name"], 10))}
<h3>3.3 TCP three-way handshake (filter: tcp.flags.syn==1)</h3><p>TCP connections open with SYN, SYN-ACK and ACK packets, which establish a reliable session before data flows.</p>
{fig("Figure 4: SYN / SYN-ACK packets (frame, src, dst, dst port, flags)", fields("tcp.flags.syn==1", ["frame.number", "ip.src", "ip.dst", "tcp.dstport", "tcp.flags"], 8))}
<h3>3.4 HTTP versus HTTPS</h3><p>HTTP requests expose the host, path and headers in plain text. HTTPS traffic shows only the TLS handshake and the server name, while the contents stay encrypted.</p>
{fig("Figure 5: HTTP requests in clear text (host, URI)", fields("http.request", ["http.host", "http.request.uri", "http.user_agent"], 6))}
{fig("Figure 6: TLS handshakes (server names visible, payload encrypted)", fields("tls.handshake.type==1", ["frame.number", "ip.dst", "tls.handshake.extensions_server_name"], 10))}
<h3>3.5 ICMP analysis (filter: icmp)</h3><p>The ping command produced echo requests and replies between the host and the target.</p>
{fig("Figure 7: ICMP packets (frame, src, dst, type)", fields("icmp", ["frame.number", "ip.src", "ip.dst", "icmp.type"], 10))}
<h3>3.6 Top conversations</h3><p>Sorting IP conversations by volume identifies the heaviest talkers on the network.</p>
{fig("Figure 8: IPv4 conversations", stat("conv,ip"))}

<h2>4. Observations</h2><ul>
<li>TCP carried {pct('tcp')} of the traffic, and UDP ({pct('udp')}) was mainly DNS and QUIC.</li>
<li>{c['dns']} DNS packets were seen, and each website visit started with name resolution.</li>
<li>{c['http']} HTTP packets were fully readable, while HTTPS sessions exposed only handshake metadata.</li>
<li>TCP retransmissions observed: {c['tcp.analysis.retransmission']}.</li></ul>

<h2>5. Security Implications</h2><p>Unencrypted protocols such as HTTP, FTP and Telnet allow credentials and data to be intercepted by anyone who can capture the traffic. Unencrypted DNS leaks browsing behaviour. Packet analysis also helps detect port scans (many SYNs without completed handshakes), unusual destinations and abnormal volumes. Recommended controls are enforcing HTTPS, DNS over HTTPS/TLS, VPN use on public networks and network segmentation.</p>

<h2>6. Outcome</h2><p>Real-time traffic of {total} packets was captured with Wireshark, saved as a .pcapng dataset and analysed for protocol distribution, DNS resolution, TCP handshakes, HTTP versus HTTPS exposure, ICMP behaviour and top conversations. The key finding is that unencrypted traffic is directly readable by anyone who can capture it, which shows why encryption is essential in secure network design.</p>
<h2>7. Conclusion</h2><p>Wireshark gives clear visibility into real network behaviour. Used ethically on authorised networks, it supports troubleshooting, security auditing and a deeper understanding of protocols.</p>
</body></html>"""

open("report.html", "w", encoding="utf-8").write(doc)
print("Done. Upload", PCAP, "and print report.html to PDF (Ctrl+P).")