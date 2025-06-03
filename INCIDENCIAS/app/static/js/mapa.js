// app/static/js/mapa.js – con lógica extendida para “Vano”

document.addEventListener("DOMContentLoaded", () => {
  /* ------------------------------------------------------------------
   * 1. Configuración inicial del mapa
   * ----------------------------------------------------------------*/
  const Zoom_ini    = 14;                   // nivel de zoom inicial
  const piuraCenter = [-5.1945, -80.6328];  // centro inicial en Piura

  // Obtenemos el JSON inyectado por map.html
  const coords = JSON.parse(
    document.getElementById("coordenadas-data").textContent
  ) || [];

  // Limites de Piura
  const bounds = L.latLngBounds(
    [-6, -81.6],
    [-3.2, -79.4]
  );

  const map = L.map("map", {
    maxBounds: bounds,
    maxBoundsViscosity: 0.7,
    worldCopyJump: false,
    minZoom: 8,
  }).setView(piuraCenter, Zoom_ini);

  let modo = "auto";  // “auto” | “heat” | “cluster”

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors"
  }).addTo(map);


  /* ------------------------------------------------------------------
   * 2. Capas de calor y clúster de incidencias
   * ----------------------------------------------------------------*/
  const heat = L.heatLayer([], {
    radius: getDynamicRadius(map.getZoom()),
    blur: 40,
    maxZoom: 10,
    gradient: {0.1:"blue",0.3:"lime",0.5:"yellow",0.7:"orange",1.0:"red"}
  });

  const clusterGroup = L.markerClusterGroup({
    iconCreateFunction: cluster => {
      const avg = cluster.getAllChildMarkers()
                         .reduce((s, m) => s + (m.options.peso || 0.7), 0)
                       / cluster.getChildCount();
      const color =
        avg >= 0.85 ? "red" :
        avg >= 0.7  ? "orange":
        avg >= 0.5  ? "gold"  :
                      "gray";
      return L.divIcon({
        html: `<div style="background:${color};
                          border-radius:50%;padding:1px;color:#fff;">
                 <b>${cluster.getChildCount()}</b>
               </div>`,
        className: "custom-cluster-icon",
        iconSize: [40, 40]
      });
    }
  });


  /* ------------------------------------------------------------------
   * 3. Capa exclusiva para “Vano” (polilíneas + puntos extremos)
   * ----------------------------------------------------------------*/
  // Aquí almacenaremos todas las líneas y puntos que correspondan a “vanos”
  const vanoLayer = L.layerGroup().addTo(map);


  /* ------------------------------------------------------------------
   * 4. Red eléctrica estática (GeoJSON) + filtrado dinámico
   * ----------------------------------------------------------------*/
  let fullRedes     = null;  // guardamos todo el GeoJSON
  let redesLayer    = null;  // el objeto L.GeoJSON que mostramos/ocultamos
  let redesCargadas = false;

  const filtroAli    = document.getElementById("filtroAli");
  const filtroArea   = document.getElementById("filtroArea");
  const filtroCrit   = document.getElementById("filtroCriticidad");
  const filtroEstado = document.getElementById("filtroEstado");
  const filtroTipo   = document.getElementById("filtroTipo");

  // Control de capas (solo una entrada)
  const layerControl = L.control.layers(null, null, {collapsed:true}).addTo(map);

  function pintarRedes() {
    if (!fullRedes) return;
    redesLayer.clearLayers();

    const aliSel  = filtroAli.value;
    const areaSel = filtroArea.value;
    const critSel = filtroCrit.value;
    const estSel  = filtroEstado.value;

    // 1) Determinamos qué alimentadores cumplen Área/Criticidad/Estado
    const feedersDynamic = new Set(
      coords
        .filter(c => {
          if (areaSel && c.area !== areaSel) return false;
          const lvl =
            c.peso >= 0.85 ? "alta" :
            c.peso >= 0.7  ? "media":
            c.peso >= 0.5  ? "baja" :
                             "leve";
          if (critSel && lvl !== critSel) return false;
          if (estSel  && c.estado !== estSel) return false;
          return true;
        })
        .map(c => c.ali_nombre.trim())
    );

    // 2) Decidimos el conjunto de alimentadores que se mostrarán
    let feedersToShow;
    if (aliSel === "__con_incid__") {
      // “Con incidencias” → solo los alimentadores dinámicamente filtrados
      feedersToShow = feedersDynamic;
    } else if (aliSel) {
      // Un alimentador específico
      feedersToShow = new Set([aliSel]);
    } else {
      // “Todos” → si hay filtros activos usamos dinámicos; si no, todos
      const anyFilter = areaSel || critSel || estSel;
      feedersToShow = anyFilter
        ? feedersDynamic
        : new Set(fullRedes.features.map(f => f.properties.alimentador.trim()));
    }

    // 3) Filtramos el GeoJSON según esos alimentadores
    const feats = fullRedes.features.filter(f =>
      feedersToShow.has(f.properties.alimentador.trim())
    );

    // 4) Actualizamos la capa
    redesLayer.addData(feats);
  }

  function cargarRedEstaticas() {
    if (redesCargadas) return;
    fetch("/data/redes.geojson")
      .then(r => r.json())
      .then(data => {
        fullRedes = data;
        redesLayer = L.geoJSON(null, {
          style: { color:"#FF0000", opacity:0.6, weight:1 },
          pane:  "overlayPane"
        }).addTo(map);
        layerControl.addOverlay(redesLayer, "Red Eléctrica");

        // Insertamos la opción “Con incidencias” en el select filtroAli
        filtroAli.insertBefore(
          new Option("Con incidencias", "__con_incid__"),
          filtroAli.children[1]
        );
        filtroAli.value = "__con_incid__";

        // Pintamos por primera vez
        pintarRedes();

        // Repintamos cada vez que cambie cualquiera de esos selects
        [filtroAli, filtroArea, filtroCrit, filtroEstado, filtroTipo]
          .forEach(el => el.addEventListener("change", pintarRedes));

        redesCargadas = true;
      })
      .catch(err => console.error("Red eléctrica:", err));
  }
  cargarRedEstaticas();


  /* ------------------------------------------------------------------
   * 5. Funciones auxiliares para incidencias
   * ----------------------------------------------------------------*/
  function crearMarker(c) {
    // c.y_inicio = latitud de inicio, c.x_inicio = longitud de inicio
    const color =
      c.peso >= 0.85 ? "red" :
      c.peso >= 0.7  ? "orange":
      c.peso >= 0.5  ? "gold"  :
                       "gray";

    const icon = L.divIcon({
      html: `<i class="fa fa-exclamation-triangle"
                    style="font-size:28px;color:${color}"></i>`,
      className: "leaflet-fa-icon",
      iconSize: [24, 24]
    });

    let evidHtml = "";
    if (c.ev_rep && c.ev_rep.length) {
      evidHtml += `<b>Evidencia reporte:</b><br>` +
                  c.ev_rep.map(u => `
                    <a href="${u}"
                       onclick="window.open('${u}','rep','width=600,height=400');return false;">
                      ${u.split('/').pop()}
                    </a>`).join("<br>") + "<br>";
    }
    if (c.ev_cie && c.ev_cie.length) {
      evidHtml += `<b>Evidencia cierre:</b><br>` +
                  c.ev_cie.map(u => `
                    <a href="${u}"
                       onclick="window.open('${u}','cie','width=600,height=400');return false;">
                      ${u.split('/').pop()}
                    </a>`).join("<br>") + "<br>";
    }

    return L.marker([c.y_inicio, c.x_inicio], { icon, peso: c.peso || 0.7 })
             .bindTooltip(c.tipo, { direction:"top", offset:[0,-12] })
             .bindPopup(`
               <div style="min-width:180px">
                 <strong>Incidencia</strong><br>
                 <b>Código:</b> ${c.cod}<br>
                 <b>Descr.:</b> ${c.descripcion}<br>
                 <b>Tipo:</b> ${c.tipo}<br>
                 <b>Ali.:</b> ${c.ali_nombre}<br>
                 <b>Área:</b> ${c.area}<br>
                 <b>Resp.:</b> ${c.responsable}<br>
                 <b>Estado:</b> ${c.estado}<br>
                 ${evidHtml}
               </div>`);
  }

  function getDynamicRadius(z) {
    if (z <= 6)   return 70;
    if (z <= 8)   return 50;
    if (z <= 10)  return 40;
    if (z <= 12)  return 30;
    return 20;
  }


  /* ------------------------------------------------------------------
   * 6. Filtros y lógica de incidencias
   * ----------------------------------------------------------------*/
  const filtroAntRad = () =>
    document.querySelector("input[name='filtroAntiguedad']:checked").value;
  const resumenDiv = document.getElementById("resumenContenido");
  const centrarBtn = document.getElementById("centrarMapa");
  const vistaSel   = document.getElementById("vistaSelector");

  (function initFiltros() {
    const setAli   = new Set(),
          setArea  = new Set(),
          setTipo  = new Set();

    coords.forEach(c => {
      c.ali_nombre && setAli.add(c.ali_nombre.trim());
      c.area       && setArea.add(c.area.trim());
      c.tipo       && setTipo.add(c.tipo.trim());
    });

    Array.from(setAli).sort()
      .forEach(v => filtroAli.append(new Option(v, v)));
    Array.from(setArea).sort()
      .forEach(v => filtroArea.append(new Option(v, v)));

    // NUEVO: llenar opciones de “Tipo de Incidencia”
    Array.from(setTipo).sort()
      .forEach(v => filtroTipo.append(new Option(v, v)));
  })();

  function filterCoords() {
    const ali  = filtroAli.value,
          area = filtroArea.value,
          crit = filtroCrit.value,
          est  = filtroEstado.value,
          tipo = filtroTipo.value,
          ant  = filtroAntRad(),
          hoy  = new Date();

    return coords.filter(c => {
      // filtro por alimentador (o “__con_incid__”)
      if (ali && ali !== "__con_incid__" && c.ali_nombre !== ali) return false;
      // filtro por área
      if (area && c.area !== area) return false;

      // filtro por criticidad
      if (crit) {
        const lvl =
          c.peso >= 0.85 ? "alta" :
          c.peso >= 0.7  ? "media":
          c.peso >= 0.5  ? "baja" :
                           "leve";
        if (lvl !== crit) return false;
      }

      // filtro por estado
      if (est && c.estado !== est) return false;

      // filtro por tipo de incidencia
      if (tipo && c.tipo !== tipo) return false;

      // filtro por antigüedad
      if (ant !== "") {
        const diff = (hoy - new Date(c.fecha)) / (1000 * 3600 * 24);
        if (ant === "0" && !(new Date(c.fecha).toDateString() === hoy.toDateString())) return false;
        if (ant !== "0" && diff < parseInt(ant, 10)) return false;
      }

      return true;
    });
  }


  /* ------------------------------------------------------------------
   * 7. actualizarMapa (con lógica para “Vano”)
   * ----------------------------------------------------------------*/
  function actualizarMapa() {
    const d = filterCoords();  // array filtrado según UI

    // 1) Limpiar capas de iteraciones previas
    clusterGroup.clearLayers();
    heat.setLatLngs([]);
    vanoLayer.clearLayers();

    // 2) Separar “vanos” y “otros”
    //    - vanos: c.tipo_elemento === "Vano" Y c.trazo es un array no vacío
    const vanos = d.filter(c =>
      c.tipo_elemento === "Vano" &&
      Array.isArray(c.trazo) && c.trazo.length > 1
    );
    const othersBase = d.filter(c => c.tipo_elemento !== "Vano");

    // 2.1) Para incluir “vanos” en heat/cluster, creamos un punto representativo por cada vano

    const others = othersBase;

    // 3) Dibujar heatmap o clusters sobre “others” (incluye vanos como puntos)
    if (modo === "heat" || (modo === "auto" && map.getZoom() <= 10)) {
      const ps = others.map(c => c.peso || 0.7);
      const m  = Math.max(...ps, 1);
      heat.setLatLngs(
        others.map(c => [c.y_inicio, c.x_inicio, (c.peso || 0.7) / m])
      );
      if (map.hasLayer(clusterGroup)) {
        map.removeLayer(clusterGroup);
      }
      map.addLayer(heat);
    }

    if (modo === "cluster" || (modo === "auto" && map.getZoom() > 10)) {
      clusterGroup.addLayers(others.map(crearMarker));
      if (map.hasLayer(heat)) {
        map.removeLayer(heat);
      }
      map.addLayer(clusterGroup);
    }
    // ————————————————
    // Función auxiliar: calcula el punto medio de una polilínea “trazo”
    // trazo = [ [lat0, lng0], [lat1, lng1], …, [latN, lngN] ]
    // Devuelve un arreglo [lat, lng] ubicado a la mitad de la longitud total.
    function puntoMedio(trazo) {
      // Convertimos cada par [lat, lng] a objetos L.LatLng para usar distanceTo()
      const latlngs = trazo.map(p => L.latLng(p[0], p[1]));

      // 1) Calcular la longitud total (en metros)
      let longTotal = 0;
      for (let i = 0; i < latlngs.length - 1; i++) {
        longTotal += latlngs[i].distanceTo(latlngs[i + 1]);
      }

      const mitad = longTotal / 2;
      let acum = 0;

      // 2) Recorrer segmentos hasta que la distancia acumulada supere “mitad”
      for (let i = 0; i < latlngs.length - 1; i++) {
        const segInicio = latlngs[i];
        const segFin    = latlngs[i + 1];
        const segmentoLen = segInicio.distanceTo(segFin);

        if (acum + segmentoLen >= mitad) {
          // 3) Interpolamos dentro de este segmento para ubicar el punto exacto
          const sobra = mitad - acum;    // distancia que nos falta dentro de este tramo
          const factor = sobra / segmentoLen; // factor entre 0 y 1 para interpolar

          const latInterpolada = segInicio.lat + (segFin.lat - segInicio.lat) * factor;
          const lngInterpolada = segInicio.lng + (segFin.lng - segInicio.lng) * factor;

          return [latInterpolada, lngInterpolada];
        }
        acum += segmentoLen;
      }

      // Si algo falla (por ejemplo, trazo muy corto), devolvemos el último punto:
      const ult = latlngs[latlngs.length - 1];
      return [ult.lat, ult.lng];
    }
    // ————————————————
    // 4) Dibujar “vanos” (polilíneas + puntos extremos), **además** de los clústeres/puntos
    vanos.forEach(c => {
      // “c.trazo” es un array [[lat0,lng0], [lat1,lng1], …, [latN,lngN]]
      const tramo = c.trazo;

      // a) Dibujar la polilínea completa
      L.polyline(tramo, {
        color: "grey",
        weight: 3,
        opacity: 0.7
      }).addTo(vanoLayer);
      // (b) Calcular el punto medio y dibujar un ícono allí
      const [latC, lngC] = puntoMedio(tramo);
      const color = c.peso >= 0.85 ? "red" :
                    c.peso >= 0.7  ? "orange" :
                    c.peso >= 0.5  ? "gold" :
                                    "gray";

      const iconVano = L.divIcon({
        html: `<i class="fa fa-exclamation-triangle" style="font-size:28px;color:${color}"></i>`,
        className: "leaflet-fa-icon",
        iconSize: [24, 24]
      });

      L.marker([latC, lngC], { icon: iconVano, peso: c.peso || 0.7 })
        .bindTooltip(c.tipo, { direction:"top", offset:[0,-12] })
        .addTo(vanoLayer);

      // b) (Opcional) Dibujar puntos en los extremos
      //    Extremo INICIAL:
      const [latIni, lngIni] = tramo[0];
      L.circleMarker([latIni, lngIni], {
        radius: 3, color: "grey", fillOpacity: 1
      })
        .bindTooltip(`Inicio Vano: ${c.cod}`, { direction:"top", offset:[0,-8] })
        .addTo(vanoLayer);

      //    Extremo FINAL:
      const [latFin, lngFin] = tramo[tramo.length - 1];
      L.circleMarker([latFin, lngFin], {
        radius: 3, color: "grey", fillOpacity: 1
      })
        .bindTooltip(`Fin Vano: ${c.cod}`, { direction:"top", offset:[0,-8] })
        .addTo(vanoLayer);
    });

    // 5) Actualizar resumen numérico
    resumenDiv.innerHTML = `<span><b>Total:</b> ${d.length}</span>`;
  }


  /* ------------------------------------------------------------------
   * 8. Listeners UI
   * ----------------------------------------------------------------*/
  vistaSel.addEventListener("change", () => {
    modo = vistaSel.value;
    actualizarMapa();
  });

  [filtroAli, filtroArea, filtroCrit, filtroEstado, filtroTipo].forEach(el =>
    el.addEventListener("change", () => {
      pintarRedes();
      actualizarMapa();
    })
  );

  document
    .querySelectorAll("input[name='filtroAntiguedad']")
    .forEach(r => r.addEventListener("change", actualizarMapa));

  map.on("zoomend moveend", () => {
    heat.setOptions({ radius: getDynamicRadius(map.getZoom()) });
    if (modo === "auto") actualizarMapa();
  });

  centrarBtn.addEventListener("click", () => {
    const d = filterCoords();
    if (!d.length) return;

    // Para centrar, incluimos los “others” y los “vanos” (usando su primer punto)
    const vanos = d.filter(c =>
      c.tipo_elemento === "Vano" &&
      Array.isArray(c.trazo) && c.trazo.length >= 1
    );
    const othersBase = d.filter(c => c.tipo_elemento !== "Vano");
    const vanosPoints = vanos.map(c => [c.trazo[0][0], c.trazo[0][1]]);
    const puntosOtros = othersBase.map(c => [c.y_inicio, c.x_inicio]);
    const allPoints = puntosOtros.concat(vanosPoints);

    if (allPoints.length) {
      map.fitBounds(L.latLngBounds(allPoints).pad(0.2));
    }
  });


  /* ------------------------------------------------------------------
   * 9. Descarga de datos a Excel
   * ----------------------------------------------------------------*/
  document.getElementById("descargarDatos")
    .addEventListener("click", () => {
      const d = filterCoords();
      if (!d.length) return alert("No hay incidencias para descargar.");
      const data = d.map(i => ({
        Latitud:    i.y_inicio,
        Longitud:   i.x_inicio,
        Codigo:     i.cod,
        Descripción:i.descripcion,
        Tipo:       i.tipo,
        Alimentador:i.ali_nombre,
        Área:       i.area,
        Responsable:i.responsable,
        Estado:     i.estado,
        Fecha:      i.fecha,
        Ocurrencia: i.ocurrencia
      }));
      const ws = XLSX.utils.json_to_sheet(data),
            wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Incidencias");
      XLSX.writeFile(wb, "incidencias.xlsx");
    });


  /* ------------------------------------------------------------------
   * 10. Pegman (Street View)
   * ----------------------------------------------------------------*/
  const pegmanIcon = L.icon({
    iconUrl: "/static/img/pegman.png",
    iconSize: [32, 32]
  });
  const pegman = L.marker([0, 0], {
    icon: pegmanIcon,
    draggable: true,
    zIndexOffset: 1000
  }).addTo(map);

  function positionPegmanBL() {
    const s = map.getSize(), m = 10;
    pegman.setLatLng(map.containerPointToLatLng(L.point(m, s.y - m)));
  }
  map.on("moveend", positionPegmanBL);
  pegman.on("dragstart", () => map.off("moveend", positionPegmanBL));
  pegman.on("dragend", e => {
    const { lat, lng } = e.target.getLatLng();
    window.open(
      `https://www.google.com/maps?q=&layer=c&cbll=${lat},${lng}`,
      "_blank"
    );
    positionPegmanBL();
    map.on("moveend", positionPegmanBL);
  });
  positionPegmanBL();


  // Inicializa clusters/heat + pinta todo por primera vez
  map.addLayer(clusterGroup);
  actualizarMapa();
});
// fin de mapa.js
