"""
Musify-X Comprehensive Build & Rebranding Pipeline
===================================================
Completely transforms the base Chromium/Brave Android APK into Musify-X:
1. Extracts vector contour from the official Musify-X liquid 'M' logo.
2. Compiles 9 dynamic XML vector drawables (URL bar shields, in-app branding, day/night vectors) with AAPT2.
3. Injects dynamic adaptive launcher icons supporting system Day/Night real-time theme switching.
4. Generates high-resolution raster WebP mipmap icons with circular clipping.
5. Comprehensive UI string rebranding across resources.arsc (over 36,000 strings):
   - "Brave VPN" -> "Musify-X VPN"
   - "Brave Shields" -> "Musify-X Shields"
   - "Brave News" -> "Musify-X News"
   - "Brave Rewards" -> "Musify-X Rewards"
   - "Brave Leo" -> "Musify-X AI"
   - "Brave Search" -> "Musify-X Search"
   - "Brave Playlist" -> "Musify-X Playlist"
   - "Brave Sync" -> "Musify-X Sync"
   - "Brave Wallet" -> "Musify-X Wallet"
   - "Brave Browser" -> "Musify-X Browser"
   - "Brave Talk" -> "Musify-X Talk"
   - "About Brave" -> "About Musify-X"
   - "Welcome to Brave" -> "Welcome to Musify-X"
   - "The Brave Authors" -> "The Musify-X Authors"
   - "Brave" -> "Musify-X" across all localized strings
6. Rebrands all Chromium localized DataPack files (assets/locales/*.pak, 80+ locales).
7. Aligns APK to 4-byte boundaries using zipalign.
8. Cryptographically signs the output APK using apksigner.
"""

import os
import sys
import zipfile
import subprocess
import io
import struct
import shutil
import re
import hashlib
import zlib
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
    
    versions = sorted(os.listdir(build_tools_root), reverse=True)
    if not versions:
        raise FileNotFoundError(f"No build-tools version found in {build_tools_root}")
    build_tools_path = os.path.join(build_tools_root, versions[0])
    
    aapt2 = os.path.join(build_tools_path, "aapt2.exe")
    zipalign = os.path.join(build_tools_path, "zipalign.exe")
    apksigner = os.path.join(build_tools_path, "apksigner.bat")
    
    platforms_root = os.path.join(sdk_dir, "platforms")
    plat_versions = sorted([p for p in os.listdir(platforms_root) if p.startswith("android-")], reverse=True)
    if not plat_versions:
        raise FileNotFoundError(f"No android platform found in {platforms_root}")
    android_jar = os.path.join(platforms_root, plat_versions[0], "android.jar")
    
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

def replace_brave_text(text: str) -> str:
    """Smart replacement of Brave branding to Musify-X while preserving URLs & package names."""
    if "com.brave." in text or "com/brave/" in text:
        return text
    if text.startswith("brave://") or text.startswith("http://") or text.startswith("https://"):
        return text
    
    # Specific feature branding
    text = re.sub(r'\bBrave VPN\b', 'Musify-X VPN', text)
    text = re.sub(r'\bBrave Shields\b', 'Musify-X Shields', text)
    text = re.sub(r'\bBrave News\b', 'Musify-X News', text)
    text = re.sub(r'\bBrave Rewards\b', 'Musify-X Rewards', text)
    text = re.sub(r'\bBrave Leo\b', 'Musify-X AI', text)
    text = re.sub(r'\bBrave Search\b', 'Musify-X Search', text)
    text = re.sub(r'\bBrave Playlist\b', 'Musify-X Playlist', text)
    text = re.sub(r'\bBrave Sync\b', 'Musify-X Sync', text)
    text = re.sub(r'\bBrave Wallet\b', 'Musify-X Wallet', text)
    text = re.sub(r'\bBrave Browser\b', 'Musify-X Browser', text)
    text = re.sub(r'\bBrave Talk\b', 'Musify-X Talk', text)
    text = re.sub(r'\bAbout Brave\b', 'About Musify-X', text)
    text = re.sub(r'\bWelcome to Brave\b', 'Welcome to Musify-X', text)
    text = re.sub(r'\bThe Brave Authors\b', 'The Musify-X Authors', text)
    text = re.sub(r'\bBrave Software Inc\b', 'Musify-X Inc', text)
    text = re.sub(r'\bBrave Software\b', 'Musify-X Software', text)
    
    # General word boundary replacements (preserving case, avoiding URLs like brave.com)
    text = re.sub(r'(?<![/\w])Brave(?!\.(?:com|org|io|net|app|ai|me))(?!\w)', 'Musify-X', text)
    text = re.sub(r'(?<![/\w])brave(?!\.(?:com|org|io|net|app|ai|me))(?!\w)', 'musify-x', text)
    text = re.sub(r'(?<![/\w])BRAVE(?!\.(?:com|org|io|net|app|ai|me))(?!\w)', 'MUSIFY-X', text)
    return text

