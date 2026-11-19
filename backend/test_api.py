"""API test: python test_api.py [cover_dir]   (cover.png/.jpg/.webp/.bmp + mylogo.png)"""
import os, sys
from fastapi.testclient import TestClient
import server

d = sys.argv[1] if len(sys.argv) > 1 else "/tmp/e2e"
c = TestClient(server.app)
fails = 0
def ok(cond, msg):
    global fails
    print(("PASS " if cond else "FAIL ") + msg); fails += (not cond)
def up(name):
    with open(os.path.join(d, name), "rb") as f:
        r = c.post("/api/upload", files={"file": (name, f)})
    assert r.status_code == 200, r.text
    return r.json()

assert c.get("/api/health").json()["ok"]
infos = {n: up(n) for n in ["cover.png", "cover.jpg", "cover.webp", "cover.bmp"]}
for n, i in infos.items():
    ok(i["width"] == 3000 and i["height"] == 2000, f"upload {n}: {i['format']} {i['width']}x{i['height']} copies {i['copies']:.1f}")
r = c.post("/api/upload", files={"file": ("x.txt", b"not an image")})
ok(r.status_code == 400, "non-image rejected")

# logo previews
for src, extra in [("standard", {}), ("text", {"logo_text": "UNI"}), ("upload", {})]:
    files = {"logo_file": ("l.png", open(os.path.join(d, "mylogo.png"), "rb"))} if src == "upload" else None
    r = c.post("/api/logo/preview", data={"logo_source": src, **extra}, files=files)
    ok(r.status_code == 200 and r.headers["content-type"] == "image/png" and int(r.headers["x-ink-pixels"]) > 100, f"logo preview {src}: ink {r.headers.get('x-ink-pixels')}")

def embed(iid, key="k1", method="dct", src="upload"):
    data = dict(image_id=iid, key=key, alpha=25, method=method, logo_source=src, logo_text="UNI")
    files = {"logo_file": ("l.png", open(os.path.join(d, "mylogo.png"), "rb"))} if src == "upload" else None
    return c.post("/api/embed", data=data, files=files)

def extract(iid, key="k1", method="dct", mode="search", src="upload"):
    data = dict(image_id=iid, key=key, alpha=25, method=method, mode=mode, logo_source=src, logo_text="UNI", null_trials=30)
    files = {"logo_file": ("l.png", open(os.path.join(d, "mylogo.png"), "rb"))} if src == "upload" else None
    r = c.post("/api/extract", data=data, files=files)
    assert r.status_code == 200, r.text
    return r.json()

# embed into every input type with the custom (uploaded) logo
wm_ids = {}
for n in ["cover.jpg", "cover.webp", "cover.bmp", "cover.png"]:
    r = embed(infos[n]["id"])
    assert r.status_code == 200, r.text
    j = r.json(); wm_ids[n] = j["id"]
    ok(j["psnr"] > 38 and j["ssim"] > 0.96, f"embed into {n}: PSNR {j['psnr']:.2f} SSIM {j['ssim']:.4f} in {j['seconds']}s")

wid = wm_ids["cover.png"]
e = extract(wid)
ok(e["ber"] == 0 and e["detected"], f"search, no attack: NC {e['nc']:.3f} BER {e['ber']:.3f} score {e['score']:.3f} thr {e['threshold']:.3f}")
e = extract(wid, mode="aligned", src="standard")
ok(e["structure"] - e["structure_baseline"] > 0.12, f"aligned (no logo needed): structure {e['structure']:.2f} vs baseline {e['structure_baseline']:.2f}")
e = extract(wid, key="wrong", mode="aligned", src="standard")
ok(e["structure"] - e["structure_baseline"] < 0.05, f"aligned wrong key looks like noise: excess {e['structure']-e['structure_baseline']:.3f}")
e = extract(wid, key="wrong")
ok(not e["detected"], f"search wrong key not detected: score {e['score']:.3f} thr {e['threshold']:.3f}")

# attacks
def attack(iid, **kw):
    r = c.post("/api/attack", data=dict(image_id=iid, **kw)); assert r.status_code == 200, r.text; return r.json()
a = attack(wid, jpeg_quality=70)
ok(a["format"] == "JPEG", f"attack {a['desc']} -> {a['format']}")
e = extract(a["id"]); ok(e["ber"] < 0.02, f"JPEG70: NC {e['nc']:.3f} BER {e['ber']:.3f}")
a = attack(wid, jpeg_quality=50); e = extract(a["id"]); ok(e["nc"] > 0.85, f"JPEG50: NC {e['nc']:.3f} BER {e['ber']:.3f}")
a = attack(wid, crop_x=753, crop_y=505, crop_w=1500, crop_h=1000, jpeg_quality=70)
e = extract(a["id"]); ok(e["ber"] < 0.02, f"crop 1500x1000 + JPEG70: NC {e['nc']:.3f} BER {e['ber']:.3f} offset {e['offset']} phase {e['phase']}")
a = attack(wid, crop_x=301, crop_y=417, crop_w=512, crop_h=512)
e = extract(a["id"]); ok(e["nc"] > 0.9, f"crop 512x512: NC {e['nc']:.3f}")
a = attack(wid, crop_x=301, crop_y=417, crop_w=384, crop_h=384)
e = extract(a["id"]); print(f"INFO crop 384x384 (< 1 copy of every bit): NC {e['nc']:.3f} BER {e['ber']:.3f}")
a = attack(wid, noise_sigma=3); e = extract(a["id"]); ok(e["ber"] < 0.02, f"noise sigma=3: BER {e['ber']:.3f}")
r = c.post("/api/attack", data=dict(image_id=wid, crop_x=2900, crop_y=0, crop_w=500, crop_h=500))
ok(r.status_code == 400, "crop outside image rejected: " + r.json()["detail"][:60])

# other formats extract (JPEG-origin cover embedded then PNG)
for n, i in wm_ids.items():
    e = extract(i); ok(e["ber"] == 0, f"extract from watermarked version of {n}: BER {e['ber']:.3f}")

# text logo, standard logo round trip
for src in ("text", "standard"):
    j = embed(infos["cover.png"]["id"], src=src).json()
    a = attack(j["id"], jpeg_quality=70)
    e = extract(a["id"], src=src); ok(e["ber"] < 0.02, f"{src} logo, JPEG70: NC {e['nc']:.3f}")

# LSB baseline
j = embed(infos["cover.png"]["id"], method="lsb").json()
a = attack(j["id"], jpeg_quality=90)
e = extract(a["id"], method="lsb"); ok(e["ber"] > 0.3 and not e["detected"], f"LSB dies under JPEG90: BER {e['ber']:.3f}")
e = extract(j["id"], method="lsb"); ok(e["ber"] == 0, f"LSB fine without attack: BER {e['ber']:.3f}")

# download / preview
r = c.get(f"/api/image/{wid}/download"); ok(r.status_code == 200 and r.content[:4] == b"\x89PNG", "download returns PNG")
r = c.get(f"/api/image/{wid}/preview?max=600"); ok(r.status_code == 200 and r.content[:2] == b"\xff\xd8", "preview returns JPEG")
# small image rejected
import cv2, numpy as np
ok_, buf = cv2.imencode(".png", np.zeros((300, 300, 3), np.uint8) + 100)
s = c.post("/api/upload", files={"file": ("small.png", buf.tobytes())}).json()
r = embed(s["id"], src="standard"); ok(r.status_code == 400, "too-small image rejected: " + r.json()["detail"][:50])
print("\nALL PASSED" if not fails else f"\n{fails} FAILED"); sys.exit(1 if fails else 0)
