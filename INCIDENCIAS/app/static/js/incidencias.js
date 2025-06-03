/* app/static/js/incidencias.js – versión optimizada con red eléctrica estática */

/* ------------------------------------------------------------------
 *  Incidencias – tabla y cierre
 * ----------------------------------------------------------------*/
const ELEMENT_TYPES = [
  'Proteccion/Control',
  'Subestacion',
  'Subestación de potencia',
  'Suministro',
  'Estructura MT',
  'Vano'
];
let tbl;
$(function () {

  /* ---------- poblar combos dinámicos ---------- */
  fetch('/api/incidencias/alimentadores')
  .then(r => r.json())
  .then(arr => {
     const $sel = $('#fAli');
     arr.forEach(o => $sel.append(
        `<option value="${o.value}">${o.label}</option>`
     ));
  });

  /* ---------- DataTable --------- */
    tbl = $('#tblInc').DataTable({
    language: {
      processing: '<div class="spinner-border text-primary"></div>',
      search    : 'Buscar código&nbsp;:'           // <── punto 1
    },
    dom: 'frtip',        // quitamos el “length” selector, queda buscar + tabla + paginación
    processing : true,
    serverSide : true,
    ajax: {
      url : '/api/incidencias/data',
      data: d => {                        // filtros que viajan al server
        d.estado = $('#fEstado').val();
        d.ali    = $('#fAli').val();
        d.crit   = $('#fCrit').val();
        d.f_ini  = $('#fIni').val();
        d.f_fin  = $('#fFin').val();

        /* traducir orden ↓ */
        if (d.order?.length) {
          const idx = d.order[0].column,
                dir = d.order[0].dir,
                map = ['id','codigo', 'ali', 'desc','area','tipo',
                       'criticidad','estado','fecha'];
          d.order_col = map[idx];
          d.order_dir = dir;
        }
      }
    },
    columns: [
      {data:'id'       , orderable:true},
      {data:'codigo'   , orderable:false, searchable:true},   // ← único searchable
      {data:'ali'      , orderable:false, searchable:false},
      {data:'desc'     , orderable:false, searchable:false},
      {data:'area'     , orderable:false, searchable:false},
      {data:'tipo'     , orderable:false, searchable:false},
      {                                                      // criticidad con barra
        data:'criticidad',
        render: v => {
          const pct  = Math.round(v*100);
          const lvl  = v>=0.85 ? 'alta'
                    : v>=0.70 ? 'media'
                    : v>=0.50 ? 'baja' : 'leve';
          const col  = {alta:'#dc3545',media:'#fd7e14',
                        baja:'#ffc107',leve:'#198754'}[lvl];
          return `
            <div class="progress" style="height:8px">
              <div class="progress-bar" role="progressbar"
                   style="width:${pct}%;background:${col}"
                   title="${lvl} – ${pct}%"></div>
            </div>`;
        }
      },
      {data:'estado'   , orderable:false, searchable:false},
      {data:'fecha'    , searchable:false},
      {
        data:null, orderable:false, searchable:false,
        render:d=> d.estado==='Cerrado'
             ? '<span class="badge bg-success">✓ Cerrado</span>'
             : `<button class="btn btn-sm btn-primary btnEditar" data-id="${d.id}">Editar</button>
                <button class="btn btn-sm btn-warning btnCerrar"
                         data-id="${d.id}">Levantar</button>`
      }
    ],
    pageLength:10,
    lengthMenu:[[10,25,50],[10,25,50]],
    order:[[0,'asc']],                 // fecha desc defecto
    /* ---------- detalle expandible (punto 3) ---------- */
    rowCallback: function(row,data){
      // si aún no existe celda “control” la añadimos
      if(!$(row).hasClass('dt-hasChild')){
        $('td:eq(0)',row).addClass('show-details')
          .css('cursor','pointer')
          .attr('title','Ver detalles');
      }
    }
  });

  /* ---------- filtros ----------- */
  $('#btnFiltrar').on('click', ()=> tbl.ajax.reload());

  /* ---------- buscar sólo Código ( enter ) ---------- */
  $('#tblInc_filter input')
      .attr('placeholder','Ejem. COD0123')
      .off()                         // quitamos handler por defecto
      .on('keypress',function(e){
        if(e.which===13){ tbl.search(this.value).draw(); }
      });

  /* ---------- detalle desplegable ---------- */
  $('#tblInc tbody').on('click','td.show-details', function () {
    const tr   = $(this).closest('tr');
    const row  = tbl.row(tr);

    if (row.child.isShown()) {
      row.child.hide(); tr.removeClass('table-active');
    } else {
      /* petición ad-hoc para traer los 4 campos + links img */
      const id = row.data().id;
      fetch(`/api/incidencias/${id}/detalle`)
         .then(r=>r.json())
         .then(j=>{
            const html = `
             <div class="p-3 bg-light">
               <div><strong>Ocurrencia:</strong><br>${j.ocurrencia}</div>
               <div class="mt-2"><strong>Tareas cierre:</strong><br>${j.tareas_cierre||'-'}</div>
               <div class="row mt-2">
                 <div class="col-md-6">
                   <strong>Reporte</strong><br>${j.img_rep||'Sin imágenes'}
                 </div>
                 <div class="col-md-6">
                   <strong>Cierre</strong><br>${j.img_cie||'Sin imágenes'}
                 </div>
               </div>
               <small class="text-muted">
                 Fecha reporte: ${j.f_rep}<br>
                 Fecha levantamiento: ${j.f_cie||'-'}
               </small>
             </div>`;
            row.child(html).show();
            tr.addClass('table-active');
         });
    }
  });

  /* ---------- modal cierre ------- */
  let selID = null;
  $('#tblInc').on('click', '.btnCerrar', function () {
    selID = $(this).data('id');
    $('#lblID').text(`#${selID}`);
    $('#formCierre')[0].reset();
    new bootstrap.Modal('#mdlCierre').show();
  });

  /* ---------- submit cierre (rate-limit lado cliente) ------ */
  $('#formCierre').on('submit', function (e) {
    e.preventDefault();
    const $btn = $('#btnGuardar');
    if($btn.prop('disabled')) return;          // doble-click guardado
    $btn.prop('disabled',true);

    const fd = new FormData(this);
    fetch(`/api/incidencias/${selID}/cerrar`, {method:'POST', body:fd})
      .then(r=>r.json())
      .then(()=>{
          bootstrap.Modal.getInstance('#mdlCierre').hide();
          tbl.ajax.reload(null,false);
      })
      .catch(err=>alert('Error: '+err))
      .finally(()=> $btn.prop('disabled',false));
  });

});

