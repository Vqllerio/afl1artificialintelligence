# ============================================================
# GRAPH-SEARCH DENGAN PETA NYATA OPENSTREETMAP (UNWEIGHTED)
# Rumah (Jl. Sangir No.94) -> Kampus UC Makassar (CitraLand City CPI)
# ============================================================

import sys
import io
import os
import lzma
import shutil
import glob

# --- Paksa stdout UTF-8 agar aman di Windows ---
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import osmnx as ox
import networkx as nx


# ============================================================
# 0. KONFIGURASI
# ============================================================
OSM_FILE_NAME = "makassar.osm"

# Koordinat (perkiraan — sesuaikan jika perlu)
RUMAH_LAT, RUMAH_LON   = -5.1355, 119.4055   # Jl. Sangir No.94, Wajo
KAMPUS_LAT, KAMPUS_LON = -5.1555, 119.3955   # CitraLand City CPI


# ============================================================
# 1. DECOMPRESS .osm.xz -> .osm (kalau belum ada)
# ============================================================
def ensure_osm_file(xz_name, osm_name):
    if os.path.exists(osm_name):
        print(f"[OK] File '{osm_name}' sudah ada, skip decompress.")
        return osm_name

    if not os.path.exists(xz_name):
        candidates = glob.glob("*.osm.xz") + glob.glob("*.osm")
        if not candidates:
            print(f"[ERROR] File '{xz_name}' tidak ditemukan di folder ini.")
            sys.exit(1)
        xz_name = candidates[0]
        print(f"[INFO] Menggunakan file yang ditemukan: {xz_name}")

    if xz_name.endswith(".osm"):
        return xz_name

    print(f"[INFO] Decompressing '{xz_name}' -> '{osm_name}' ...")
    with lzma.open(xz_name, "rb") as f_in:
        with open(osm_name, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    size_mb = os.path.getsize(osm_name) / (1024 * 1024)
    print(f"[OK] Decompress selesai. Ukuran file .osm: {size_mb:.1f} MB")
    return osm_name


# ============================================================
# 2. LOAD GRAF
# ============================================================
osm_path = ensure_osm_file(XZ_FILE_NAME, OSM_FILE_NAME)

print(f"\n[INFO] Loading graph dari '{osm_path}' ...")
G = ox.graph_from_xml(osm_path, simplify=True, retain_all=False)
print(f"[OK] Graf berhasil dimuat: {G.number_of_nodes()} node, {G.number_of_edges()} edge")

# Konversi ke undirected
G_undirected = ox.convert.to_undirected(G)
print("[OK] Graf siap — bobot diabaikan saat pencarian (weight=None).")


# ============================================================
# 3. FUNGSI BANTU: EKSTRAK NAMA JALAN DARI EDGE
# ============================================================
def get_edge_name(G, u, v):
    """
    Ambil nama jalan dari edge antara node u dan v.
    Kalau tidak ada nama, coba ambil atribut lain (ref, highway).
    """
    try:
        edge_data = G.get_edge_data(u, v)
        if not edge_data:
            return None

        # Kalau MultiGraph, ambil edge pertama
        if isinstance(edge_data, dict) and any(isinstance(k, int) for k in edge_data.keys()):
            # MultiDiGraph: keys -> {key: {attrs}}
            data = next(iter(edge_data.values()))
        else:
            data = edge_data

        # Prioritas: name -> ref -> highway
        if 'name' in data and data['name']:
            name = data['name']
            if isinstance(name, list):
                name = name[0]
            return name
        if 'ref' in data and data['ref']:
            return f"({data['ref']})"
        if 'highway' in data and data['highway']:
            hw = data['highway']
            if isinstance(hw, list):
                hw = hw[0]
            return f"[{hw}]"
    except Exception:
        pass
    return None


def describe_path(G, path, start_label, goal_label):
    """
    Ubah list node ID menjadi list deskripsi yang enak dibaca.
    Format: ['Rumah (Jl. Sangir)', 'via Jl. Ahmad Yani', 'via Jl. Riburane', ..., 'Kampus UC']
    """
    lines = [f"{start_label}  [node {path[0]}]"]

    current_street = None
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        name = get_edge_name(G, u, v) or f"(unnamed {u}->{v})"

        if name != current_street:
            lines.append(f"  |  via {name}")
            current_street = name

    lines.append(f"{goal_label}  [node {path[-1]}]")
    return lines


# ============================================================
# 4. CARI NODE TERDEKAT
# ============================================================
start_node = ox.distance.nearest_nodes(G_undirected, X=RUMAH_LON, Y=RUMAH_LAT)
goal_node  = ox.distance.nearest_nodes(G_undirected, X=KAMPUS_LON, Y=KAMPUS_LAT)

print(f"\n[INFO] Node awal  (Rumah) : {start_node}")
print(f"[INFO] Node tujuan (Kampus): {goal_node}")


# ============================================================
# 5. JALANKAN GRAPH-SEARCH (BFS UNWEIGHTED)
# ============================================================
try:
    path = nx.shortest_path(G_undirected, source=start_node, target=goal_node, weight=None)
    print("\n" + "=" * 60)
    print("=== JALUR DITEMUKAN ===")
    print("=" * 60)

    # Tampilkan dalam bentuk nama jalan
    pretty = describe_path(
        G_undirected, path,
        start_label="RUMAH (Jl. Sangir No.94, Melayu Baru, Wajo)",
        goal_label="KAMPUS UC (CitraLand City CPI, Jl. Sunset Boulevard)"
    )
    for line in pretty:
        print(line)

    print(f"\nTotal: {len(path) - 1} langkah (edge), {len(path)} node")

    # Bonus: daftar nama jalan unik yang dilalui
    streets = []
    for i in range(len(path) - 1):
        nm = get_edge_name(G_undirected, path[i], path[i + 1])
        if nm and nm not in streets:
            streets.append(nm)
    print(f"\nJalan yang dilalui ({len(streets)}):")
    for s in streets:
        print(f"  - {s}")

except nx.NetworkXNoPath:
    print("\n[ERROR] Tidak ada jalur yang ditemukan.")
except nx.NodeNotFound as e:
    print(f"\n[ERROR] Node tidak ditemukan: {e}")

print("\n[DONE]")