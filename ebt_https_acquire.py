"""Constrained HTTPS acquisition of allowlisted raw evidence.

This performs actual TLS-verified retrieval. Authorization and source truth
still require external review. Never bypass HTTP access controls.
"""
import hashlib
import json
import ipaddress
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPSHandler, HTTPRedirectHandler
from http.client import HTTPSConnection
from ebt_certification import CertificationHold

def collect_https(url, destination, *, allowed_hosts, collector_version,
                  timeout_seconds=15, max_bytes=2_000_000):
    if not isinstance(url,str):
        raise CertificationHold("URL required")
    try:
        parts=urlsplit(url)
        port=parts.port
    except ValueError as exc:
        raise CertificationHold("malformed URL") from exc
    if not isinstance(allowed_hosts,(set,frozenset)) or not allowed_hosts:
        raise CertificationHold("explicit host allowlist required")
    if parts.scheme!="https" or parts.username or parts.password or parts.fragment or port not in (None,443) or parts.hostname not in allowed_hosts:
        raise CertificationHold("URL not allowlisted")
    if type(max_bytes) is not int or not 0<max_bytes<=10_000_000:
        raise CertificationHold("invalid capture limit")
    if type(timeout_seconds) not in (int,float) or not 0<timeout_seconds<=30:
        raise CertificationHold("invalid timeout")
    if not isinstance(collector_version,str) or not collector_version.strip():
        raise CertificationHold("collector version required")
    # DNS preflight is only a screening measure: urllib resolves again later.
    # A pinned-address transport is required before treating this as SSRF-safe.
    try:
        answers=socket.getaddrinfo(parts.hostname,443,type=socket.SOCK_STREAM)
    except (socket.gaierror,OSError) as exc:
        raise CertificationHold("DNS lookup failed") from exc
    if not answers:
        raise CertificationHold("DNS lookup empty")
    for answer in answers:
        try:
            addr=ipaddress.ip_address(answer[4][0])
        except ValueError as exc:
            raise CertificationHold("invalid resolved address") from exc
        if not addr.is_global:
            raise CertificationHold("nonpublic resolved address prohibited")
    approved_ips={ipaddress.ip_address(answer[4][0]).compressed for answer in answers}
    root=Path(destination).resolve()
    root.mkdir(parents=True,exist_ok=True)
    req=Request(url,headers={"User-Agent":"EBT-BlackDiamond-EvidenceCollector/1.0"})
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, request, fp, code, msg, headers, newurl):
            raise CertificationHold("redirect prohibited")
    class PinnedConnection(HTTPSConnection):
        def connect(self):
            # Preserve TLS hostname verification and SNI, but pin TCP target.
            import socket as _socket
            current=_socket.getaddrinfo(self.host,self.port,type=_socket.SOCK_STREAM)
            for candidate in current:
                if ipaddress.ip_address(candidate[4][0]).compressed not in approved_ips:
                    raise CertificationHold("DNS answer changed before connection")
            address=next(iter(sorted(approved_ips)))
            self.sock=_socket.create_connection((address,self.port),self.timeout,
                                               self.source_address)
            if self._tunnel_host:
                raise CertificationHold("proxy tunneling prohibited")
            self.sock=self._context.wrap_socket(self.sock,server_hostname=self.host)
    class PinnedHTTPSHandler(HTTPSHandler):
        def https_open(self,req):
            return self.do_open(lambda host,**kw: PinnedConnection(
                host,context=ssl.create_default_context(),**kw),req)
    opener=build_opener(NoRedirect(),PinnedHTTPSHandler())
    try:
        # System CA trust; redirects prohibited before any secondary request.
        with opener.open(req,timeout=timeout_seconds) as response:
            final=urlsplit(response.geturl())
            if final.scheme!="https" or final.hostname not in allowed_hosts or final.port not in (None,443) or final.username or final.password:
                raise CertificationHold("redirected outside allowlist")
            if response.status!=200:
                raise CertificationHold("HTTP acquisition failed")
            data=response.read(max_bytes+1)
            if len(data)>max_bytes:
                raise CertificationHold("capture exceeds size limit")
    except (HTTPError,URLError,TimeoutError) as exc:
        raise CertificationHold("HTTPS acquisition failed") from exc
    if not data:
        raise CertificationHold("empty capture")
    digest=hashlib.sha256(data).hexdigest()
    filename=digest+".bin"
    path=root/filename
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
            raise CertificationHold("existing raw capture conflicts")
    else:
        with path.open("xb") as stream:
            stream.write(data)
    now=datetime.now(timezone.utc).isoformat()
    receipt={"sha256":digest,"url":url,"raw_path":filename,
             "retrieved_at":now,"bytes":len(data),
             "acquisition":{"method":"permitted_public_endpoint",
                            "collector_version":collector_version,
                            "request_id":digest,
                            "tls_verified":True,"http_status":200,
                            "completed_at":now}}
    receipt_path=root/(digest+".receipt.json")
    if not receipt_path.exists():
        with receipt_path.open("x",encoding="utf-8") as stream:
            json.dump(receipt,stream,sort_keys=True)
    return {"capture_id":digest,"receipt_path":str(receipt_path),
            "integrity_verified":True,"provider_truth_verified":False,
            "authorization_independently_verified":False,
            "dns_rebinding_protection_verified":True}
