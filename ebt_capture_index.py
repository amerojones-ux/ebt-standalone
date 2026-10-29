"""Verify references against a caller-supplied immutable capture index.

This verifies integrity and provenance consistency, not source authenticity.
"""
import hashlib
from pathlib import Path
from urllib.parse import urlsplit
from ebt_certification import CertificationHold, timestamp

def verify_capture(capture_id, index, raw_root, *, cutoff, allowed_hosts):
    if not isinstance(capture_id, str) or not capture_id.strip():
        raise CertificationHold("capture ID missing")
    if not isinstance(index, dict) or capture_id not in index:
        raise CertificationHold("capture ID absent from index")
    entry = index[capture_id]
    if not isinstance(entry, dict):
        raise CertificationHold("capture entry invalid")
    digest = entry.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise CertificationHold("invalid SHA-256")
    url = entry.get("url")
    if not isinstance(url, str):
        raise CertificationHold("source URL missing")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.username or parsed.password or parsed.fragment or parsed.port not in (None,443) or parsed.hostname not in allowed_hosts:
        raise CertificationHold("unapproved capture source")
    if timestamp(entry.get("retrieved_at")) > timestamp(cutoff):
        raise CertificationHold("post-cutoff capture")
    relative = entry.get("raw_path")
    if not isinstance(relative, str) or not relative:
        raise CertificationHold("raw capture path missing")
    root = Path(raw_root).resolve(strict=True)
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts:
        raise CertificationHold("capture path traversal")
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root) or not resolved.is_file():
        raise CertificationHold("capture escapes root")
    if hashlib.sha256(resolved.read_bytes()).hexdigest() != digest:
        raise CertificationHold("capture hash mismatch")
    return {"capture_id":capture_id,"host":parsed.hostname,"sha256":digest,"integrity_verified":True,"source_truth_verified":False}

def corroborate_distinct_sources(capture_ids, index, raw_root, *, cutoff, allowed_hosts):
    if not isinstance(capture_ids, list) or len(capture_ids) < 2 or len(set(capture_ids)) != len(capture_ids):
        raise CertificationHold("distinct capture IDs required")
    verified = [verify_capture(cid,index,raw_root,cutoff=cutoff,allowed_hosts=allowed_hosts) for cid in capture_ids]
    if len({v["host"] for v in verified}) < 2:
        raise CertificationHold("distinct source hosts required")
    return {"integrity_verified":True,"independent_truth_certified":False,"capture_count":len(verified)}
