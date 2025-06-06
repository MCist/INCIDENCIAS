# app/services/vano_service.py  –  versión 3 (mejorada)
from __future__ import annotations

import logging
import heapq
from collections import defaultdict
from typing import List, Tuple, Dict, Set

import numpy as np
from scipy.spatial import KDTree
import pyodbc

from app.database.sqlserver import get_sqlserver_connection


# ───────── Parámetros globales ─────────
EPS           = 3e-6        # ≈ 0.30 m
MAX_FALLBACK  = 5e-4        # ≈ 55 m  (solo si no hay vecino explícito)
K_NEIGHBOURS  = 8           # nº de vecinos KD-Tree
MAX_ANG_DEG   = 120         # giro máximo admitido en fallback
# ───────────────────────────────────────


# ───────── utilidades geométricas ─────────
def _dist(p1, p2) -> float:
    return np.hypot(p1[0] - p2[0], p1[1] - p2[1])


def _angle(v1, v2) -> float:
    n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return 180.0
    cosang = np.clip(np.dot(v1, v2) / (n1 * n2), -1, 1)
    return np.degrees(np.arccos(cosang))


def _round_key(x: float, y: float, tol: float = EPS) -> tuple[int, int]:
    """Clave entera estable para agrupar puntos dentro de ±EPS."""
    scale = 1.0 / tol
    return int(round(x * scale)), int(round(y * scale))
# ─────────────────────────────────────────


# ───────── Algoritmo principal ─────────
Camino     = List[int]
Polilinea  = List[Tuple[float, float]]      # [(lat, lng), …]


def obtener_trazo_vanos(
    codigo_inicio: str,
    codigo_fin: str
) -> Tuple[Camino, Polilinea]:

    conn = cur = None
    try:
        # 1) Datos de los postes A y B --------------------------
        conn = get_sqlserver_connection()
        cur  = conn.cursor()

        sql_poste = """
            SELECT nodo, NodX, NodY
              FROM dbo.EST_Poste
             WHERE NodNtcse = ? AND IdEstado = 1 AND NodBTMT = 'M'
        """
        cur.execute(sql_poste, codigo_inicio.strip())
        r_ini = cur.fetchone()
        cur.execute(sql_poste, codigo_fin.strip())
        r_fin = cur.fetchone()
        if not r_ini or not r_fin:
            return [], []

        nodo_ini, x_ini, y_ini = int(r_ini.nodo), float(r_ini.NodX), float(r_ini.NodY)
        nodo_fin               = int(r_fin.nodo)

        # 2) Vanos MT activos ----------------------------------
        cur.execute("""
            SELECT VanCodigo, VanCodigoAnt, nodoposte,
                   VanX1, VanY1, VanX2, VanY2
              FROM dbo.RDP_Vano
             WHERE IdEstado = 1
        """)
        rows = cur.fetchall()
        if not rows:
            return [], []

        vlist = []
        for r in rows:
            vlist.append({
                "vc":  int(r.VanCodigo),
                "ant": None if r.VanCodigoAnt is None else int(r.VanCodigoAnt),
                "npo": int(r.nodoposte),
                "x1":  float(r.VanX1), "y1": float(r.VanY1),
                "x2":  float(r.VanX2), "y2": float(r.VanY2),
            })

        idx: Dict[int, int] = {v["vc"]: i for i, v in enumerate(vlist)}

        # grafo “hijos”
        hijos: Dict[int, List[int]] = defaultdict(list)
        for v in vlist:
            if v["ant"] is not None:
                hijos[v["ant"]].append(v["vc"])

        # 2.1) Índice coord → vanos cuyo extremo (x2,y2) coincide
        coord2van: Dict[tuple[int, int], List[int]] = defaultdict(list)
        for v in vlist:
            coord2van[_round_key(v["x2"], v["y2"])].append(v["vc"])

        # KD-Tree sobre extremos (x2,y2) para fallback
        t_end = KDTree([(v["x2"], v["y2"]) for v in vlist])

        # 3) Dijkstra inverso ---------------------------------
        inicio = [v["vc"] for v in vlist if v["npo"] == nodo_fin]
        if not inicio:
            return [], []

        heap: List[Tuple[float, Camino]] = [(0.0, [vc]) for vc in inicio]
        mejor_coste: Dict[int, float]    = {vc: 0.0 for vc in inicio}

        while heap:
            coste, camino = heapq.heappop(heap)
            actual        = camino[-1]
            vact          = vlist[idx[actual]]

            # 3.1) Condición de parada (llegó al poste A)
            if (_dist((vact["x1"], vact["y1"]), (x_ini, y_ini)) < EPS
                    or vact["npo"] == nodo_ini):
                camino.reverse()                       # A → B
                pol, first = [], True
                for vc in camino:
                    inf = vlist[idx[vc]]
                    if first:
                        pol.append((inf["y1"], inf["x1"]))
                        first = False
                    pol.append((inf["y2"], inf["x2"]))
                return camino, pol

            # 3.2) Vecinos “naturales” ------------------------
            vecinos: Set[int] = set()
            if vact["ant"] is not None:
                vecinos.add(vact["ant"])
            vecinos.update(hijos.get(actual, []))

            #    + Vecinos que comparten coordenada ----------
            key1 = _round_key(vact["x1"], vact["y1"])   # extremo inicial
            key2 = _round_key(vact["x2"], vact["y2"])   # extremo final
            vecinos.update(coord2van.get(key1, []))
            vecinos.update(coord2van.get(key2, []))
            vecinos.discard(vact["vc"])                 # evita bucle trivial

            # 3.3) Fallback KD-Tree si aún no hay vecinos ----
            if not vecinos:
                dists, idxs = t_end.query((vact["x1"], vact["y1"]), k=K_NEIGHBOURS)
                if np.isscalar(idxs):           # k = 1
                    idxs, dists = [int(idxs)], [float(dists)]

                vec_act = np.array([vact["x2"] - vact["x1"],
                                    vact["y2"] - vact["y1"]])

                for dist, ii in zip(dists, idxs):
                    if dist > MAX_FALLBACK:
                        break
                    cand = vlist[ii]
                    ang  = _angle(vec_act,
                                  np.array([cand["x2"] - cand["x1"],
                                            cand["y2"] - cand["y1"]]))
                    if ang > MAX_ANG_DEG:
                        continue
                    vecinos.add(cand["vc"])

            # 3.4) Expansión de vecinos ----------------------
            for vn in vecinos:
                nuevo_coste = coste + _dist(
                    (vact["x1"], vact["y1"]),
                    (vlist[idx[vn]]["x1"], vlist[idx[vn]]["y1"])
                )
                if nuevo_coste < mejor_coste.get(vn, 1e9):
                    mejor_coste[vn] = nuevo_coste
                    heapq.heappush(heap, (nuevo_coste, camino + [vn]))

        # No se encontró ruta
        return [], []

    except pyodbc.Error as e:
        logging.error("VanService SQL error: %s", e)
        return [], []

    finally:
        try:
            cur and cur.close()
            conn and conn.close()
        except Exception:
            pass
