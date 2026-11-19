"""Minimaler OPC-UA-Binary-Client (ohne Zusatzbibliothek).

Einziger Zweck: das vom OPC-UA-Server ausgelieferte Server-Zertifikat lesen
(Hello -> OpenSecureChannel mit SecurityPolicy None -> GetEndpoints), um vor einem
Zertifikats-Upload zu prüfen, ob dasselbe Zertifikat bereits aktiv ist.
Am AL1590 (FW 1.7.0.2) verifiziert am 2026-11-19.
"""
import socket
import struct
import time

POLICY_NONE = "http://opcfoundation.org/UA/SecurityPolicy#None"


def _ua_string(value):
    if value is None:
        return struct.pack("<i", -1)
    data = value.encode("utf-8")
    return struct.pack("<i", len(data)) + data


def _request_header(handle):
    timestamp = int((time.time() + 11644473600) * 10_000_000)
    # AuthToken (TwoByte NodeId 0), Timestamp, RequestHandle, ReturnDiagnostics, AuditEntryId(null), TimeoutHint, AdditionalHeader
    return b"\x00\x00" + struct.pack("<qIIiI", timestamp, handle, 0, -1, 10000) + b"\x00\x00\x00"


class _Buf:
    def __init__(self, data, pos=0):
        self.data, self.pos = data, pos

    def take(self, n):
        chunk = self.data[self.pos:self.pos + n]
        if len(chunk) < n:
            raise ValueError("OPC UA response truncated")
        self.pos += n
        return chunk

    def u32(self):
        return struct.unpack("<I", self.take(4))[0]

    def i32(self):
        return struct.unpack("<i", self.take(4))[0]

    def bytestring(self):
        n = self.i32()
        return None if n < 0 else self.take(n)

    def string(self):
        raw = self.bytestring()
        return None if raw is None else raw.decode("utf-8", "replace")

    def nodeid(self):
        enc = self.take(1)[0]
        sizes = {0: 1, 1: 3, 2: 6}
        if enc not in sizes:
            raise ValueError(f"unsupported NodeId encoding {enc}")
        return self.take(sizes[enc])

    def localized_text(self):
        mask = self.take(1)[0]
        if mask & 1:
            self.string()
        if mask & 2:
            self.string()

    def diagnostic_info(self):
        mask = self.take(1)[0]
        if mask & 0x01: self.i32()
        if mask & 0x02: self.i32()
        if mask & 0x04: self.i32()
        if mask & 0x08: self.i32()
        if mask & 0x10: self.string()
        if mask & 0x20: self.u32()
        if mask & 0x40: self.diagnostic_info()


def _send(sock, msg_type, payload):
    sock.sendall(msg_type + b"F" + struct.pack("<I", len(payload) + 8) + payload)


def _recv(sock):
    head = b""
    while len(head) < 8:
        part = sock.recv(8 - len(head))
        if not part:
            raise ConnectionError("OPC UA connection closed")
        head += part
    size = struct.unpack("<I", head[4:8])[0]
    body = b""
    while len(body) < size - 8:
        part = sock.recv(size - 8 - len(body))
        if not part:
            raise ConnectionError("OPC UA connection closed")
        body += part
    return head[:3], body


def get_server_certificate(host, port, timeout=8):
    """Gibt das DER-Server-Zertifikat des ersten Endpunkts zurück (oder wirft eine Exception)."""
    url = f"opc.tcp://{host}:{port}"
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.settimeout(timeout)
        _send(sock, b"HEL", struct.pack("<IIIII", 0, 65535, 65535, 0, 0) + _ua_string(url))
        msg_type, body = _recv(sock)
        if msg_type != b"ACK":
            raise ConnectionError(f"OPC UA Hello rejected: {msg_type!r}")

        opn = struct.pack("<I", 0) + _ua_string(POLICY_NONE) + struct.pack("<ii", -1, -1) + struct.pack("<II", 1, 1)
        opn += b"\x01\x00" + struct.pack("<H", 446) + _request_header(1)
        opn += struct.pack("<III", 0, 0, 1) + struct.pack("<i", 0) + struct.pack("<I", 3600000)
        _send(sock, b"OPN", opn)
        msg_type, body = _recv(sock)
        if msg_type != b"OPN":
            raise ConnectionError(f"OPC UA OpenSecureChannel rejected: {msg_type!r}")
        buf = _Buf(body)
        channel_id = buf.u32()
        buf.string(); buf.bytestring(); buf.bytestring()      # Policy, SenderCert, ReceiverThumbprint
        buf.u32(); buf.u32()                                  # SequenceNumber, RequestId
        buf.nodeid()                                          # OpenSecureChannelResponse
        buf.take(8); buf.u32(); status = buf.u32()            # Timestamp, RequestHandle, ServiceResult
        if status != 0:
            raise ConnectionError(f"OPC UA OpenSecureChannel status 0x{status:08X}")
        buf.diagnostic_info()
        for _ in range(max(buf.i32(), 0)):
            buf.string()
        buf.nodeid(); buf.take(1)                             # AdditionalHeader
        buf.u32()                                             # ServerProtocolVersion
        buf.u32(); token_id = buf.u32()                       # SecurityToken.ChannelId, TokenId

        msg = struct.pack("<II", channel_id, token_id) + struct.pack("<II", 2, 2)
        msg += b"\x01\x00" + struct.pack("<H", 428) + _request_header(2) + _ua_string(url) + struct.pack("<ii", -1, -1)
        _send(sock, b"MSG", msg)
        msg_type, body = _recv(sock)
        if msg_type != b"MSG":
            raise ConnectionError(f"OPC UA GetEndpoints rejected: {msg_type!r}")

    buf = _Buf(body)
    buf.take(16)                                              # ChannelId, TokenId, Seq, RequestId
    buf.nodeid()                                              # GetEndpointsResponse
    buf.take(8); buf.u32(); status = buf.u32()
    if status != 0:
        raise ConnectionError(f"OPC UA GetEndpoints status 0x{status:08X}")
    buf.diagnostic_info()
    for _ in range(max(buf.i32(), 0)):
        buf.string()
    buf.nodeid(); buf.take(1)
    if buf.i32() < 1:
        raise ValueError("OPC UA server returned no endpoints")
    buf.string()                                              # EndpointUrl
    buf.string(); buf.string(); buf.localized_text(); buf.u32()   # ApplicationUri, ProductUri, Name, Type
    buf.string(); buf.string()                                # GatewayServerUri, DiscoveryProfileUri
    for _ in range(max(buf.i32(), 0)):
        buf.string()                                          # DiscoveryUrls
    certificate = buf.bytestring()
    if not certificate:
        raise ValueError("OPC UA endpoint has no server certificate")
    return certificate
