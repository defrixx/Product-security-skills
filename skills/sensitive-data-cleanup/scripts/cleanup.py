#!/usr/bin/env python3
"""Bounded, offline, copy-only cleanup. See references/helper-contract.md.
Python 3.9+, POSIX O_NOFOLLOW/dir_fd support; standard library only.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys

VERSION = '1.2.0'
TEXT = {'.txt', '.md', '.log', '.env', '.ini', '.conf'}
FORMATS = TEXT | {'.json', '.jsonl', '.csv'}
SECRET_FIELDS = {'password', 'passwd', 'api_key', 'access_token', 'refresh_token', 'client_secret', 'private_key', 'secret', 'token'}
PERSON_FIELDS = {'email', 'phone', 'phone_number', 'full_name', 'first_name', 'last_name', 'personal_id',
                 'middle_name', 'date_of_birth', 'birth_date', 'dob', 'home_address',
                 'residential_address', 'passport_number', 'national_id',
                 'social_security_number', 'ssn', 'taxpayer_id', 'driver_license_number',
                 'bank_account', 'iban', 'credit_card_number', 'medical_record_number'}
LIMITS = {'max_file_bytes': 2 * 1024 * 1024, 'max_total_bytes': 64 * 1024 * 1024,
          'max_entries': 10000, 'max_depth': 32, 'max_records': 10000, 'max_findings': 10000,
          'max_output_bytes': 128 * 1024 * 1024}
PEM = re.compile(r'-----BEGIN (?P<kind>(?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY|CERTIFICATE)-----[\s\S]*?-----END (?P=kind)-----')
ASSIGN = re.compile(r'''(?im)\b(?:password|passwd|api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret)\b["']?\s*[:=]\s*(?:["']([^"'\r\n]+)["']|([^\s,;#]+))''')
TOKEN = re.compile(r'\b(?:ghp_[A-Za-z0-9]{20,}|sk-(?:proj-)?[A-Za-z0-9_-]{20,})\b')
EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')
URI = re.compile(r'\b[a-z][a-z0-9+.-]*://([^\s/@]+)@', re.I)
IPV4 = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')
IPV6 = re.compile(r'(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f:.]*(?![\w:])', re.I)
HOST = re.compile(r'\b(?:[a-z0-9-]+\.)+(?:internal|corp|local)\b', re.I)
MARKER = re.compile(r'REDACTED_[A-Z_]+_[0-9]{6}\Z')

class CleanupError(Exception):
    """Only fixed public error codes may be placed in this exception."""


def normalize(key):
    return re.sub(r'[^a-z0-9]', '', key.lower())


def strict_json(text):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj: raise CleanupError('duplicate_json_key')
            obj[key] = value
        return obj
    def invalid(_): raise CleanupError('nonfinite_json_number')
    try: return json.loads(text, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, RecursionError): raise CleanupError('invalid_json') from None


def policy_config(value=None):
    cfg = {'exclude_dirs': ['.git', 'node_modules', '.venv', '__pycache__'],
           'text_extensions': [], 'redact_network': True, 'suppressions': [], 'sensitive_values': []}
    value = {} if value is None else value
    if not isinstance(value, dict) or set(value) - set(cfg): raise CleanupError('invalid_policy')
    cfg.update(value)
    if not isinstance(cfg['redact_network'], bool): raise CleanupError('invalid_policy')
    for key in ('exclude_dirs', 'text_extensions', 'suppressions', 'sensitive_values'):
        if not isinstance(cfg[key], list): raise CleanupError('invalid_policy')
    for name in cfg['exclude_dirs']:
        if not isinstance(name, str) or not name or name in {'.', '..'} or '/' in name or '\\' in name: raise CleanupError('invalid_policy')
    for ext in cfg['text_extensions']:
        if not isinstance(ext, str) or not re.fullmatch(r'\.[a-z0-9]{1,12}', ext) or ext in FORMATS: raise CleanupError('invalid_policy')
    for val in cfg['sensitive_values']:
        if not isinstance(val, str) or len(val) < 4 or MARKER.fullmatch(val): raise CleanupError('invalid_policy')
    seen = set()
    for item in cfg['suppressions']:
        if not isinstance(item, dict) or set(item) != {'file', 'pointer', 'expected_value', 'reason'}: raise CleanupError('invalid_policy')
        if any(not isinstance(v, str) for v in item.values()): raise CleanupError('invalid_policy')
        path = Path(item['file'])
        if path.is_absolute() or '..' in path.parts or any(c in item['file'] for c in '*?[]\\') or not item['reason']: raise CleanupError('invalid_policy')
        if not item['pointer'].startswith('/') or len(item['expected_value']) > 256: raise CleanupError('invalid_policy')
        key = (item['file'], item['pointer'])
        if key in seen: raise CleanupError('invalid_policy')
        seen.add(key)
    return cfg


class Detector:
    def __init__(self, cfg, max_findings=10000):
        self.cfg = cfg
        self.max_findings = max_findings
        self.mapping = {}  # In-memory only; original values never enter the report.
        self.events = []
        self.used_suppressions = set()

    def event(self, value):
        if len(self.events) >= self.max_findings: raise CleanupError("finding_limit")
        self.events.append(value)

    def marker(self, category, value):
        # Same complete value uses the same marker even in a different semantic context.
        if value not in self.mapping:
            self.mapping[value] = 'REDACTED_%s_%06d' % (category.upper(), len(self.mapping) + 1)
        return self.mapping[value]

    def spans(self, text, field=''):
        found = []
        def add(a, b, category):
            value = text[a:b]
            if value and not MARKER.fullmatch(value): found.append((a, b, category))
        for value in self.cfg['sensitive_values']:
            for m in re.finditer(re.escape(value), text): add(m.start(), m.end(), 'custom')
        if normalize(field) in {normalize(x) for x in SECRET_FIELDS | PERSON_FIELDS} and text:
            add(0, len(text), 'credential' if normalize(field) in {normalize(x) for x in SECRET_FIELDS} else 'personal')
        for m in PEM.finditer(text): add(*m.span(), 'certificate' if m.group('kind') == 'CERTIFICATE' else 'private_key')
        for pattern, category in ((TOKEN, 'credential'), (EMAIL, 'email')):
            for m in pattern.finditer(text): add(*m.span(), category)
        for m in ASSIGN.finditer(text): add(*m.span(1 if m.group(1) is not None else 2), 'credential')
        for m in URI.finditer(text): add(*m.span(1), 'credential')
        if self.cfg['redact_network']:
            for pattern in (IPV4, IPV6):
                for m in pattern.finditer(text):
                    try: ipaddress.ip_address(m.group())
                    except ValueError: continue
                    add(*m.span(), 'address')
            for m in HOST.finditer(text): add(*m.span(), 'hostname')
        # Whole structured fields or PEM blocks take precedence over nested matches.
        accepted = []
        for a, b, cat in sorted(found, key=lambda x: (x[0], -(x[1]-x[0]), x[2])):
            if accepted and a < accepted[-1][1]:
                # Partially overlapping matches must not leave the unredacted tail.
                pa, pb, pc = accepted[-1]
                accepted[-1] = (pa, max(pb, b), pc)
            else: accepted.append((a, b, cat))
        return accepted

    def scrub(self, text, file, location, field='', pointer=None):
        if pointer is not None:
            for i, rule in enumerate(self.cfg['suppressions']):
                if rule['file'] == file and rule['pointer'] == pointer:
                    self.used_suppressions.add(i)
                    if text != rule['expected_value']: raise CleanupError('suppression_value_changed')
                    self.event({'location': location, 'category': 'reviewed_field', 'action': 'suppressed', 'reason': 'exact_policy_match'})
                    return text
        out = []; end = 0
        for a, b, category in self.spans(text, field):
            replacement = self.marker(category, text[a:b])
            event = {'location': location, 'category': category, 'action': 'replace', 'replacement': replacement}
            if location == 'text': event['line'] = text[:a].count('\n') + 1
            self.event(event)
            out.extend([text[end:a], replacement]); end = b
        out.append(text[end:])
        return ''.join(out)


def transform(text, suffix, file, detector, max_records=10000, depth_limit=32):
    scalar = [0]
    def walk(value, pointer='', field='', depth=0):
        if depth > depth_limit: raise CleanupError('structure_depth_limit')
        scalar[0] += 1
        if scalar[0] > max_records: raise CleanupError('record_limit')
        location = 'node:%d' % scalar[0]  # JSON pointers can themselves disclose values.
        if value is not None and not isinstance(value, str) and normalize(field) in {normalize(x) for x in SECRET_FIELDS | PERSON_FIELDS}:
            raise CleanupError('sensitive_nonstring_field')
        if isinstance(value, str): return detector.scrub(value, file, location, field, pointer)
        if isinstance(value, list): return [walk(v, pointer+'/'+str(i), '', depth+1) for i,v in enumerate(value)]
        if isinstance(value, dict):
            result = {}
            for key, v in value.items():
                safe = detector.scrub(key, file, location+':key')
                if safe in result: raise CleanupError('sanitized_key_collision')
                next_pointer = pointer+'/'+key.replace('~','~0').replace('/','~1')
                result[safe] = walk(v, next_pointer, key, depth+1)
            return result
        return value
    if suffix == '.json':
        result = json.dumps(walk(strict_json(text)), ensure_ascii=True, indent=2, allow_nan=False)+'\n'
        strict_json(result)
        return result
    if suffix == '.jsonl':
        lines = text.splitlines()
        if len(lines) > max_records: raise CleanupError('record_limit')
        return ''.join(json.dumps(walk(strict_json(line), '/'+str(i)), ensure_ascii=True, allow_nan=False)+'\n' for i,line in enumerate(lines) if line.strip())
    if suffix == '.csv':
        try:
            rows = list(csv.reader(io.StringIO(text, newline=''), strict=True))
        except csv.Error: raise CleanupError('invalid_csv') from None
        if not rows: return ''
        if len(rows)>max_records or len(rows[0])>max_records: raise CleanupError('record_limit')
        if len(set(rows[0])) != len(rows[0]) or any(len(row)!=len(rows[0]) for row in rows): raise CleanupError('invalid_csv_shape')
        output=io.StringIO(newline=''); writer=csv.writer(output)
        writer.writerow([detector.scrub(h,file,'header:%d'%i) for i,h in enumerate(rows[0])])
        for rownum,row in enumerate(rows[1:],1):
            writer.writerow([detector.scrub(v,file,'row:%d:column:%d'%(rownum,i),rows[0][i]) for i,v in enumerate(row)])
        return output.getvalue()
    return detector.scrub(text, file, 'text')


def strip_image_metadata(data, suffix):
    """Lossless container rewrite; no decoding, OCR, or pixel redaction.
    Return bytes and a count of removed/replaced metadata containers.
    Reject unsupported structures rather than passing through unknown content.
    """
    import struct
    import zlib
    removed = 0
    if suffix == '.png':
        if not data.startswith(b'\x89PNG\r\n\x1a\n'): raise CleanupError('image_signature_mismatch')
        output = bytearray(data[:8]); pos = 8; seen = set(); chunks = 0; idat_ended = False
        while pos < len(data):
            chunks += 1
            if chunks > 10000: raise CleanupError('image_container_limit')
            if pos + 12 > len(data): raise CleanupError('invalid_image_structure')
            size = int.from_bytes(data[pos:pos+4], 'big'); kind = data[pos+4:pos+8]
            end = pos + 12 + size
            if end > len(data) or not re.fullmatch(b'[A-Za-z]{4}', kind): raise CleanupError('invalid_image_structure')
            payload = data[pos+8:end-4]
            if zlib.crc32(kind + payload) & 0xffffffff != int.from_bytes(data[end-4:end], 'big'): raise CleanupError('image_crc_error')
            if not seen and kind != b'IHDR': raise CleanupError('invalid_image_structure')
            if kind in {b'acTL', b'fcTL', b'fdAT'}: raise CleanupError('animated_image_unsupported')
            if kind == b'IHDR':
                if seen or size != 13: raise CleanupError('invalid_image_structure')
                width, height, bits, color, compression, filtering, interlace = struct.unpack('>IIBBBBB', payload)
                if not width or not height or width*height > 40000000: raise CleanupError('image_pixel_limit')
                allowed = {0:{1,2,4,8,16},2:{8,16},3:{1,2,4,8},4:{8,16},6:{8,16}}
                if bits not in allowed.get(color,set()) or compression or filtering or interlace not in {0,1}: raise CleanupError('invalid_image_structure')
            if kind in {b'PLTE', b'tRNS'}:
                if kind in seen or b'IDAT' in seen: raise CleanupError('invalid_image_structure')
                if kind == b'PLTE' and (not size or size%3 or size>768 or color in {0,4}): raise CleanupError('invalid_image_structure')
                if kind == b'tRNS' and (color not in {0,2,3} or (color==0 and size!=2) or (color==2 and size!=6) or (color==3 and (b'PLTE' not in seen or not size or size>palette_size))): raise CleanupError('invalid_image_structure')
                if kind == b'PLTE': palette_size=size//3
            if kind == b'IDAT':
                if idat_ended or (color==3 and b'PLTE' not in seen): raise CleanupError('invalid_image_structure')
            elif b'IDAT' in seen: idat_ended=True
            if kind in {b'IHDR', b'PLTE', b'IDAT', b'IEND', b'tRNS'}:
                output.extend(data[pos:end])
            elif kind[0] & 32:
                removed += 1
            else: raise CleanupError('unknown_critical_image_chunk')
            seen.add(kind); pos=end
            if kind == b'IEND':
                if size or b'IDAT' not in seen: raise CleanupError('invalid_image_structure')
                if pos < len(data): removed += 1  # Remove unparsed trailing payload, never copy it.
                return bytes(output), removed
        raise CleanupError('invalid_image_structure')
    if suffix not in {'.jpg','.jpeg'} or not data.startswith(b'\xff\xd8'): raise CleanupError('image_signature_mismatch')
    output=bytearray(data[:2]); pos=2; frame=False; scan=False
    while pos<len(data):
        start=pos
        if data[pos]!=255: raise CleanupError('invalid_image_structure')
        while pos<len(data) and data[pos]==255: pos+=1
        if pos>=len(data): raise CleanupError('invalid_image_structure')
        marker=data[pos];pos+=1
        if marker==0xd9:
            if not frame or not scan: raise CleanupError('invalid_image_structure')
            output.extend(b'\xff\xd9')
            if pos<len(data): removed+=1
            return bytes(output),removed
        if marker in {0,0xd8,1} or 0xd0<=marker<=0xd7: raise CleanupError('invalid_image_structure')
        if pos+2>len(data): raise CleanupError('invalid_image_structure')
        length=int.from_bytes(data[pos:pos+2],'big');end=pos+length
        if length<2 or end>len(data): raise CleanupError('invalid_image_structure')
        payload=data[pos+2:end]
        if marker in {0xc0,0xc2}:
            if frame or len(payload)<6: raise CleanupError('unsupported_jpeg_frame')
            height=int.from_bytes(payload[1:3],'big');width=int.from_bytes(payload[3:5],'big');components=payload[5]
            if payload[0]!=8 or components not in {1,3,4} or len(payload)!=6+3*components: raise CleanupError('unsupported_jpeg_frame')
            if not width or not height or width*height>40000000: raise CleanupError('image_pixel_limit')
            frame=True
        elif marker not in {0xc4,0xdb,0xdd,0xda,0xfe} and not 0xe0<=marker<=0xef: raise CleanupError('unsupported_jpeg_marker')
        if marker==0xee:
            if len(payload)!=12 or payload[:5]!=b'Adobe' or payload[11] not in {0,1,2}: raise CleanupError('unsupported_adobe_marker')
            # Preserve the color transform, discard arbitrary version/flags metadata.
            canonical=b'Adobe\x00\x64\x00\x00\x00\x00'+payload[11:12]
            output.extend(b'\xff\xee\x00\x0e'+canonical)
            if canonical!=payload: removed+=1
        elif marker==0xfe or 0xe0<=marker<=0xef: removed+=1
        else: output.extend(data[start:end])
        pos=end
        if marker==0xda:
            if not frame or len(payload)<4 or len(payload)!=4+2*payload[0]: raise CleanupError('invalid_image_structure')
            scan=True;start=pos
            while pos<len(data):
                if data[pos]!=255: pos+=1;continue
                markpos=pos
                while pos<len(data) and data[pos]==255: pos+=1
                if pos>=len(data): raise CleanupError('invalid_image_structure')
                if data[pos]==0 or 0xd0<=data[pos]<=0xd7: pos+=1;continue
                output.extend(data[start:markpos]);pos=markpos;break
            else: raise CleanupError('invalid_image_structure')
    raise CleanupError('invalid_image_structure')


def identity(st): return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def read_regular(directory, name, limit):
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode): raise CleanupError('nonregular')
        if before.st_nlink != 1: raise CleanupError('hardlink')
        if before.st_size > limit: raise CleanupError('file_size_limit')
        with os.fdopen(os.dup(fd), 'rb') as stream: data=stream.read(limit+1)
        if len(data)>limit: raise CleanupError('file_size_limit')
        if identity(before)!=identity(os.fstat(fd)): raise CleanupError('source_changed')
        return data, identity(before)
    finally: os.close(fd)


def private_write(directory, name, content):
    fd=os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=directory)
    try:
        with os.fdopen(os.dup(fd),'wb') as stream: stream.write(content); stream.flush()
    finally: os.close(fd)


def run(source, output, mode='scan-only', policy=None, limits=None, image_metadata_only=False):
    if os.name!='posix' or not hasattr(os,'O_NOFOLLOW'): raise CleanupError('unsupported_platform')
    if mode not in {'scan-only','clean-copy'}: raise CleanupError('invalid_mode')
    cfg=policy_config(policy); bounds=dict(LIMITS)
    if limits:
        if set(limits)-set(bounds): raise CleanupError('invalid_limits')
        bounds.update(limits)
    if any(type(v) is not int or v<1 for v in bounds.values()): raise CleanupError('invalid_limits')
    source=Path(source);output=Path(output)
    if source.is_symlink() or output.is_symlink(): raise CleanupError('symlink_root')
    source=source.resolve(strict=True)
    parent=output.parent.resolve(strict=True); output=parent/output.name
    if source==output or source in output.parents or output in source.parents: raise CleanupError('overlapping_roots')
    if output.exists(): raise CleanupError('destination_exists')
    rootfd=os.open(source,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        parentfd=os.open(parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    except OSError:
        os.close(rootfd)
        raise
    outfd=None; filesfd=None
    report={'schema_version':1,'helper_version':VERSION,'mode':mode,'status':'running',
            'limitations':['bounded_detectors_not_complete_pii_detection','opaque_paths_break_references',
                          'no_archive_binary_metadata_or_history_coverage','syntax_not_runtime_validation',
                          'quiet_source_and_trusted_output_parent_required'],
            'limits':bounds,'files':[],'excluded_trees':[],'issues':[]}
    detector=Detector(cfg,bounds['max_findings']); pending=[]; entries=[0]; total=[0]; output_bytes=[0]
    def visit(dirfd, prefix='', depth=0):
        if depth>bounds['max_depth']:
            report['excluded_trees'].append({'id':'X%06d'%(len(report['excluded_trees'])+1),'reason':'directory_depth_limit'});return
        names=[]
        try:
            with os.scandir(dirfd) as listing:
                for entry in listing:
                    entries[0]+=1
                    if entries[0]>bounds['max_entries']:
                        if 'entry_limit' not in report['issues']: report['issues'].append('entry_limit')
                        return  # Do not process an arbitrary filesystem-order prefix.
                    names.append(entry.name)
        except OSError:
            report['issues'].append('directory_read_error');return
        for name in sorted(names):
            rel=prefix+name
            try: st=os.stat(name,dir_fd=dirfd,follow_symlinks=False)
            except OSError:
                report['files'].append({'id':'F%06d'%(len(report['files'])+1),'status':'failed','reason':'stat_error'});continue
            if stat.S_ISDIR(st.st_mode):
                if name in cfg['exclude_dirs']:
                    report['excluded_trees'].append({'id':'X%06d'%(len(report['excluded_trees'])+1),'reason':'policy_directory_exclusion'});continue
                if entries[0]>bounds['max_entries']: continue
                try:
                    child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=dirfd)
                    try: visit(child,rel+'/',depth+1)
                    finally: os.close(child)
                except OSError: report['issues'].append('directory_changed_or_unreadable')
                continue
            item={'id':'F%06d'%(len(report['files'])+1),'status':'skipped'};report['files'].append(item)
            if not stat.S_ISREG(st.st_mode): item['reason']='symlink_or_nonregular';continue
            suffix=Path(name).suffix.lower()
            if name=='.env': suffix='.env'
            if (image_metadata_only and suffix not in {'.jpg','.jpeg','.png'}) or (not image_metadata_only and suffix not in FORMATS and suffix not in cfg['text_extensions']): item['reason']='unsupported_format';continue
            start=len(detector.events)
            try:
                if st.st_size > bounds['max_total_bytes']-total[0]: raise CleanupError('total_byte_limit')
                data, stamp=read_regular(dirfd,name,min(bounds['max_file_bytes'],bounds['max_total_bytes']-total[0]))
                total[0]+=len(data)
                if total[0]>bounds['max_total_bytes']: raise CleanupError('total_byte_limit')
                if image_metadata_only:
                    content, removed = strip_image_metadata(data,suffix)
                    checked, residual = strip_image_metadata(content,suffix)
                    if checked != content or residual: raise CleanupError('image_metadata_residual')
                    item.update(status='checked',format=suffix,metadata_containers_removed=removed,
                                verification='container_reparse_no_pixel_decode',changed=content!=data,
                                coverage='metadata_only_pixels_and_steganography_not_checked')
                else:
                    text=data.decode('utf-8-sig')
                    if '\x00' in text: raise CleanupError('binary_content')
                    without_pem=PEM.sub('',text)
                    if re.search(r'-----[A-Z ]*(?:PRIVATE KEY|CERTIFICATE)-----',without_pem): raise CleanupError('incomplete_pem_block')
                    # Markers already in inputs can collide with generated IDs. Omit, do not silently merge entities.
                    if re.search(r'REDACTED_[A-Z_]+_[0-9]{6}',text): raise CleanupError('reserved_marker_in_input')
                    cleaned=transform(text,suffix,rel,detector,bounds['max_records'],bounds['max_depth'])
                    local_events=detector.events[start:]
                    # Rescan using the same policy; exact suppressions remain visible, not treated as clean by omission.
                    checker=Detector(cfg,bounds['max_findings'])
                    transform(cleaned,suffix,rel,checker,bounds['max_records'],bounds['max_depth'])
                    if any(e['action']=='replace' for e in checker.events): raise CleanupError('residual_detector_match')
                    item.update(status='checked',format=suffix,events=local_events,residual_matches=0,
                                verification='same_detector_rescan',changed=any(e['action']=='replace' for e in local_events))
                    content=cleaned.encode('utf-8')
                recheck,after=read_regular(dirfd,name,bounds['max_file_bytes'])
                if stamp!=after or data!=recheck: raise CleanupError('source_changed')
                if mode=='clean-copy':
                    if output_bytes[0]+len(content)>bounds['max_output_bytes']: raise CleanupError('output_byte_limit')
                    output_bytes[0]+=len(content)
                    filename=item['id']+suffix;item['output']='files/'+filename
                    pending.append((filename,content))
            except CleanupError as exc:
                item.update(status='skipped' if str(exc) in {'hardlink','file_size_limit','total_byte_limit','binary_content','reserved_marker_in_input'} else 'failed',reason=str(exc))
                item.pop('events',None);item.pop('output',None);item.pop('changed',None)
                del detector.events[start:]
            except (UnicodeError, OSError, ValueError, RecursionError):
                item.update(status='failed',reason='read_parse_or_encoding_error');item.pop('events',None);item.pop('output',None);item.pop('changed',None);del detector.events[start:]
    try:
        # Create the private run directory before work; a fatal interruption never leaves a success report.
        os.mkdir(output.name,0o700,dir_fd=parentfd)
        outfd=os.open(output.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parentfd)
        private_write(outfd,'RUNNING',b'Incomplete until report.json exists and RUNNING is absent.\n')
        visit(rootfd)
        if len(detector.used_suppressions)!=len(cfg['suppressions']): report['issues'].append('unused_suppression')
        if mode=='clean-copy':
            os.mkdir('files',0o700,dir_fd=outfd);filesfd=os.open('files',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=outfd)
            for name,content in pending: private_write(filesfd,name,content)
        counts={key:sum(f['status']==key for f in report['files']) for key in ('checked','skipped','failed')}
        events=[e for f in report['files'] for e in f.get('events',[])]
        report['counts']={**counts,'inventoried_files':len(report['files']),'excluded_trees':len(report['excluded_trees']),
                          'emitted_files':len(pending),'changed_files':sum(f.get('changed',False) for f in report['files']),
                          'replacement_occurrences':sum(e['action']=='replace' for e in events),
                          'suppressed_occurrences':sum(e['action']=='suppressed' for e in events)}
        if mode=='scan-only':
            for event in events:
                if event['action']=='replace': event['action']='proposed'
            report['counts']['proposed_occurrences']=report['counts'].pop('replacement_occurrences')
            report['counts']['replacement_occurrences']=0
        report['status']='partial' if counts['skipped'] or counts['failed'] or report['issues'] or report['excluded_trees'] else 'completed_within_declared_coverage'
        if image_metadata_only:
            report['scope']='jpeg_png_metadata_only'
            report['limitations']=['no_pixel_ocr_or_steganography_redaction','color_profiles_and_orientation_removed_display_may_change','container_validation_not_full_decode','other_formats_omitted','quiet_source_and_trusted_output_parent_required']
            count=sum(f.get('metadata_containers_removed',0) for f in report['files'] if f['status']=='checked')
            report['counts']['metadata_containers_removed']=count if mode=='clean-copy' else 0
            report['counts']['metadata_containers_proposed']=count if mode=='scan-only' else 0
            if mode=='scan-only':
                for item in report['files']:
                    if 'metadata_containers_removed' in item:
                        item['metadata_containers_proposed']=item.pop('metadata_containers_removed')
        report['source_preservation']='opened_read_only; byte_comparison_immediately_after_each_processed_file; no_global_snapshot_claim'
        report['helper_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        private_write(outfd,'report.json',(json.dumps(report,indent=2,sort_keys=True)+'\n').encode())
        os.unlink('RUNNING',dir_fd=outfd)
        return report
    finally:
        for fd in (filesfd,outfd,parentfd,rootfd):
            if fd is not None: os.close(fd)


class SafeParser(argparse.ArgumentParser):
    def error(self,message): raise CleanupError('invalid_arguments')


def main(argv=None):
    try:
        parser=SafeParser(description=__doc__)
        parser.add_argument('--source',required=True);parser.add_argument('--output',required=True)
        parser.add_argument('--mode',choices=['scan-only','clean-copy'],default='scan-only')
        parser.add_argument('--image-metadata-only',action='store_true',help='Process only JPEG/PNG metadata; omit all other formats.')
        parser.add_argument('--policy',help='Local JSON policy; never included in the report.')
        for key in LIMITS:
            parser.add_argument('--'+key.replace('_','-'),type=int,default=None)
        args=parser.parse_args(argv)
        policy=strict_json(Path(args.policy).read_text()) if args.policy else None
        bounds={key:getattr(args,key) for key in LIMITS if getattr(args,key) is not None}
        result=run(args.source,args.output,args.mode,policy,bounds,args.image_metadata_only)
        print(json.dumps({'status':result['status'],'counts':result['counts']}))
        return 2 if result['status']=='partial' else 0
    except CleanupError as exc:
        print(json.dumps({'status':'failed','code':str(exc)}),file=sys.stderr);return 1
    except Exception:
        print('{"status":"failed","code":"operation_failed"}',file=sys.stderr);return 1

if __name__=='__main__': sys.exit(main())