def rebrand_resources_arsc(arsc_data: bytes) -> bytes:
    """Parse and replace all Brave strings in resources.arsc global StringPool."""
    tbl_type, tbl_hdr_size, tbl_size, pkg_count = struct.unpack('<HHII', arsc_data[:12])
    sp_offset = tbl_hdr_size
    sp_type, sp_hdr_size, sp_size, str_count, style_count, flags, strings_start, styles_start = struct.unpack('<HHIIIIII', arsc_data[sp_offset:sp_offset+28])
    
    is_utf8 = (flags & (1 << 8)) != 0 or (flags & 0x01) != 0
    offsets_start = sp_offset + 28
    string_offsets = struct.unpack(f'<{str_count}I', arsc_data[offsets_start : offsets_start + str_count * 4])
    
    style_offsets_start = offsets_start + str_count * 4
    if style_count > 0:
        style_offsets = struct.unpack(f'<{style_count}I', arsc_data[style_offsets_start : style_offsets_start + style_count * 4])
    else:
        style_offsets = ()
        
    data_abs = sp_offset + strings_start
    strings = []
    
    for i in range(str_count):
        pos = data_abs + string_offsets[i]
        if is_utf8:
            u16_len = arsc_data[pos]
            pos += 1
            if u16_len & 0x80:
                u16_len = ((u16_len & 0x7F) << 8) | arsc_data[pos]
                pos += 1
            u8_len = arsc_data[pos]
            pos += 1
            if u8_len & 0x80:
                u8_len = ((u8_len & 0x7F) << 8) | arsc_data[pos]
                pos += 1
            s_bytes = arsc_data[pos : pos + u8_len]
            strings.append(s_bytes)
        else:
            u16_len = struct.unpack('<H', arsc_data[pos:pos+2])[0]
            pos += 2
            if u16_len & 0x8000:
                u16_len = ((u16_len & 0x7FFF) << 16) | struct.unpack('<H', arsc_data[pos:pos+2])[0]
                pos += 2
            s_bytes = arsc_data[pos : pos + u16_len * 2]
            strings.append(s_bytes)
            
    if style_count > 0:
        style_data_bytes = arsc_data[sp_offset + styles_start : sp_offset + sp_size]
    else:
        style_data_bytes = b""
        
    remainder = arsc_data[sp_offset + sp_size:]
    
    # Rebrand strings
    replaced_count = 0
    new_strings = []
    for s_bytes in strings:
        try:
            s_str = s_bytes.decode('utf-8', errors='surrogatepass')
            new_str = replace_brave_text(s_str)
            if new_str != s_str:
                replaced_count += 1
                new_strings.append(new_str.encode('utf-8', errors='surrogatepass'))
            else:
                new_strings.append(s_bytes)
        except Exception:
            new_strings.append(s_bytes)
            
    print(f"  -> Rebranded {replaced_count:,} strings in resources.arsc")
    
    # Re-encode StringPool
    encoded_strings = []
    new_offsets = []
    cur_offset = 0
    
    for s_bytes in new_strings:
        new_offsets.append(cur_offset)
        if is_utf8:
            try:
                s_text = s_bytes.decode('utf-8', errors='surrogatepass')
                u16_len = len(s_text.encode('utf-16-le', errors='surrogatepass')) // 2
            except Exception:
                u16_len = len(s_bytes)
            u8_len = len(s_bytes)
            
            hdr = bytearray()
            if u16_len > 0x7F:
                hdr.append(0x80 | ((u16_len >> 8) & 0x7F))
                hdr.append(u16_len & 0xFF)
            else:
                hdr.append(u16_len)
                
            if u8_len > 0x7F:
                hdr.append(0x80 | ((u8_len >> 8) & 0x7F))
                hdr.append(u8_len & 0xFF)
            else:
                hdr.append(u8_len)
                
            entry = bytes(hdr) + s_bytes + b"\x00"
        else:
            u16_len = len(s_bytes) // 2
            hdr = bytearray()
            if u16_len > 0x7FFF:
                hdr += struct.pack('<H', 0x8000 | ((u16_len >> 16) & 0x7FFF))
                hdr += struct.pack('<H', u16_len & 0xFFFF)
            else:
                hdr += struct.pack('<H', u16_len)
            entry = bytes(hdr) + s_bytes + b"\x00\x00"
            
        encoded_strings.append(entry)
        cur_offset += len(entry)
        
    strings_blob = b"".join(encoded_strings)
    strings_pad_len = (4 - (len(strings_blob) % 4)) % 4
    strings_blob += b"\x00" * strings_pad_len
    
    offsets_table = struct.pack(f'<{str_count}I', *new_offsets)
    if style_count > 0:
        style_offsets_table = struct.pack(f'<{style_count}I', *style_offsets)
    else:
        style_offsets_table = b""
        
    new_sp_hdr_size = 28
    new_strings_start = new_sp_hdr_size + len(offsets_table) + len(style_offsets_table)
    
    if style_count > 0:
        new_styles_start = new_strings_start + len(strings_blob)
        new_sp_size = new_styles_start + len(style_data_bytes)
    else:
        new_styles_start = 0
        new_sp_size = new_strings_start + len(strings_blob)
        
    new_sp_pad_len = (4 - (new_sp_size % 4)) % 4
    new_sp_size += new_sp_pad_len
    
    new_sp_header = struct.pack('<HHIIIIII', 0x0001, new_sp_hdr_size, new_sp_size, str_count, style_count, flags, new_strings_start, new_styles_start)
    new_sp_chunk = new_sp_header + offsets_table + style_offsets_table + strings_blob + style_data_bytes + (b"\x00" * new_sp_pad_len)
    
    new_total_size = tbl_hdr_size + len(new_sp_chunk) + len(remainder)
    new_tbl_header = struct.pack('<HHII', 0x0002, tbl_hdr_size, new_total_size, pkg_count)
    
    return new_tbl_header + new_sp_chunk + remainder

