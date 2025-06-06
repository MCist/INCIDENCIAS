/*  app/static/js/mapa.js
 *  versión “backend completo” v2025-06-fix
 *  – dibuja heat-map, clusters y vanos (polilíneas + icono central)
 *  – protección JSON, reset Leaflet, filtros, resumen, centrar, descarga, pegman
 */

document.addEventListener('DOMContentLoaded', () => {

/* ------------------------------------------------------------------ */
/* 1. Leer JSON inyectado                                             */
/* ------------------------------------------------------------------ */
let coords = [];
try {
  const raw = document.getElementById('coordenadas-data')?.textContent ?? '[]';
  coords = JSON.parse(raw) || [];
} catch (e) { console.warn('⚠️  coordenadas-data inválido:', e); }
if (!Array.isArray(coords)) coords = [];

/* ------------------------------------------------------------------ */
/* 2. Inicializar mapa Leaflet                                         */
/* ------------------------------------------------------------------ */
(function initMap () {

  const Z_INIT = 14,
        CENTER = [-5.1945, -80.6328],
        BOUNDS = L.latLngBounds([-6,-81.6],[-3.2,-79.4]);

  const container = L.DomUtil.get('map');
  if (container && container._leaflet_id) container._leaflet_id = null;

  const map = L.map('map', {
    maxBounds: BOUNDS, maxBoundsViscosity: 0.7,
    worldCopyJump: false, minZoom: 8
  }).setView(CENTER, Z_INIT);

  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; OpenStreetMap contributors'
  }).addTo(map);

/* ------------------------------------------------------------------ */
/* 3. Capas heat, cluster, vano                                        */
/* ------------------------------------------------------------------ */
  let viewMode = 'auto';               // auto | heat | cluster
  let lastZoom = map.getZoom();

  const heat = L.heatLayer([], {
    radius  : getDynamicRadius(lastZoom),
    blur    : 40,
    maxZoom : 10,
    gradient: {0.1:'blue',0.3:'lime',0.5:'yellow',0.7:'orange',1:'red'}
  });

  const clusterGroup = L.markerClusterGroup({
    iconCreateFunction: cl => {
      const avg = cl.getAllChildMarkers()
                    .reduce((s,m)=>s+(m.options.peso||0.7),0) / cl.getChildCount();
      const color = avg>=0.85?'red':avg>=0.7?'orange':avg>=0.5?'gold':'gray';
      return L.divIcon({
        html: `<div style="background:${color};border-radius:50%;
                           padding:1px 3px;color:#fff;"><b>${cl.getChildCount()}</b></div>`,
        className: 'custom-cluster-icon', iconSize: [40,40]
      });
    }
  });

  const vanoLayer = L.layerGroup().addTo(map);

/* ------------------------------------------------------------------ */
/* 4. GeoJSON redes + combos                                           */
/* ------------------------------------------------------------------ */
  let fullRedes=null, redesLayer=null, redesReady=false;
  const filtroAli    = document.getElementById('filtroAli');
  const filtroArea   = document.getElementById('filtroArea');
  const filtroCrit   = document.getElementById('filtroCriticidad');
  const filtroEstado = document.getElementById('filtroEstado');
  const filtroTipo   = document.getElementById('filtroTipo');
  const filtroTipoElem = document.getElementById('filtroTipoElem');

  const layerControl = L.control.layers(null,null,{collapsed:true}).addTo(map);

  function pintarRedes(){
    if (!fullRedes) return;
    redesLayer.clearLayers();

    const aliSel=filtroAli.value, areaSel=filtroArea.value,
          critSel=filtroCrit.value, estSel=filtroEstado.value;

    const feedersDyn = new Set(
      coords.filter(c=>{
        if (areaSel && c.area!==areaSel) return false;
        const lvl=c.peso>=0.85?'alta':c.peso>=0.7?'media':c.peso>=0.5?'baja':'leve';
        if (critSel && lvl!==critSel) return false;
        if (estSel && c.estado!==estSel) return false;
        return true;
      }).map(c=>c.ali_nombre?.trim()).filter(Boolean)
    );

    let feedersToShow;
    if (aliSel==='__con_incid__')      feedersToShow=feedersDyn;
    else if (aliSel)                   feedersToShow=new Set([aliSel]);
    else {
      const any=areaSel||critSel||estSel;
      feedersToShow= any ? feedersDyn :
        new Set(fullRedes.features.map(f=>f.properties.alimentador.trim()));
    }

    redesLayer.addData(
      fullRedes.features.filter(f=>feedersToShow.has(f.properties.alimentador.trim()))
    );
  }

  function cargarRedEstaticas(){
    if (redesReady) return;
    fetch('/data/redes.geojson')
      .then(r=>r.json())
      .then(gj=>{
        fullRedes=gj;
        redesLayer=L.geoJSON(null,{style:{color:'#f00',weight:1,opacity:0.6}}).addTo(map);
        layerControl.addOverlay(redesLayer,'Red Eléctrica');
        filtroAli.prepend(new Option('Con incidencias','__con_incid__'));
        filtroAli.value='__con_incid__';
        pintarRedes();
        [filtroAli,filtroArea,filtroCrit,filtroEstado,filtroTipo,filtroTipoElem]
          .forEach(el=>el.addEventListener('change',pintarRedes));
        redesReady=true;
      })
      .catch(e=>console.error('GeoJSON redes:',e));
  }
  cargarRedEstaticas();

/* ------------------------------------------------------------------ */
/* 5. Helpers                                                          */
/* ------------------------------------------------------------------ */
  function getColor(p){return p>=0.85?'red':p>=0.7?'orange':p>=0.5?'gold':'gray';}

  function puntoMedio(trazo){
    if (!trazo||trazo.length<2) return trazo?.[0]||[0,0];
    const ll=trazo.map(p=>L.latLng(p[0],p[1]));
    const total=ll.slice(1).reduce((s,_,i)=>s+ll[i].distanceTo(ll[i+1]),0);
    let acum=0, mitad=total/2;
    for(let i=0;i<ll.length-1;i++){
      const seg=ll[i].distanceTo(ll[i+1]);
      if (acum+seg>=mitad){
        const f=(mitad-acum)/seg;
        return [ll[i].lat+(ll[i+1].lat-ll[i].lat)*f,
                ll[i].lng+(ll[i+1].lng-ll[i].lng)*f];
      }
      acum+=seg;
    }
    return trazo[trazo.length-1];
  }

  function popupHTML(c,evid){
    return `<div style="min-width:180px">
        <strong>Incidencia</strong><br>
        <b>Código:</b> ${c.cod}<br>
        <b>Descr.:</b> ${c.descripcion}<br>
        <b>Tipo:</b> ${c.tipo}<br>
        <b>Ali.:</b> ${c.ali_nombre}<br>
        <b>Área:</b> ${c.area}<br>
        <b>Resp.:</b> ${c.responsable}<br>
        <b>Estado:</b> ${c.estado}<br>
        ${evid}
      </div>`;
  }

  function crearMarker(c){
    const icon=L.divIcon({
      html:`<i class="fa fa-exclamation-triangle" style="font-size:28px;color:${getColor(c.peso)}"></i>`,
      className:'leaflet-fa-icon',iconSize:[24,24]
    });
    let evid=''; if(c.ev_rep?.length) evid += '<b>Evidencia reporte:</b><br>'+
      c.ev_rep.map(u=>`<a href="${u}" target="_blank">${u.split('/').pop()}</a>`).join('<br>')+'<br>';
    if(c.ev_cie?.length) evid += '<b>Evidencia cierre:</b><br>'+
      c.ev_cie.map(u=>`<a href="${u}" target="_blank">${u.split('/').pop()}</a>`).join('<br>')+'<br>';

    return L.marker([c.y_inicio,c.x_inicio],{icon,peso:c.peso||0.7})
            .bindTooltip(c.tipo,{direction:'top',offset:[0,-12]})
            .bindPopup(popupHTML(c,evid));
  }

  function crearMarkerVano(c){
    const icon=L.divIcon({
      html:`<i class="fa fa-exclamation-triangle" style="font-size:28px;color:${getColor(c.peso)}"></i>`,
      className:'leaflet-fa-icon',iconSize:[24,24]
    });
    let evid=''; if(c.ev_rep?.length) evid += '<b>Evidencia reporte:</b><br>'+
      c.ev_rep.map(u=>`<a href="${u}" target="_blank">${u.split('/').pop()}</a>`).join('<br>')+'<br>';
    if(c.ev_cie?.length) evid += '<b>Evidencia cierre:</b><br>'+
      c.ev_cie.map(u=>`<a href="${u}" target="_blank">${u.split('/').pop()}</a>`).join('<br>')+'<br>';

    return L.marker(puntoMedio(c.trazo),{icon,peso:c.peso||0.7})
            .bindTooltip(c.tipo,{direction:'top',offset:[0,-12]})
            .bindPopup(popupHTML(c,evid));
  }

  function getDynamicRadius(z){
    if (z<=6) return 70;
    if (z<=8) return 50;
    if (z<=10) return 40;
    if (z<=12) return 30;
    return 20;
  }

/* ------------------------------------------------------------------ */
/* 6. Combos                                                           */
/* ------------------------------------------------------------------ */
  const filtroAnt = ()=>document.querySelector("input[name='filtroAntiguedad']:checked")?.value ?? '';
  const resumenDiv=document.getElementById('resumenContenido');
  const centrarBtn=document.getElementById('centrarMapa');
  const vistaSel  =document.getElementById('vistaSelector');

  (function fillCombos(){
    const setAli=new Set(),setArea=new Set(),setTipo=new Set();setTipoElem=new Set();
    coords.forEach(c=>{
      c.ali_nombre&&setAli.add(c.ali_nombre.trim());
      c.area&&setArea.add(c.area.trim());
      c.tipo&&setTipo.add(c.tipo.trim());
      c.tipo_elemento&&setTipoElem.add(c.tipo_elemento.trim());
    });
    [...setAli].sort().forEach(v=>filtroAli.append(new Option(v,v)));
    [...setArea].sort().forEach(v=>filtroArea.append(new Option(v,v)));
    [...setTipo].sort().forEach(v=>filtroTipo.append(new Option(v,v)));
    [...setTipoElem].sort().forEach(v=>filtroTipoElem.append(new Option(v,v)));
  })();

/* ------------------------------------------------------------------ */
/* 7. Filtro principal                                                 */
/* ------------------------------------------------------------------ */
  function filterCoords(){
    const ali=filtroAli.value, area=filtroArea.value, crit=filtroCrit.value,
          est=filtroEstado.value, tipo=filtroTipo.value, tipoElem=filtroTipoElem.value, ant=filtroAnt(), hoy=new Date();

    return coords.filter(c=>{
      if (ali && ali!=='__con_incid__' && c.ali_nombre!==ali) return false;
      if (area && c.area!==area) return false;
      if (crit){
        const lvl=c.peso>=0.85?'alta':c.peso>=0.7?'media':c.peso>=0.5?'baja':'leve';
        if (lvl!==crit) return false;
      }
      if (est && c.estado!==est) return false;
      if (tipo && c.tipo!==tipo) return false;
      if (tipoElem && c.tipo_elemento!==tipoElem) return false;
      if (ant!==''){
        const diff=(hoy-new Date(c.fecha))/8.64e7;
        if (ant==='0'){
          if (new Date(c.fecha).toDateString()!==hoy.toDateString()) return false;
        } else if (diff < +ant) return false;
      }
      return true;
    });
  }

/* ------------------------------------------------------------------ */
/* 8. Redibujado principal                                             */
/* ------------------------------------------------------------------ */
  function actualizarMapa(){
    const data=filterCoords();
    clusterGroup.clearLayers(); heat.setLatLngs([]); vanoLayer.clearLayers();

    const vanos = data.filter(c=>c.tipo_elemento==='Vano' &&
                                 Array.isArray(c.trazo)&&c.trazo.length>=2);
    const others= data.filter(c=>c.tipo_elemento!=='Vano');

    const markersNorm = others.map(crearMarker);
    const markersVano = vanos.map(crearMarkerVano);

    /* heat o cluster */
    if (viewMode==='heat' || (viewMode==='auto' && map.getZoom()<=10)){
      const src=[...others,...vanos];
      const max=Math.max(...src.map(c=>c.peso||0.7),1);
      heat.setLatLngs(src.map(c=>{
        const latlng = c.tipo_elemento==='Vano' ? puntoMedio(c.trazo) : [c.y_inicio,c.x_inicio];
        return [latlng[0],latlng[1],(c.peso||0.7)/max];
      }));
      map.removeLayer(clusterGroup); map.addLayer(heat);
    } else {
      clusterGroup.addLayers([...markersNorm,...markersVano]);
      map.removeLayer(heat); map.addLayer(clusterGroup);
    }

    /* dibujar polilíneas de vanos + extremos */
    vanos.forEach(c=>{
      L.polyline(c.trazo,{color:'grey',weight:3,opacity:0.7}).addTo(vanoLayer);
      L.circleMarker(c.trazo[0],{radius:3,color:'grey',fillOpacity:1})
        .bindTooltip(`Inicio Vano: ${c.cod}`,{direction:'top',offset:[0,-8]}).addTo(vanoLayer);
      L.circleMarker(c.trazo[c.trazo.length-1],{radius:3,color:'grey',fillOpacity:1})
        .bindTooltip(`Fin Vano: ${c.cod}`,{direction:'top',offset:[0,-8]}).addTo(vanoLayer);
    });

    resumenDiv.textContent=`Total: ${data.length}`;
  }

/* ------------------------------------------------------------------ */
/* 9. Listeners UI                                                     */
/* ------------------------------------------------------------------ */
  vistaSel.addEventListener('change',e=>{viewMode=e.target.value; actualizarMapa();});
  [filtroAli,filtroArea,filtroCrit,filtroEstado,filtroTipo,filtroTipoElem]
    .forEach(el=>el.addEventListener('change',()=>{pintarRedes();actualizarMapa();}));
  document.querySelectorAll("input[name='filtroAntiguedad']")
          .forEach(r=>r.addEventListener('change',actualizarMapa));

  map.on('zoomend',()=>{
    const z=map.getZoom();
    if (z!==lastZoom){
      heat.setOptions({radius:getDynamicRadius(z)}); lastZoom=z;
      if(viewMode==='auto') actualizarMapa();
    }
  });

/* ------------------------------------------------------------------ */
/* 10. Centrar, descarga, pegman                                       */
/* ------------------------------------------------------------------ */
  centrarBtn.addEventListener('click',()=>{
    const d=filterCoords();
    if(!d.length) return;
    const pts=[
      ...d.filter(c=>c.tipo_elemento==='Vano'&&c.trazo?.length).map(c=>c.trazo[0]),
      ...d.filter(c=>c.tipo_elemento!=='Vano').map(c=>[c.y_inicio,c.x_inicio])
    ].filter(p=>Array.isArray(p)&&isFinite(p[0])&&isFinite(p[1]));
    if(pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.2));
  });

  document.getElementById('descargarDatos').addEventListener('click',()=>{
    const d=filterCoords(); if(!d.length) return alert('No hay incidencias para descargar.');
    const data=d.map(i=>({
      Latitud:i.y_inicio, Longitud:i.x_inicio, Codigo:i.cod, Descripción:i.descripcion,
      Tipo:i.tipo, Alimentador:i.ali_nombre, Área:i.area, Responsable:i.responsable,
      Estado:i.estado, TipoElemento:i.tipo_elemento, Fecha:i.fecha, Ocurrencia:i.ocurrencia
    }));
    const ws=XLSX.utils.json_to_sheet(data), wb=XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb,ws,'Incidencias'); XLSX.writeFile(wb,'incidencias.xlsx');
  });

  const pegIcon=L.icon({iconUrl:'/static/img/pegman.png',iconSize:[32,32]});
  const pegman=L.marker([0,0],{icon:pegIcon,draggable:true,zIndexOffset:1000}).addTo(map);
  const stick=()=>{const s=map.getSize(),m=10;
                   pegman.setLatLng(map.containerPointToLatLng(L.point(m,s.y-m)));};
  map.on('moveend',stick);
  pegman.on('dragstart',()=>map.off('moveend',stick));
  pegman.on('dragend',e=>{
    const {lat,lng}=e.target.getLatLng();
    window.open(`https://www.google.com/maps?q=&layer=c&cbll=${lat},${lng}`,'_blank');
    stick(); map.on('moveend',stick);
  });
  stick();

/* ------------------------------------------------------------------ */
/* 11. ¡Arrancar!                                                      */
/* ------------------------------------------------------------------ */
  map.addLayer(clusterGroup);
  actualizarMapa();

})(); /* initMap */
});   /* DOMContentLoaded */
