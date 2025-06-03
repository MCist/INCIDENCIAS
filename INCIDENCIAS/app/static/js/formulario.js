// app/static/js/formulario.js
document.addEventListener('DOMContentLoaded', () => {
  // --- Contenedor del campo Alimentador ---
  const grupoAli = document.getElementById('ali_nombre').closest('.form-group');

  // --- Referencias al DOM ---
  const tipoElemento       = document.getElementById('tipo_elemento');
  const descripcionInput    = document.getElementById('descripcion_elemento');
  const coordXInicioInput   = document.getElementById('coord_x_inicio');
  const coordYInicioInput   = document.getElementById('coord_y_inicio');
  const coordXFinInput      = document.getElementById('coord_x_fin');
  const coordYFinInput      = document.getElementById('coord_y_fin');

  const grupoPro    = document.getElementById('grupo_pro_coords');
  const grupoSub    = document.getElementById('grupo_sub_coords');
  const grupoTrafo  = document.getElementById('grupo_trafo');
  const grupoSum    = document.getElementById('grupo_suministro');
  const grupoMT     = document.getElementById('grupo_estructura_mt');
  const grupoVano   = document.getElementById('grupo_vano'); // debe existir en tu HTML

  const responsableSelect = document.getElementById('responsable_id');
  const areaSelect        = document.getElementById('area_responsable_id');
  // Referencia al formulario completo
  const form = document.querySelector('form');

  // Campos comunes y específicos
  const camposGlobales = {
    ali_nombre: document.getElementById('ali_nombre'),
    uun_nombre: document.getElementById('uun_nombre'),
    alicodigo:  document.getElementById('alicodigo')
  };
  const camposProCon = {
    nombre_propietario: document.getElementById('nombre_propietario_pro'),
    device_type:        document.getElementById('device_type'),
    codtennomimt:       document.getElementById('codtennomimt')
  };
  const camposSubestacion = {
    direccion:          document.getElementById('direccion'),
    nombre_propietario: document.getElementById('nombre_propietario_sub'),
    tension_bt:         document.getElementById('tension_bt'),
    tension_mt:         document.getElementById('tension_mt'),
    subconectra_bt:     document.getElementById('subconectra_bt'),
    potencia:           document.getElementById('potencia'),
    tipo_sub:           document.getElementById('tipo_sub')
  };
  const camposTrafo = {
    nombre_trafo: document.getElementById('nombre_trafo'),
    codigo_trafo: document.getElementById('codigo_trafo')
  };
  const camposSuministro = {
    cod_suministro: document.getElementById('cod_suministro'),
    sub_codigo:     document.getElementById('sub_codigo'),
    circ_codigo:    document.getElementById('circ_codigo'),
    direccion_sum:  document.getElementById('direccion_sum')
  };
  const camposMT = {
    cod_poste:  document.getElementById('cod_poste'),
    owner_type: document.getElementById('owner_type')
  };

  // --- Helpers ---
  function ocultarGrupos() {
    [grupoPro, grupoSub, grupoTrafo, grupoSum, grupoMT, grupoVano]
      .forEach(g => g.style.display = 'none');
  }
  function limpiarCampos(obj) {
    Object.values(obj).forEach(el => el.value = '');
  }
  function actualizarTiposIncidencia(areaId) {
    fetch(`/api/tipos_area/${areaId}`)
      .then(r => r.json())
      .then(data => {
        tipoSelectTS.clearOptions();
        tipoSelectTS.addOptions(data.tipos);
        tipoSelectTS.refreshOptions(false);
      });
  }
  // Escuchamos el evento submit
  form.addEventListener('submit', function(event) {
    // Si el tipo de elemento no es “Vano”, dejamos que continúe normalmente
    if (tipoElemento.value !== 'Vano') {
      return;
    }

    // Obtenemos los valores “ini” y “fin”
    const ini = tsInicio.getValue();
    const fin = tsFin.getValue();

    // Si falta alguno de los dos, dejamos que el backend valide con su propia lógica
    if (!ini || !fin) {
      return;
    }

    // DETENER momentáneamente el envío del formulario
    event.preventDefault();

    // Llamada AJAX al endpoint de validación
    fetch(`/api/validar_vano?ini=${encodeURIComponent(ini)}&fin=${encodeURIComponent(fin)}`)
      .then(response => response.json())
      .then(data => {
        if (data.ok) {
          // La ruta está completa → reenviamos el formulario
          form.submit();
        } else {
          // La ruta NO conecta
          const mensaje = 'La ruta entre "' + ini + '" y "' + fin + '" no conecta. ' +
                          '¿Deseas registrar la incidencia de todas formas?';
          if (window.confirm(mensaje)) {
            // El usuario decidió continuar de todas formas
            form.submit();
          }
          // Si el usuario elige “Cancelar” en confirm(), no hacemos nada.
        }
      })
      .catch(err => {
        // Si hay un error inesperado al llamar al backend, imprimimos en consola y permitimos el envío
        console.error('Error validando vano:', err);
        form.submit();
      });
  });

  // --- TomSelects ---
  const tipoSelectTS = new TomSelect('#tipo_id', {
    valueField: 'id',
    labelField: 'nombre',
    searchField: 'nombre',
    options: [],
    create: false,
    placeholder: 'Seleccione tipo de incidencia',
    render: { no_results: () => '<div class="no-results">No hay tipos disponibles</div>' }
  });

  // TomSelect para código_elemento (no usado en "Vano")
  const codigoSelectTS = new TomSelect('#codigo_elemento', {
    valueField: 'codigo',
    labelField: 'codigo',
    searchField: 'codigo',
    options: [],
    create: false,
    placeholder: 'Escriba código...',
    load: (term, cb) => {
      const t = tipoElemento.value;
      // no cargar cuando el tipo sea Vano
      if (!t || t === 'Vano') return cb([]);
      fetch(`/api/autocomplete_codigo?tipo=${encodeURIComponent(t)}&term=${encodeURIComponent(term)}`)
        .then(r => r.json())
        .then(list => cb(list.map(c => ({ codigo: c }))))
        .catch(() => cb([]));
    }
  });

  // TomSelect para "Estructura MT Inicio"
  const tsInicio = new TomSelect('#codigo_inicio', {
    valueField: 'codigo',
    labelField: 'codigo',
    searchField: 'codigo',
    options: [],
    create: false,
    placeholder: 'Estructura MT inicio...',
    preload: 'focus',
    load: (term, cb) => {
      fetch(`/api/autocomplete_codigo?tipo=Estructura%20MT&term=${encodeURIComponent(term)}`)
        .then(r => r.json())
        .then(list => cb(list.map(c => ({ codigo: c }))))
        .catch(() => cb([]));
    }
  });
  // TomSelect para "Estructura MT Fin"
  const tsFin = new TomSelect('#codigo_fin', {
    valueField: 'codigo',
    labelField: 'codigo',
    searchField: 'codigo',
    options: [],
    create: false,
    placeholder: 'Estructura MT fin...',
    preload: 'focus',
    load: (term, cb) => {
      fetch(`/api/autocomplete_codigo?tipo=Estructura%20MT&term=${encodeURIComponent(term)}`)
        .then(r => r.json())
        .then(list => cb(list.map(c => ({ codigo: c }))))
        .catch(() => cb([]));
    }
  });

  // Abrir dropdown al enfocar cada TomSelect
  document.getElementById('codigo_elemento')
    .addEventListener('focus', () => codigoSelectTS.open());
  document.getElementById('codigo_inicio')
    .addEventListener('focus', () => tsInicio.open());
  document.getElementById('codigo_fin')
    .addEventListener('focus', () => tsFin.open());

  // --- Cascada Responsable → Área → Tipos ---
  responsableSelect.addEventListener('change', () => {
    const rId = responsableSelect.value;
    if (!rId) return;
    fetch(`/api/responsable/${rId}`)
      .then(r => r.json())
      .then(data => {
        areaSelect.value = data.area_id;
        return data.area_id;
      })
      .then(actualizarTiposIncidencia);
  });
  areaSelect.addEventListener('change', () => {
    if (areaSelect.value) actualizarTiposIncidencia(areaSelect.value);
  });

  // --- Cambio de Tipo de Elemento ---
  tipoElemento.addEventListener('change', () => {
    const t = tipoElemento.value;

    // 1) Reset general
    codigoSelectTS.clear();     codigoSelectTS.clearOptions();
    tsInicio.clear();           tsInicio.clearOptions();
    tsFin.clear();              tsFin.clearOptions();
    descripcionInput.value     = '';
    coordXInicioInput.value    = '';
    coordYInicioInput.value    = '';
    coordXFinInput.value       = '';
    coordYFinInput.value       = '';
    limpiarCampos(camposGlobales);
    limpiarCampos(camposProCon);
    limpiarCampos(camposSubestacion);
    limpiarCampos(camposTrafo);
    limpiarCampos(camposSuministro);
    limpiarCampos(camposMT);
    ocultarGrupos();

    // 2) Mostrar solo el grupo correspondiente
    if      (t === 'Proteccion/Control')      grupoPro.style.display   = 'block';
    else if (t === 'Subestacion')             grupoSub.style.display   = 'block';
    else if (t === 'Subestación de potencia') grupoTrafo.style.display = 'block';
    else if (t === 'Suministro')              grupoSum.style.display   = 'block';
    else if (t === 'Estructura MT')           grupoMT.style.display    = 'block';
    else if (t === 'Vano')                    grupoVano.style.display  = 'block';

    // 3) Ocultar/mostrar campo “Código elemento”
    const wrapCodigo = document.getElementById('codigo_elemento').closest('.form-group');
    wrapCodigo.style.display = (t === 'Vano') ? 'none' : '';

    // 4) Cargar autocomplete normal si no es Vano
    if (t && t !== 'Vano') {
      fetch(`/api/autocomplete_codigo?tipo=${encodeURIComponent(t)}&term=`)
        .then(r => r.json())
        .then(list => {
          codigoSelectTS.clearOptions();
          list.forEach(c => codigoSelectTS.addOption({ codigo: c }));
          codigoSelectTS.refreshOptions(false);
        });
    }

    // 5) Ocultar alimentador si es Subestación de potencia
    grupoAli.style.display = (t === 'Subestación de potencia') ? 'none' : '';
  });

  // --- Selección de código único (para todos excepto “Vano”) ---
  codigoSelectTS.on('change', value => {
    const t = tipoElemento.value;
    if (!t || !value) return;

    fetch(`/api/datos_elemento?tipo=${encodeURIComponent(t)}&codigo=${encodeURIComponent(value)}`)
      .then(r => r.json())
      .then(data => {
        // Mostrar todos los subcampos antes de ocultarlos
        ['cod_suministro','nombre_trafo','cod_poste']
          .forEach(id => document.getElementById(id).closest('.form-group').style.display = '');

        // Descripción
        let desc = data.descripcion || '';
        if (t === 'Suministro') {
          desc = data.cod_suministro || '';
          document.getElementById('cod_suministro').closest('.form-group').style.display = 'none';
        }
        else if (t === 'Subestación de potencia') {
          desc = data.nombre_trafo || '';
          document.getElementById('nombre_trafo').closest('.form-group').style.display = 'none';
        }
        else if (t === 'Estructura MT') {
          desc = data.cod_poste || '';
          document.getElementById('cod_poste').closest('.form-group').style.display = 'none';
        }
        descripcionInput.value = desc;

        // Coordenadas de inicio
        const mapX = {
          'Proteccion/Control':'pro_x',  'Subestacion':'sub_x',
          'Subestación de potencia':'trafo_x',
          'Suministro':'sum_x',          'Estructura MT':'poste_x'
        };
        const mapY = {
          'Proteccion/Control':'pro_y',  'Subestacion':'sub_y',
          'Subestación de potencia':'trafo_y',
          'Suministro':'sum_y',          'Estructura MT':'poste_y'
        };
        coordXInicioInput.value = data[mapX[t]] || '';
        coordYInicioInput.value = data[mapY[t]] || '';

        // Rellenar campos específicos
        if      (t === 'Proteccion/Control')      Object.keys(camposProCon).forEach(k => camposProCon[k].value = data[k] || '');
        else if (t === 'Subestacion')             Object.keys(camposSubestacion).forEach(k => camposSubestacion[k].value = data[k] || '');
        else if (t === 'Subestación de potencia') Object.keys(camposTrafo).forEach(k => camposTrafo[k].value = data[k] || '');
        else if (t === 'Suministro')              Object.keys(camposSuministro).forEach(k => camposSuministro[k].value = data[k] || '');
        else if (t === 'Estructura MT')           Object.keys(camposMT).forEach(k => camposMT[k].value = data[k] || '');

        // Rellenar campos globales
        camposGlobales.ali_nombre.value = data.ali_nombre || '';
        camposGlobales.uun_nombre.value = data.uun_nombre || '';
        camposGlobales.alicodigo.value  = data.alicodigo  || '';
      })
      .catch(() => {
        coordXInicioInput.value = coordYInicioInput.value = '';
      });
  });

  // --- Cuando cambian los TomSelect de Vano (inicio/fin) ---
  function actualizarVano() {
    const ini = tsInicio.getValue();
    const fin = tsFin.getValue();

    // 1) Descripción combinada
    if (ini && fin)      descripcionInput.value = `${ini} – ${fin}`;
    else if (ini)        descripcionInput.value = ini;
    else if (fin)        descripcionInput.value = fin;
    else                 descripcionInput.value = '';

    // 2) Datos de Estructura MT inicio
    if (ini) {
      fetch(`/api/datos_elemento?tipo=Estructura%20MT&codigo=${encodeURIComponent(ini)}`)
        .then(r => r.json())
        .then(data => {
          camposGlobales.ali_nombre.value = data.ali_nombre || '';
          camposGlobales.uun_nombre.value = data.uun_nombre || '';
          camposGlobales.alicodigo.value  = data.alicodigo  || '';
          coordXInicioInput.value = data.poste_x || '';
          coordYInicioInput.value = data.poste_y || '';
        });
    } else {
      coordXInicioInput.value = '';
      coordYInicioInput.value = '';
      camposGlobales.ali_nombre.value = '';
      camposGlobales.uun_nombre.value = '';
      camposGlobales.alicodigo.value  = '';
    }

    // 3) Datos de Estructura MT fin
    if (fin) {
      fetch(`/api/datos_elemento?tipo=Estructura%20MT&codigo=${encodeURIComponent(fin)}`)
        .then(r => r.json())
        .then(data => {
          coordXFinInput.value = data.poste_x || '';
          coordYFinInput.value = data.poste_y || '';
        });
    } else {
      coordXFinInput.value = '';
      coordYFinInput.value = '';
    }
  }
  tsInicio.on('change', actualizarVano);
  tsFin.on('change',    actualizarVano);

  // --- Arranque (inicial) ---
  ocultarGrupos();
  limpiarCampos(camposGlobales);
  limpiarCampos(camposProCon);
  limpiarCampos(camposSubestacion);
  limpiarCampos(camposTrafo);
  limpiarCampos(camposSuministro);
  limpiarCampos(camposMT);
  coordXInicioInput.value = coordYInicioInput.value = '';
  coordXFinInput.value    = coordYFinInput.value    = '';
  tsInicio.clearOptions();
  tsFin.clearOptions();
});
