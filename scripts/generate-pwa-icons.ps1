# Generate minimal PNG PWA icons from SVG (requires Python + Pillow, or skips gracefully)
param(
  [string]$OutDir = ""
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$Public = Join-Path $Root "frontend\public"
if (-not $OutDir) { $OutDir = $Public }

$py = @"
import struct, zlib, pathlib
out = pathlib.Path(r'$OutDir')

def write_png(path, size, rgb=(0, 212, 255)):
    # Minimal solid PNG with simple circle-like gradient corner mark
    w = h = size
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter None
        for x in range(w):
            cx, cy = w/2, h/2
            d = ((x-cx)**2 + (y-cy)**2) ** 0.5
            r0 = size * 0.42
            if d <= r0:
                t = max(0.0, min(1.0, 1.0 - d/r0))
                r = int(5 + (rgb[0]-5)*t)
                g = int(8 + (rgb[1]-8)*t)
                b = int(22 + (rgb[2]-22)*t)
                raw += bytes((r, g, b, 255))
            else:
                raw += bytes((5, 8, 22, 255))

    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)

    ihdr = struct.pack('>IIBBBBB', w, h, 8, 6, 0, 0, 0)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    path.write_bytes(png)
    print('wrote', path, len(png))

write_png(out / 'pwa-192.png', 192)
write_png(out / 'pwa-512.png', 512)
"@

$tmp = Join-Path $env:TEMP "af_pwa_icons.py"
Set-Content -Path $tmp -Value $py -Encoding UTF8
python $tmp
if ($LASTEXITCODE -ne 0) {
  Write-Host "Python icon gen failed — PWA still works with SVG icons." -ForegroundColor Yellow
} else {
  Write-Host "PWA PNG icons ready in $OutDir" -ForegroundColor Green
}