// —————— EDITAR MODAL ——————
let editarID = null;
let edtCodigoTS = null;

$('#tblInc').on('click','.btnEditar', function(){
  editarID = $(this).data('id');
  $('#editID').text('#'+editarID);
  $('#edt_id').val(editarID);

  // 1) Inicializa el select de tipos “estático”
  const $tipo = $('#edt_tipo').empty().append('<option value="">— Seleccione —</option>');
  ELEMENT_TYPES.forEach(t => {
    $tipo.append(`<option value="${t}">${t}</option>`);
  });
  // 1.1) Al cambiar tipo, recarga el TomSelect de códigos
  $tipo.off('change').on('change', function(){
    const tipoVal = this.value;
    if (!tipoVal) {
      edtCodigoTS.clearOptions();
      return;
    }
    // Llamada “sin término” para obtener las primeras 10 sugerencias
    fetch(`/api/autocomplete_codigo?tipo=${encodeURIComponent(tipoVal)}&term=`)
      .then(r => r.json())
      .then(list => {
        edtCodigoTS.clearOptions();
        list.forEach(c => edtCodigoTS.addOption({ codigo: c }));
      });
  });
  // 2) Inicializa TomSelect para el código, si no existe aún
  if (!edtCodigoTS) {
    edtCodigoTS = new TomSelect('#edt_codigo', {
      valueField   : 'codigo',
      labelField   : 'codigo',
      searchField  : 'codigo',
      options      : [],
      create       : false,
      placeholder  : 'Escribe o busca código...',
      maxItems     : 1,
      load: (query, callback) => {
        const tipo = $tipo.val();
        if (!tipo) return callback([]);
        fetch(`/api/autocomplete_codigo?tipo=${encodeURIComponent(tipo)}&term=${encodeURIComponent(query)}`)
          .then(r => r.json())
          .then(list => callback(list.map(c => ({ codigo: c }))))
          .catch(() => callback([]));
      }
    });
  }

  // 3) Abrir modal
  const modalEl = document.getElementById('mdlEditar');
  const modal   = new bootstrap.Modal(modalEl);
  modal.show();

  // 4) Precargar datos del registro
  fetch(`/api/incidencias/${editarID}/detalle`)
    .then(res => res.json())
    .then(d => {
      // 4.1) marca el tipo actual
      $tipo.val(d.tipo_elemento);

      // 4.2) precarga el código en TomSelect
      edtCodigoTS.clearOptions();
      if (d.codigo_elemento) {
        edtCodigoTS.addOption({ codigo: d.codigo_elemento });
        edtCodigoTS.setValue(d.codigo_elemento);
      }
      edtCodigoTS.clearOptions();
      if (d.codigo_elemento) {
        // Como ya recargamos con el cambio de tipo, solo aseguramos la opción actual
        edtCodigoTS.addOption({ codigo: d.codigo_elemento });
        edtCodigoTS.setValue(d.codigo_elemento);
      }
      // 4.3) ocurrecia
      $('#edt_ocurrencia').val(d.ocurrencia);

      // 4.4) preview de evidencias
      const cont = $('#preview_evidencias').empty();
      (d.img_rep || []).forEach(htmlLink => {
        cont.append(`<div>${htmlLink}</div>`);
      });
    });
});

// 5) Submit del modal
$('#formEditar').on('submit', function(e){
  e.preventDefault();
  const fd = new FormData(this);

  // usamos POST porque Flask no parsea bien multipart-forms en PUT
  fetch(`/api/incidencias/${editarID}`, {
    method: 'POST',
    body: fd
  })
  .then(r => {
    if (!r.ok) throw 'Error actualizando';
    return r.json();
  })
  .then(() => {
    bootstrap.Modal.getInstance(document.getElementById('mdlEditar')).hide();
    tbl.ajax.reload(null, false);
  })
  .catch(err => alert(err));
});