def rebrand_pak_data(pak_data: bytes) -> bytes:
    """Parse and replace all Brave strings in Chromium DataPack (version 5)."""
    version = struct.unpack('<I', pak_data[:4])[0]
    if version != 5:
        return pak_data
        
    encoding = pak_data[4]
    resource_count, alias_count = struct.unpack('<HH', pak_data[8:12])
    
    index_start = 12
    entries = []
    for i in range(resource_count + 1):
        rid, offset = struct.unpack('<HI', pak_data[index_start + i*6 : index_start + i*6 + 6])
        entries.append((rid, offset))
        
    alias_start = index_start + (resource_count + 1) * 6
    aliases = []
    for i in range(alias_count):
        arid, target_idx = struct.unpack('<HH', pak_data[alias_start + i*4 : alias_start + i*4 + 4])
        aliases.append((arid, target_idx))
        
    resources = {}
    for i in range(resource_count):
        rid, start = entries[i]
        _, end = entries[i+1]
        raw_res = pak_data[start:end]
        try:
            txt = raw_res.decode('utf-8')
            new_txt = replace_brave_text(txt)
            resources[rid] = new_txt.encode('utf-8')
        except Exception:
            resources[rid] = raw_res
            
    # Repack DataPack
    header = struct.pack('<IB3sHH', 5, encoding, b'\x00\x00\x00', resource_count, alias_count)
    index_len = (resource_count + 1) * 6
    alias_len = alias_count * 4
    data_start = len(header) + index_len + alias_len
    
    new_entries = []
    cur_offset = data_start
    data_parts = []
    
    for i in range(resource_count):
        rid = entries[i][0]
        content = resources[rid]
        new_entries.append((rid, cur_offset))
        data_parts.append(content)
        cur_offset += len(content)
        
    last_rid = entries[-1][0]
    new_entries.append((last_rid, cur_offset))
    
    index_bytes = b"".join(struct.pack('<HI', rid, off) for rid, off in new_entries)
    alias_bytes = b"".join(struct.pack('<HH', arid, tidx) for arid, tidx in aliases)
    payload = b"".join(data_parts)
    
    return header + index_bytes + alias_bytes + payload

