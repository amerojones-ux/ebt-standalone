"""Constrained HTTPS acquisition of allowlisted raw evidence.

This performs actual TLS-verified retrieval. Authorization and source truth
still require external review. Never bypass HTTP access controls.
"""
import hashlib
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from ebt_certification import CertificationHold

def collect_https(url, destination, *, allowed_hosts, collector_version,
                  timeout_seconds=15, max_bytes=2_000_000):
    if not isinstance(url,str):
        raise CertificationHold("URL required")
    parts=urlsplit(url)
    if parts.scheme!="https" or parts.username or parts.password or parts.fragment or parts.port not in (None,443) or parts.hostname not in allowed_hosts:
        raise CertificationHold("URL not allowlisted")
    if type(max_bytes) is not int or not 0<max_bytes<=10_000_000:
        raise CertificationHold("invalid capture limit")
    if type(timeout_seconds) not in (int,float) or not 0<timeout_seconds<=30:
        raise CertificationHold("invalid timeout")
    if not isinstance(collector_version,str) or not collector_version.strip():
        raise CertificationHold("collector version required")
    root=Path(destination).resolve()
    root.mkdir(parents=True,exist_ok=True)
    req=Request(url,headers={"User-Agent":"EBT-BlackDiamond-EvidenceCollector/1.0"})
    try:
        # System CA trust; no disabling certificate validation.
        with urlopen(req,timeout=timeout_seconds,context=ssl.create_default_context()) as response:
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
            "authorization_independently_verified":False}
