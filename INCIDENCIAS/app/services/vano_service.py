# app/services/vano_service.py

from app.database.sqlserver import get_sqlserver_connection
import pyodbc
import logging
from scipy.spatial import KDTree
import numpy as np

def obtener_trazo_vanos(codigo_inicio: str, codigo_fin: str):
    """
    Dado el NodNtcse inicial (estructura A) y final (estructura B),
    esta función construye el “camino de vanos” entre A y B. Usa un BFS
    y, cuando no existe un VanCodigoAnt explícito, hace un fallback
    calculando el vano cuyo extremo (VanX2, VanY2) esté más cerca al
    comienzo del vano actual (VanX1, VanY1).

    Retorna tupla (camino_de_vanodos, polilinea) donde:
      - camino_de_vanodos = [VanCodigo1, VanCodigo2, ..., VanCodigoN]
        en orden A→B. Si no existe ruta, devuelve ([], []).
      - polilinea = [(lat1, lng1), (lat2, lng2), ...] cuyos puntos son
        exactamente (VanY1, VanX1) del primer tramo, luego (VanY2, VanX2)
        de cada tramo en orden. Si no existe ruta, devuelve ([], []).
    """
    conn = None
    cursor = None
    try:
        conn = get_sqlserver_connection()
        cursor = conn.cursor()

        # -------------------------------------------------------------
        # 1) Obtener “nodo interno” (columna 'nodo') para poste A y B,
        #    filtrando IdEstado=1 y NodBTMT='M'.
        # -------------------------------------------------------------
        cursor.execute("""
            SELECT nodo
              FROM dbo.EST_Poste
             WHERE NodNtcse = ?
               AND IdEstado = 1
               AND NodBTMT = 'M'
        """, (codigo_inicio.strip(),))
        fila_ini = cursor.fetchone()
        if not fila_ini:
            # No existe nodo interno MT activo para A → no ruta.
            return [], []
        nodo_ini = fila_ini[0]

        cursor.execute("""
            SELECT nodo
              FROM dbo.EST_Poste
             WHERE NodNtcse = ?
               AND IdEstado = 1
               AND NodBTMT = 'M'
        """, (codigo_fin.strip(),))
        fila_fin = cursor.fetchone()
        if not fila_fin:
            # No existe nodo interno MT activo para B → no ruta.
            return [], []
        nodo_fin = fila_fin[0]

        # -------------------------------------------------------------
        # 2) Cargar en memoria todos los vanos activos (IdEstado = 1),
        #    obteniendo VanCodigo, VanCodigoAnt, nodoposte, VanX1, VanY1, VanX2, VanY2.
        # -------------------------------------------------------------
        cursor.execute("""
            SELECT VanCodigo, VanCodigoAnt, nodoposte, VanX1, VanY1, VanX2, VanY2
              FROM dbo.RDP_Vano
             WHERE IdEstado = 1
        """)
        rows = cursor.fetchall()

        # Construimos listas paralelas en Python:
        #   vanos_list  = [ { "VanCodigo":…, "VanCodigoAnt":…, "nodoposte":…, "VanX1":…, "VanY1":…, "VanX2":…, "VanY2":… }, … ]
        vanos_list = []
        for (vc, vca, nodo, x1, y1, x2, y2) in rows:
            vanos_list.append({
                "VanCodigo":     int(vc),
                "VanCodigoAnt":  None if vca is None else int(vca),
                "nodoposte":     int(nodo),
                "VanX1":         float(x1),
                "VanY1":         float(y1),
                "VanX2":         float(x2),
                "VanY2":         float(y2)
            })

        # Si no hay vanos activos en toda la tabla, devolvemos vacíos:
        if not vanos_list:
            return [], []

        # Mapeamos VanCodigo → índice en vanos_list (para fácil lookup)
        cod2idx = {v["VanCodigo"]: idx for idx, v in enumerate(vanos_list)}

        # Construimos la lista de endpoints [(x2,y2), ...] en el mismo orden de vanos_list.
        endpoints = [(v["VanX2"], v["VanY2"]) for v in vanos_list]

        # Armamos un KDTree para hacer consultas “¿qué (x2,y2) está más cerca de este (x1,y1)?”
        tree = KDTree(endpoints)

        # -------------------------------------------------------------
        # 3) Encontrar TODOS los VanCodigo que terminan en nodo_fin
        # -------------------------------------------------------------
        #   SELECT VanCodigo FROM RDP_Vano WHERE nodoposte = nodo_fin AND IdEstado = 1
        initial_cursor = conn.cursor()
        initial_cursor.execute("""
            SELECT VanCodigo
              FROM dbo.RDP_Vano
             WHERE nodoposte = ?
               AND IdEstado = 1
        """, (nodo_fin,))
        vs = initial_cursor.fetchall()
        initial_cursor.close()

        if not vs:
            # No hay ningún vano que termine en el nodo de la estructura B
            return [], []

        # Colectamoslos como lista de enteros
        vanos_inicio = [int(r[0]) for r in vs]

        # -------------------------------------------------------------
        # 4) Hacemos un BFS “hacia atrás” a partir de cada uno de esos VanCodigo,
        #    para intentar llegar a cualquiera cuyo nodoposte == nodo_ini.
        # -------------------------------------------------------------
        from collections import deque
        queue = deque()
        visited = set()  # conjunto de VanCodigo que ya pusimos en la busca

        # Cada elemento de queue será (van_codigo_actual, [path hasta aquí]),
        # donde “path” es la lista de VanCodigo en orden desde B→…→cur.
        for vc in vanos_inicio:
            queue.append((vc, [vc]))
            visited.add(vc)

        camino_final = None
        while queue:
            cur_van, path = queue.popleft()

            # Extraemos los datos de cur_van desde vanos_list:
            idx = cod2idx.get(cur_van)
            if idx is None:
                # por alguna razón no tenemos ese VanCodigo en vanos_list
                continue
            info = vanos_list[idx]
            nodo_dest = info["nodoposte"]

            # 4.1) Si este vano “llega” a nodo_ini, lo tomamos como final y terminamos
            if nodo_dest == nodo_ini:
                camino_final = path[:]  # path ya va de B→…→cur_van
                break

            # 4.2) Si existe un VanCodigoAnt explícito, lo encolamos
            van_ant = info["VanCodigoAnt"]
            if van_ant is not None:
                if van_ant not in visited:
                    visited.add(van_ant)
                    queue.append((van_ant, path + [van_ant]))
            else:
                # 4.3) Si VanCodigoAnt es NULL, hacemos fallback espacial:
                #      Buscamos hasta K = 3 vanos cuyo (VanX2,VanY2) esté más cerca al (VanX1,VanY1)
                x1 = info["VanX1"]
                y1 = info["VanY1"]

                # KDTree.query devuelve los K índices más cercanos; devuelve
                #   dists = array de distancias,
                #   idxs  = array de índices en endpoints que son los más cercanos
                K = 3
                dists, idxs = tree.query((x1, y1), k=K)

                # Si K=1, idxs vendrá como un solo valor en vez de lista; lo normalizamos:
                if not isinstance(idxs, (list, tuple, np.ndarray)):
                    idxs = [idxs]
                    dists = [dists]

                # Encolamos cada uno de esos van candidatos, en orden crece de distancia Euclidiana:
                for ii in idxs:
                    van_cand = vanos_list[ii]["VanCodigo"]
                    if van_cand not in visited:
                        visited.add(van_cand)
                        queue.append((van_cand, path + [van_cand]))

        # Si no hallamos ningún camino
        if camino_final is None:
            logging.warning(
                f"obtener_trazo_vanos: no se encontró ruta válida "
                f"entre '{codigo_inicio}' y '{codigo_fin}'."
            )
            return [], []

        # -------------------------------------------------------------
        # 5) Invertimos camino_final (hoy está de B→…→A). Queremos A→B.
        # -------------------------------------------------------------
        camino_final.reverse()  # ahora está en orden A→…→B

        # -------------------------------------------------------------
        # 6) A partir de cada VanCodigo en camino_final, construimos la polilínea:
        #    [(lat1, lng1), (lat2, lng2), …] donde cada tramo añade
        #      - si es el primer tramo, append (VanY1, VanX1)
        #      - luego append siempre (VanY2, VanX2)
        # -------------------------------------------------------------
        polilinea = []
        first = True
        for van_cd in camino_final:
            idx = cod2idx[van_cd]
            info = vanos_list[idx]
            x1, y1, x2, y2 = info["VanX1"], info["VanY1"], info["VanX2"], info["VanY2"]
            if first:
                polilinea.append((y1, x1))
                first = False
            polilinea.append((y2, x2))

        return camino_final, polilinea

    except pyodbc.Error as e:
        logging.error(f"Error en SQL al buscar ruta: {e}")
        return [], []

    finally:
        if cursor:
            try:
                cursor.close()
            except:
                pass
        if conn:
            try:
                conn.close()
            except:
                pass
