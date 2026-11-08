"""
Musify-X Build & Rebranding Pipeline
====================================
Transforms the base Chromium/Brave Android APK into Musify-X:
1. Extracts vector contour from the official Musify-X liquid 'M' logo.
2. Compiles 9 dynamic XML vector drawables (URL bar shields, in-app branding, day/night vectors) with AAPT2.
3. Injects dynamic adaptive launcher icons supporting system Day/Night real-time theme switching.
4. Generates high-resolution raster WebP mipmap icons with circular clipping.
5. Patches `resources.arsc` application label to 'Musify-X'.
6. Aligns APK to 4-byte boundaries using `zipalign`.
7. Cryptographically signs the output APK using `apksigner`.
"""

import os
import sys
import zipfile
import subprocess
import io
import struct
import shutil
import cv2
import numpy as np
from PIL import Image, ImageDraw

def find_android_tools():
    """Detect Android SDK build-tools, android.jar, and keystore."""
    local_app_data = os.environ.get("LOCALAPPDATA", r"C:\Users\adity\AppData\Local")
    default_sdk = os.path.join(local_app_data, "Android", "Sdk")
    sdk_dir = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or default_sdk
    
    build_tools_root = os.path.join(sdk_dir, "build-tools")
    if not os.path.exists(build_tools_root):
        raise FileNotFoundError(f"Android build-tools not found in {build_tools_root}")
    
    # Pick highest version
    versions = sorted(os.listdir(build_tools_root), reverse=True)
    if not versions:
        raise FileNotFoundError(f"No build-tools version found in {build_tools_root}")
    build_tools_path = os.path.join(build_tools_root, versions[0])
    
    aapt2 = os.path.join(build_tools_path, "aapt2.exe")
    zipalign = os.path.join(build_tools_path, "zipalign.exe")
    apksigner = os.path.join(build_tools_path, "apksigner.bat")
    
    # Platform android.jar
    platforms_root = os.path.join(sdk_dir, "platforms")
    plat_versions = sorted([p for p in os.listdir(platforms_root) if p.startswith("android-")], reverse=True)
    if not plat_versions:
        raise FileNotFoundError(f"No android platform found in {platforms_root}")
    android_jar = os.path.join(platforms_root, plat_versions[0], "android.jar")
    
    # Keystore
    debug_keystore = os.path.expanduser(r"~\.android\debug.keystore")
    if not os.path.exists(debug_keystore):
        raise FileNotFoundError(f"Debug keystore not found at {debug_keystore}")
        
    return {
        "aapt2": aapt2,
        "zipalign": zipalign,
        "apksigner": apksigner,
        "android_jar": android_jar,
        "keystore": debug_keystore
    }

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_brave_apk = os.path.join(base_dir, "Brave.apk")
    
    if not os.path.exists(src_brave_apk):
        print(f"[ERROR] Base Brave.apk not found at {src_brave_apk}")
        sys.exit(1)
        
    tools = find_android_tools()
    print(f"[*] Detected Android Build Tools at: {os.path.dirname(tools['aapt2'])}")
    print(f"[*] Using platform: {tools['android_jar']}")
    
    # Canonical brand assets
    asset_white_trans = os.path.join(base_dir, "assets", "icons", "logo-white-transparent.png")
    asset_black_trans = os.path.join(base_dir, "assets", "icons", "logo-black-transparent.png")
    
    if not os.path.exists(asset_white_trans):
        print(f"[ERROR] Brand asset not found: {asset_white_trans}")
        sys.exit(1)

    build_dir = os.path.join(base_dir, "build_temp")
    res_dir = os.path.join(build_dir, "res", "drawable")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(res_dir, exist_ok=True)

    print("\n[Step 1/7] Extracting Vector Contour from Musify-X Logo...")
    im_src = Image.open(asset_white_trans).convert("RGBA")
    alpha = np.array(im_src)[:, :, 3]
    _, thresh = cv2.threshold(alpha, 128, 255, cv2.THRESH_BINARY)
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_TC89_KCOS)
    main_cnt = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(main_cnt)
    cx, cy = x + w / 2.0, y + h / 2.0
    approx = cv2.approxPolyDP(main_cnt, 1.0, True)
    pts = approx.reshape(-1, 2)
    print(f"  -> Extracted {len(pts)} vector vertices (bbox: {w}x{h})")

    def generate_svg_path(target_vp_w, target_vp_h, pad_ratio=0.85):
        avail_w = target_vp_w * pad_ratio
        avail_h = target_vp_h * pad_ratio
        scale = min(avail_w / w, avail_h / h)
        target_cx = target_vp_w / 2.0
        target_cy = target_vp_h / 2.0
        transformed_pts = []
        for px, py in pts:
            tx = (px - cx) * scale + target_cx
            ty = (py - cy) * scale + target_cy
            transformed_pts.append((round(tx, 2), round(ty, 2)))
        path_d = f"M{transformed_pts[0][0]},{transformed_pts[0][1]}"
        for tx, ty in transformed_pts[1:]:
            path_d += f"L{tx},{ty}"
        path_d += "Z"
        return path_d

    path_24 = generate_svg_path(24, 24, 0.82)
    path_108 = generate_svg_path(108, 108, 0.70)
    path_168 = generate_svg_path(168, 168, 0.82)
    path_288 = generate_svg_path(288, 288, 0.75)

    print("\n[Step 2/7] Generating Vector Drawables for In-App & Dynamic Launcher...")
    # 1. uwm.xml (Shields active in URL bar: Vibrant Orange #FFFF5601)
    with open(os.path.join(res_dir, "uwm.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFF5601"
        android:pathData="{path_24}"/>
</vector>''')

    # 2. di6.xml (Shields disabled in URL bar: Neutral Grey #FF888888)
    with open(os.path.join(res_dir, "di6.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FF888888"
        android:pathData="{path_24}"/>
</vector>''')

    # 3. yul.xml (Splash & onboarding)
    with open(os.path.join(res_dir, "yul.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="128dp"
    android:height="128dp"
    android:viewportWidth="288"
    android:viewportHeight="288">
    <group android:name="brave_logo" android:pivotX="144" android:pivotY="144">
        <path
            android:fillColor="#FFFFFFFF"
            android:pathData="{path_288}"/>
    </group>
</vector>''')

    # 4. wq9.xml (Day monochrome launcher foreground: Solid Black liquid M)
    with open(os.path.join(res_dir, "wq9.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FF000000"
        android:pathData="{path_108}"/>
</vector>''')

    # 5. kv0.xml (Night monochrome launcher foreground: Solid White liquid M)
    with open(os.path.join(res_dir, "kv0.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="{path_108}"/>
</vector>''')

    # 6. pig.xml (Dialogs & Settings)
    with open(os.path.join(res_dir, "pig.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="20dp"
    android:height="20dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFF5601"
        android:pathData="{path_24}"/>
</vector>''')

    # 7. ki5.xml (Layout logo)
    with open(os.path.join(res_dir, "ki5.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="168"
    android:viewportHeight="168">
    <path
        android:fillColor="#FFFF5601"
        android:pathData="{path_168}"/>
</vector>''')

    # 8. vmw.xml (Adaptive background Day: Solid Crisp White #FFFFFFFF)
    with open(os.path.join(res_dir, "vmw.xml"), "w") as f:
        f.write('''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="M0,0h108v108h-108z"/>
</vector>''')

    # 9. 7vu.xml (Adaptive background Night: Solid Pitch Dark #FF0A0A0E)
    with open(os.path.join(res_dir, "7vu.xml"), "w") as f:
        f.write('''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path
        android:fillColor="#FF0A0A0E"
        android:pathData="M0,0h108v108h-108z"/>
</vector>''')

    with open(os.path.join(build_dir, "AndroidManifest.xml"), "w") as f:
        f.write('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.musifyx">
    <uses-sdk android:minSdkVersion="29" android:targetSdkVersion="36"/>
</manifest>''')

    print("\n[Step 3/7] Compiling Vector XMLs with AAPT2...")
    items = ["uwm.xml", "di6.xml", "yul.xml", "wq9.xml", "kv0.xml", "pig.xml", "ki5.xml", "vmw.xml", "7vu.xml"]
    for item in items:
        cmd = [tools["aapt2"], "compile", os.path.join(res_dir, item), "-o", build_dir]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error compiling {item}:", res.stderr)
            sys.exit(1)

    flats = [os.path.join(build_dir, f"drawable_{item}.flat") for item in items]
    compiled_apk = os.path.join(build_dir, "compiled.apk")
    cmd_link = [tools["aapt2"], "link", "-I", tools["android_jar"], "--manifest", os.path.join(build_dir, "AndroidManifest.xml")] + flats + ["-o", compiled_apk]
    res = subprocess.run(cmd_link, capture_output=True, text=True)
    if res.returncode != 0:
        print("Link error:", res.stderr)
        sys.exit(1)

    binary_vectors = {}
    with zipfile.ZipFile(compiled_apk, "r") as z:
        binary_vectors["res/UWM.xml"] = z.read("res/drawable/uwm.xml")
        binary_vectors["res/dI6.xml"] = z.read("res/drawable/di6.xml")
        binary_vectors["res/YUL.xml"] = z.read("res/drawable/yul.xml")
        binary_vectors["res/wq9.xml"] = z.read("res/drawable/wq9.xml")
        binary_vectors["res/kv0.xml"] = z.read("res/drawable/kv0.xml")
        binary_vectors["res/PIg.xml"] = z.read("res/drawable/pig.xml")
        binary_vectors["res/ki5.xml"] = z.read("res/drawable/ki5.xml")
        binary_vectors["res/VMw.xml"] = z.read("res/drawable/vmw.xml")
        binary_vectors["res/7VU.xml"] = z.read("res/drawable/7vu.xml")
    print(f"  -> Successfully generated {len(binary_vectors)} binary vector XMLs.")

    print("\n[Step 4/7] Patching Dynamic Adaptive Icon XMLs...")
    with zipfile.ZipFile(src_brave_apk, "r") as z:
        r2e_data = bytearray(z.read("res/r2e.xml"))
        bjw_data = bytearray(z.read("res/BJw.xml"))

    # In res/r2e.xml & res/BJw.xml:
    # background (attr at offset 224): 0x7f0909b8 (Day: res/VMw.xml Solid White, Night: res/7VU.xml Solid Dark)
    # foreground (attr at offset 304): 0x7f0909c7 (Day: res/wq9.xml Black M, Night: res/kv0.xml White M)
    r2e_data[224:228] = struct.pack("<I", 0x7f0909b8)
    r2e_data[304:308] = struct.pack("<I", 0x7f0909c7)

    bjw_data[224:228] = struct.pack("<I", 0x7f0909b8)
    bjw_data[304:308] = struct.pack("<I", 0x7f0909c7)
    print("  -> Patched dynamic adaptive switcher in res/r2e.xml and res/BJw.xml.")

    print("\n[Step 5/7] Generating High-Resolution Raster Mipmap Icons...")
    im_white_trans = Image.open(asset_white_trans).convert("RGBA")

    def make_launcher_icon(size):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse((0, 0, size - 1, size - 1), fill=(10, 10, 14, 255))
        inner_size = int(size * 0.85)
        resized_src = im_white_trans.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
        offset = (size - inner_size) // 2
        img.paste(resized_src, (offset, offset), resized_src)
        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size - 1, size - 1), fill=255)
        img.putalpha(mask)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=100)
        return buf.getvalue()

    def make_adaptive_fg(size):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        inner_size = int(size * 0.68)
        resized_src = im_white_trans.resize((inner_size, inner_size), Image.Resampling.LANCZOS)
        offset = (size - inner_size) // 2
        img.paste(resized_src, (offset, offset), resized_src)
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=100)
        return buf.getvalue()

    def make_adaptive_bg(size):
        img = Image.new("RGBA", (size, size), (10, 10, 14, 255))
        buf = io.BytesIO()
        img.save(buf, format="WEBP", quality=100)
        return buf.getvalue()

    raster_replacements = {
        # 0x7f110000 app_icon
        "res/80y": make_launcher_icon(48),
        "res/k1k": make_launcher_icon(72),
        "res/gSD": make_launcher_icon(96),
        "res/R4U": make_launcher_icon(144),
        "res/tT1": make_launcher_icon(192),
        # 0x7f110001 layered_app_icon (foreground)
        "res/QtC": make_adaptive_fg(108),
        "res/rps": make_adaptive_fg(162),
        "res/PQv": make_adaptive_fg(216),
        "res/EFE": make_adaptive_fg(324),
        "res/ima": make_adaptive_fg(432),
        # 0x7f110002 layered_app_icon_background
        "res/lMS": make_adaptive_bg(108),
        "res/c5g": make_adaptive_bg(162),
        "res/6Pj": make_adaptive_bg(216),
        "res/BLH": make_adaptive_bg(324),
        "res/PCI": make_adaptive_bg(432),
        # 0x7f110004 shortcut_icon_shadow
        "res/Nkp": make_adaptive_fg(48),
        "res/NTo": make_adaptive_fg(72),
        "res/0dH": make_adaptive_fg(96),
        "res/gG8": make_adaptive_fg(144),
        "res/tOW": make_adaptive_fg(192),
    }

    all_file_replacements = {
        **binary_vectors,
        "res/r2e.xml": bytes(r2e_data),
        "res/BJw.xml": bytes(bjw_data),
        **raster_replacements,
    }

    print("\n[Step 6/7] Repacking APK & Rebranding Application Strings...")
    unaligned_apk = os.path.join(base_dir, "Musify-X-unaligned.apk")
    aligned_apk = os.path.join(base_dir, "Musify-X-aligned.apk")
    signed_apk = os.path.join(base_dir, "Musify-X-signed.apk")
    final_output_apk = os.path.join(base_dir, "Musify-X.apk")

    old_label_bytes = b"\x0f\x0fBrave - Nightly\x00"
    new_label_bytes = b"\x08\x08Musify-X\x00" + b"\x00" * (len(old_label_bytes) - len(b"\x08\x08Musify-X\x00"))

    if os.path.exists(unaligned_apk): os.remove(unaligned_apk)
    if os.path.exists(aligned_apk): os.remove(aligned_apk)
    if os.path.exists(signed_apk): os.remove(signed_apk)

    replaced_counts = 0
    with zipfile.ZipFile(src_brave_apk, "r") as zin:
        with zipfile.ZipFile(unaligned_apk, "w") as zout:
            for item in zin.infolist():
                if item.filename.startswith("META-INF/") and (
                    item.filename.endswith(".SF") or
                    item.filename.endswith(".RSA") or
                    item.filename.endswith(".DSA") or
                    item.filename.endswith("MANIFEST.MF")
                ):
                    continue
                
                content = zin.read(item.filename)

                # Rename app title
                if item.filename == "resources.arsc":
                    if old_label_bytes in content:
                        content = content.replace(old_label_bytes, new_label_bytes, 1)
                        print("  -> Patched application-label -> 'Musify-X' in resources.arsc")
                    else:
                        print("  [!] Warning: old label bytes not found in resources.arsc")

                # Replace assets/drawables/XMLs
                if item.filename in all_file_replacements:
                    content = all_file_replacements[item.filename]
                    replaced_counts += 1

                zinfo = zipfile.ZipInfo(filename=item.filename, date_time=item.date_time)
                zinfo.compress_type = item.compress_type
                zinfo.external_attr = item.external_attr
                zout.writestr(zinfo, content)

    print(f"  -> Repacked APK with {replaced_counts} custom assets.")

    print("\n[Step 7/7] 4KB Zipalign & Apksigner...")
    res = subprocess.run([tools["zipalign"], "-p", "-f", "4", unaligned_apk, aligned_apk], capture_output=True, text=True)
    if res.returncode != 0:
        print("Zipalign error:", res.stderr)
        sys.exit(1)
    print("  -> Zipalign complete (4-byte page aligned).")

    res = subprocess.run([
        tools["apksigner"], "sign",
        "--ks", tools["keystore"],
        "--ks-pass", "pass:android",
        "--key-pass", "pass:android",
        "--out", signed_apk,
        aligned_apk
    ], capture_output=True, text=True)
    if res.returncode != 0:
        print("Apksigner error:", res.stderr)
        sys.exit(1)
    print("  -> Cryptographic signing complete.")

    res = subprocess.run([tools["apksigner"], "verify", signed_apk], capture_output=True, text=True)
    print(f"  -> Signature verification: {'PASSED' if res.returncode == 0 else 'FAILED'}")

    shutil.copyfile(signed_apk, final_output_apk)
    print(f"  -> Output generated: {final_output_apk} ({os.path.getsize(final_output_apk):,} bytes)")

    # Cleanup temp build files
    if os.path.exists(unaligned_apk): os.remove(unaligned_apk)
    if os.path.exists(aligned_apk): os.remove(aligned_apk)
    if os.path.exists(signed_apk): os.remove(signed_apk)
    shutil.rmtree(build_dir, ignore_errors=True)

    print("\n========================================================")
    print(" BUILD SUCCESSFUL: Musify-X.apk is ready!")
    print("========================================================")

if __name__ == "__main__":
    main()
