"""Unit tests for the pure output parsers."""

from lab_sentinel.core import parsers


def test_parse_os_release():
    name, version = parsers.parse_os_release(
        'NAME="Raspbian GNU/Linux"\nPRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n'
    )
    assert name == "Raspbian GNU/Linux"
    assert "bookworm" in version


def test_parse_uname():
    kernel, arch = parsers.parse_uname("Linux pi 6.6.20+rpt-rpi-v8 #1 SMP aarch64 GNU/Linux")
    assert kernel.startswith("6.6")
    assert arch == "aarch64"


def test_parse_disk_percent():
    assert parsers.parse_disk_percent("/dev/root 15G 12G 2.5G 82% /") == 82


def test_parse_memory_percent():
    assert parsers.parse_memory_percent("Mem:  1000  610  200") == 61


def test_parse_uptime():
    assert "3 days" in parsers.parse_uptime(" 14:02 up 3 days,  4:11,  1 user, load 0.1")


def test_parse_disk_percent_missing_returns_none():
    assert parsers.parse_disk_percent("no percent here") is None


IP_ADDR_OUTPUT = """\
1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500
    link/ether dc:a6:32:aa:bb:cc brd ff:ff:ff:ff:ff:ff
    inet 192.168.1.100/24 brd 192.168.1.255 scope global eth0
    inet6 2001:db8::1/64 scope global
"""

IP_ROUTE_OUTPUT = """\
default via 192.168.1.1 dev eth0 proto dhcp src 192.168.1.100
192.168.1.0/24 dev eth0 proto kernel scope link
"""

SS_OUTPUT = """\
State   Recv-Q Send-Q Local Address:Port Peer Address:Port Process
LISTEN  0      128    0.0.0.0:22        0.0.0.0:*         users:(("sshd",pid=123,fd=3))
LISTEN  0      128    127.0.0.1:631     0.0.0.0:*         users:(("cupsd",pid=456,fd=7))
"""

ARP_OUTPUT = """\
IP address       HW type     Flags       HW address            Mask     Device
192.168.1.1      0x1         0x2         aa:bb:cc:dd:ee:ff     *        eth0
192.168.1.50     0x1         0x0         00:00:00:00:00:00     *        eth0
"""


def test_parse_ip_addr_interfaces():
    ifaces = parsers.parse_ip_addr(IP_ADDR_OUTPUT)
    names = [i.name for i in ifaces]
    assert "eth0" in names
    eth0 = next(i for i in ifaces if i.name == "eth0")
    assert "192.168.1.100/24" in eth0.ipv4
    assert eth0.mac == "dc:a6:32:aa:bb:cc"
    assert eth0.state == "UP"
    assert "2001:db8::1/64" in eth0.ipv6


def test_parse_ip_route_gateway():
    gateway, routes = parsers.parse_ip_route(IP_ROUTE_OUTPUT)
    assert gateway == "192.168.1.1"
    assert len(routes) == 2


def test_parse_ss_services():
    services = parsers.parse_ss(SS_OUTPUT)
    assert any("sshd" in s and "22" in s for s in services)


def test_parse_arp_skips_incomplete():
    neighbors = parsers.parse_arp(ARP_OUTPUT)
    # 192.168.1.50 has flags 0x0 (incomplete) — must be skipped
    assert len(neighbors) == 1
    assert "192.168.1.1" in neighbors[0]


def test_build_network_info_integration():
    info = parsers.build_network_info(
        hostname_i="192.168.1.100",
        ip_addr=IP_ADDR_OUTPUT,
        ip_route=IP_ROUTE_OUTPUT,
        ss_output=SS_OUTPUT,
        arp_output=ARP_OUTPUT,
        iw_output="",
    )
    assert info.default_gateway == "192.168.1.1"
    assert any(i.name == "eth0" for i in info.interfaces)
    assert any("sshd" in s for s in info.listening_services)
    assert len(info.arp_neighbors) == 1
