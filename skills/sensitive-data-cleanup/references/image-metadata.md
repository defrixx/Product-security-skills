# JPEG/PNG metadata-only cleanup

Use this opt-in mode only for removing JPEG/PNG metadata. It does not clean documents, PDFs, archives, visible text, faces, QR codes, or steganographic payloads. It does not run OCR or edit pixels. Other files are omitted from the output and reported; originals remain untouched.

```sh
python3 scripts/cleanup.py --source /path/to/images --output /path/to/new-run --mode clean-copy --image-metadata-only
```

Run from the copied skill directory. Omit `--mode clean-copy` for scan-only: no image copy is emitted and removal counts are proposals. The ordinary text-cleanup mode continues to omit images. Standard file/total/output size limits, link exclusions, private output permissions, opaque filenames, fresh-destination checks, and source byte comparisons apply in both modes. The helper needs no image library.

## Exact transformation

- PNG: retain IHDR, PLTE, IDAT, IEND, and tRNS (palette/pixel transparency). Remove all other ancillary chunks, including EXIF, text, compressed text, XMP carried in text, timestamps, density, and color-profile chunks. Preserve retained chunks byte-for-byte, including compressed pixels. Reject animation chunks, unknown critical chunks, CRC errors, and unsupported container structures. Do not silently flatten APNG.
- JPEG: support 8-bit baseline and progressive frames with one, three, or four components. Remove APP metadata segments and comments, including EXIF/GPS, XMP, ICC, IPTC, and thumbnails. Preserve coding tables, frames, scans, and entropy-coded bytes. A recognized Adobe APP14 color transform is retained in a normalized segment; arbitrary flags are discarded. Unknown APP14 layouts and unsupported coding markers are rejected.
- Discard trailing bytes after the image's terminal marker. This is reported as one removed container, without inspecting or publishing its content.
- Pixel dimensions and format/color-transform structures remain because they are needed to interpret the image. This is not a claim that every byte other than pixels is removed.

EXIF orientation and color profiles are removed. A viewer may consequently show a different orientation or color even though encoded pixel data is unchanged. No corrective rotation or re-encoding is performed. Validate suitability for the intended viewer before sharing.

## Verification and reporting

The helper checks signatures, container boundaries, PNG CRCs, selected structural constraints, a 40-million-pixel declared-dimension limit, and a 10,000 PNG chunk limit. It reparses the output and requires an idempotent rewrite with no additional metadata removed. It does not decode entropy/zlib pixel streams and cannot certify that all accepted images are fully decodable or safe for every decoder.

Reports identify opaque file IDs, format, removed/proposed container counts, verification method, omissions, and errors. A count describes containers, not individual tags, people, or confirmed sensitive values; metadata values never appear in reports. A zero count does not establish image anonymity. Output files do not inherit original filenames, filesystem timestamps, permissions, or extended attributes; newly created filesystem metadata still exists.

Synthetic tests cover baseline/progressive/CMYK JPEG, PNG text/EXIF/profile removal, palette transparency, malformed/truncated structures, animation refusal, source preservation, scan-only, copy-only CLI execution, and unchanged other-format originals. Independent Pillow decoding checks compare synthetic image samples before/after; they do not prove every real-world image is supported.

Sources checked 2026-09-24: [W3C PNG third edition](https://www.w3.org/TR/png-3/) (critical/ancillary chunks, tRNS, EXIF, animation) and [ExifTool JPEG tag documentation](https://exiftool.org/TagNames/JPEG.html) / [deletion behavior](https://exiftool.org/exiftool_pod.html) (APP metadata and Adobe color-transform caveat). The helper implements the bounded transformation above, not the full ExifTool feature set.