def patch_classes2_dex(dex_data: bytes) -> bytes:
    """
    Patches classes2.dex so that whenever Musify-X is opened,
    it automatically navigates to and browses https://open.spotify.com:
    1. Replaces string 29887 in-place with 'https://open.spotify.com/?source=musify-x-official' (exact 50 bytes).
    2. Injects intent initialization into ChromeTabbedActivity.<init> (code_off=4320152):
       When intent.getData() == null (e.g. launched from home screen / drawer / cold start),
       it automatically sets data = https://open.spotify.com and action = ACTION_VIEW.
    3. Patches default homepage in Lua2; (code_off=1699276) to open.spotify.com.
    4. Recalculates SHA-1 and Adler32 checksums.
    """
    d = bytearray(dex_data)
    
    # 1. Update string 29887 in-place
    target_idx = 29887
    string_ids_off = struct.unpack('<I', d[60:64])[0]
    old_off = struct.unpack('<I', d[string_ids_off + target_idx*4 : string_ids_off + (target_idx+1)*4])[0]
    new_url = b'https://open.spotify.com/?source=musify-x-official'
    assert len(new_url) == 50
    assert d[old_off] == 50
    d[old_off + 1 : old_off + 1 + 50] = new_url

    # 2. Patch ChromeTabbedActivity.<init> at 4320152
    code_off = 4320152
    units = [
        # 00-02: invoke-virtual {v3}, Activity.getIntent() -> 6e 10 69 04 03 00
        0x106e, 0x0469, 0x0003,
        # 03: move-result-object v0 -> 0c 00
        0x000c,
        # 04-05: if-eqz v0, +22 (to unit 26 return-void) -> 38 00 16 00
        0x0038, 0x0016,
        # 06-08: invoke-virtual {v0}, Intent.getData() -> 6e 10 72 06 00 00
        0x106e, 0x0672, 0x0000,
        # 09: move-result-object v1 -> 0c 01
        0x010c,
        # 10-11: if-nez v1, +16 (to unit 26 return-void) -> 39 01 10 00
        0x0139, 0x0010,
        # 12-13: const-string v1, 29887 (0x74bf) -> 1a 01 bf 74
        0x011a, 0x74bf,
        # 14-16: invoke-static {v1}, Uri.parse(String) -> 71 10 9f 0a 01 00
        0x1071, 0x0a9f, 0x0001,
        # 17: move-result-object v1 -> 0c 01
        0x010c,
        # 18-20: invoke-virtual {v0, v1}, Intent.setData(Uri) -> 6e 20 a3 06 10 00
        0x206e, 0x06a3, 0x0010,
        # 21-22: const-string v1, 25087 (0x61ff) -> 1a 01 ff 61
        0x011a, 0x61ff,
        # 23-25: invoke-virtual {v0, v1}, Intent.setAction(String) -> 6e 20 9d 06 10 00
        0x206e, 0x069d, 0x0010,
        # 26: return-void -> 0e 00
        0x000e,
    ]
    while len(units) < 36:
        units.append(0x0000)
    assert len(units) == 36
    insns_bytes = struct.pack(f'<{len(units)}H', *units)
    d[code_off + 16 : code_off + 16 + len(insns_bytes)] = insns_bytes

    # 3. Patch default homepage in Lua2; at 1699276
    lua2_off = 1699276
    d[lua2_off + 16 + 8 : lua2_off + 16 + 12] = struct.pack('<HH', 0x011a, 0x74bf)

    # 4. Update checksums
    d[12:32] = hashlib.sha1(d[32:]).digest()
    adler = zlib.adler32(d[12:]) & 0xffffffff
    d[8:12] = struct.pack('<I', adler)
    
    print("  -> Patched classes2.dex: ChromeTabbedActivity & HomepageManager default to open.spotify.com.")
    return bytes(d)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_brave_apk = os.path.join(base_dir, "Brave.apk")
    
    if not os.path.exists(src_brave_apk):
        print(f"[ERROR] Base Brave.apk not found at {src_brave_apk}")
        sys.exit(1)
        
    tools = find_android_tools()
    print(f"[*] Detected Android Build Tools at: {os.path.dirname(tools['aapt2'])}")
    print(f"[*] Using platform: {tools['android_jar']}")
    
    # Official brand assets
    asset_white_trans = os.path.join(base_dir, "assets", "icons", "logo-white-transparent.png")
    
    if not os.path.exists(asset_white_trans):
        print(f"[ERROR] Brand asset not found: {asset_white_trans}")
        sys.exit(1)

    build_dir = os.path.join(base_dir, "build_temp")
    res_dir = os.path.join(build_dir, "res", "drawable")
    shutil.rmtree(build_dir, ignore_errors=True)
    os.makedirs(res_dir, exist_ok=True)

    print("\n[Step 1/8] Extracting Vector Contour from Musify-X Logo...")
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

    print("\n[Step 2/8] Generating Vector Drawables for In-App & Dynamic Launcher...")
    # Base 9 icons
    with open(os.path.join(res_dir, "uwm.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="{path_24}"/>
</vector>''')

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

    with open(os.path.join(res_dir, "pig.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="20dp"
    android:height="20dp"
    android:viewportWidth="24"
    android:viewportHeight="24">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="{path_24}"/>
</vector>''')

    with open(os.path.join(res_dir, "ki5.xml"), "w") as f:
        f.write(f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="24dp"
    android:height="24dp"
    android:viewportWidth="168"
    android:viewportHeight="168">
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="{path_168}"/>
</vector>''')

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

    # All 42 in-app lion vector replacements to completely eliminate Brave lion everywhere
    lion_files_specs = [
        ("-SX.xml", "v_sx", 272, 221, 272, 221, "#FFFFFFFF"),
        ("2iB.xml", "v_2ib", 75, 18, 75, 18, "#FFFFFFFF"),
        ("3DF.xml", "v_3df", 24, 24, 960, 960, "#FFFFFFFF"),
        ("3kr.xml", "v_3kr", 24, 24, 960, 960, "#FFFFFFFF"),
        ("9xr.xml", "v_9xr", 24, 24, 960, 960, "#FFFFFFFF"),
        ("G1k.xml", "v_g1k", 20, 20, 960, 960, "#FFFFFFFF"),
        ("IHP.xml", "v_ihp", 24, 24, 960, 960, "#FFFFFFFF"),
        ("KAy.xml", "v_kay", 24, 24, 960, 960, "#FFFFFFFF"),
        ("KTE.xml", "v_kte", 128, 128, 128, 128, "#FFFFFFFF"),
        ("PpV.xml", "v_ppv", 24, 24, 960, 960, "#FFFFFFFF"),
        ("Q1J.xml", "v_q1j", 24, 24, 960, 960, "#FFFFFFFF"),
        ("RSq.xml", "v_rsq", 24, 24, 960, 960, "#FFFFFFFF"),
        ("SGm.xml", "v_sgm", 200, 173, 207, 180, "#FFFFFFFF"),
        ("SJ9.xml", "v_sj9", 24, 24, 960, 960, "#FFFFFFFF"),
        ("SOF.xml", "v_sof", 164, 162, 164, 162, "#FFFFFFFF"),
        ("THr.xml", "v_thr", 24, 24, 960, 960, "#FFFFFFFF"),
        ("TKV.xml", "v_tkv", 200, 97, 200, 97, "#FFFFFFFF"),
        ("aUO.xml", "v_auo", 24, 24, 960, 960, "#FFFFFFFF"),
        ("abX.xml", "v_abx", 114, 114, 114, 114, "#FFFFFFFF"),
        ("b2P.xml", "v_b2p", 24, 24, 960, 960, "#FFFFFFFF"),
        ("bYe.xml", "v_bye", 164, 150, 164, 150, "#FFFFFFFF"),
        ("cTk.xml", "v_ctk", 24, 24, 960, 960, "#FFFFFFFF"),
        ("egV.xml", "v_egv", 87, 102, 87, 102, "#FFFFFFFF"),
        ("frC.xml", "v_frc", 24, 24, 960, 960, "#FFFFFFFF"),
        ("hEV.xml", "v_hev", 24, 24, 960, 960, "#FFFFFFFF"),
        ("kHH.xml", "v_khh", 412, 129, 412, 129, "#FFFFFFFF"),
        ("kcY.xml", "v_kcy", 302, 302, 302, 302, "#FFFFFFFF"),
        ("lFm.xml", "v_lfm", 311, 226, 311, 226, "#FFFFFFFF"),
        ("n-E.xml", "v_ne", 114, 114, 114, 114, "#FFFFFFFF"),
        ("oOb.xml", "v_oob", 379, 105, 379, 105, "#FFFFFFFF"),
        ("oV9.xml", "v_ov9", 24, 24, 960, 960, "#FFFFFFFF"),
        ("pXs.xml", "v_pxs", 24, 24, 960, 960, "#FFFFFFFF"),
        ("sl3.xml", "v_sl3", 24, 24, 960, 960, "#FFFFFFFF"),
        ("sly.xml", "v_sly", 24, 24, 960, 960, "#FFFFFFFF"),
        ("tQz.xml", "v_tqz", 412, 283, 412, 283, "#FFFFFFFF"),
        ("tkq.xml", "v_tkq", 24, 24, 960, 960, "#FFFFFFFF"),
        ("uFv.xml", "v_ufv", 412, 129, 412, 129, "#FFFFFFFF"),
        ("v5C.xml", "v_v5c", 24, 24, 960, 960, "#FFFFFFFF"),
        ("vDs.xml", "v_vds", 128, 93, 128, 93, "#FFFFFFFF"),
        ("val.xml", "v_val", 164, 150, 164, 150, "#FFFFFFFF"),
        ("x_p.xml", "v_xp", 300, 180, 300, 180, "#FFFFFFFF"),
        ("yjj.xml", "v_yjj", 24, 24, 960, 960, "#FFFFFFFF"),
    ]

    all_vector_items = ["uwm.xml", "di6.xml", "yul.xml", "wq9.xml", "kv0.xml", "pig.xml", "ki5.xml", "vmw.xml", "7vu.xml"]

    for target_zip, cname, w_dp, h_dp, vp_w, vp_h, col in lion_files_specs:
        fname = f"{cname}.xml"
        fpath = os.path.join(res_dir, fname)
        all_vector_items.append(fname)
        pd = generate_svg_path(vp_w, vp_h, 0.82)
        content = f'''<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="{w_dp}dp" android:height="{h_dp}dp"
    android:viewportWidth="{vp_w}" android:viewportHeight="{vp_h}">
    <path android:fillColor="{col}" android:pathData="{pd}"/>
</vector>'''
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)

    with open(os.path.join(build_dir, "AndroidManifest.xml"), "w") as f:
        f.write('''<manifest xmlns:android="http://schemas.android.com/apk/res/android" package="com.musifyx">
    <uses-sdk android:minSdkVersion="29" android:targetSdkVersion="36"/>
</manifest>''')

    print("\n[Step 3/8] Compiling Vector XMLs with AAPT2...")
    for item in all_vector_items:
        cmd = [tools["aapt2"], "compile", os.path.join(res_dir, item), "-o", build_dir]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            print(f"Error compiling {item}:", res.stderr)
            sys.exit(1)

    flats = [os.path.join(build_dir, f"drawable_{item}.flat") for item in all_vector_items]
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

        # Map all lion specs back to their exact zip paths
        for target_zip, cname, _, _, _, _, _ in lion_files_specs:
            binary_vectors[f"res/{target_zip}"] = z.read(f"res/drawable/{cname}.xml")

    print(f"  -> Successfully generated {len(binary_vectors)} binary vector XMLs.")

    print("\n[Step 4/8] Patching Dynamic Adaptive Icon XMLs...")
    with zipfile.ZipFile(src_brave_apk, "r") as z:
        r2e_data = bytearray(z.read("res/r2e.xml"))
        bjw_data = bytearray(z.read("res/BJw.xml"))

    r2e_data[224:228] = struct.pack("<I", 0x7f0909b8)
    r2e_data[304:308] = struct.pack("<I", 0x7f0909c7)

    bjw_data[224:228] = struct.pack("<I", 0x7f0909b8)
    bjw_data[304:308] = struct.pack("<I", 0x7f0909c7)
    print("  -> Patched dynamic adaptive switcher in res/r2e.xml and res/BJw.xml.")

    print("\n[Step 5/8] Generating High-Resolution Raster Mipmap Icons...")
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
        "res/80y": make_launcher_icon(48),
        "res/k1k": make_launcher_icon(72),
        "res/gSD": make_launcher_icon(96),
        "res/R4U": make_launcher_icon(144),
        "res/tT1": make_launcher_icon(192),
        "res/QtC": make_adaptive_fg(108),
        "res/rps": make_adaptive_fg(162),
        "res/PQv": make_adaptive_fg(216),
        "res/EFE": make_adaptive_fg(324),
        "res/ima": make_adaptive_fg(432),
        "res/lMS": make_adaptive_bg(108),
        "res/c5g": make_adaptive_bg(162),
        "res/6Pj": make_adaptive_bg(216),
        "res/BLH": make_adaptive_bg(324),
        "res/PCI": make_adaptive_bg(432),
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

    print("\n[Step 6/8] Comprehensive String Rebranding (resources.arsc & 80+ Locales PAK)...")
    unaligned_apk = os.path.join(base_dir, "Musify-X-unaligned.apk")
    aligned_apk = os.path.join(base_dir, "Musify-X-aligned.apk")
    signed_apk = os.path.join(base_dir, "Musify-X-signed.apk")
    final_output_apk = os.path.join(base_dir, "Musify-X.apk")

    if os.path.exists(unaligned_apk): os.remove(unaligned_apk)
    if os.path.exists(aligned_apk): os.remove(aligned_apk)
    if os.path.exists(signed_apk): os.remove(signed_apk)

    rebranded_paks_count = 0
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

                # Rebrand resources.arsc
                if item.filename == "resources.arsc":
                    print("  -> Processing resources.arsc...")
                    content = rebrand_resources_arsc(content)

                # Rebrand Chromium localization .pak files
                elif item.filename.startswith("assets/locales/") and item.filename.endswith(".pak"):
                    content = rebrand_pak_data(content)
                    rebranded_paks_count += 1

                # Patch classes2.dex for automatic open.spotify.com browsing
                elif item.filename == "classes2.dex":
                    print("  -> Processing classes2.dex...")
                    content = patch_classes2_dex(content)

                # Replace assets/drawables/XMLs
                if item.filename in all_file_replacements:
                    content = all_file_replacements[item.filename]

                zinfo = zipfile.ZipInfo(filename=item.filename, date_time=item.date_time)
                zinfo.compress_type = item.compress_type
                zinfo.external_attr = item.external_attr
                zout.writestr(zinfo, content)

    print(f"  -> Rebranded {rebranded_paks_count} locale PAK files (VPN, Shields, Rewards, AI, Sync).")

    print("\n[Step 7/8] 4KB Zipalign (Memory Page Optimization)...")
    res = subprocess.run([tools["zipalign"], "-p", "-f", "4", unaligned_apk, aligned_apk], capture_output=True, text=True)
    if res.returncode != 0:
        print("Zipalign error:", res.stderr)
        sys.exit(1)
    print("  -> Zipalign complete (4-byte page aligned).")

    print("\n[Step 8/8] Cryptographic Signing with Apksigner...")
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
    print(" BUILD SUCCESSFUL: Musify-X.apk fully rebranded!")
    print("========================================================")

if __name__ == "__main__":
    main()
