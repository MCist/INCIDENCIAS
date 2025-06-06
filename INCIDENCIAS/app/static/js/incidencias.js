/*  app/static/js/incidencias.js – Incidencias lista · filtros · edición · cierre  */
/*  (jun-2025)                                                                    */

/* ------------------------------------------------------------------ */
/* 1.   Tabla + filtros                                               */
/* ------------------------------------------------------------------ */

const ELEMENT_TYPES = [
  'Proteccion/Control',
  'Subestacion',
  'Subestación de potencia',
  'Suministro',
  'Estructura MT',
  'Vano'
];

let tbl;          // DataTable global
$(function () {
  /* ----------------------------------------------------------------
   * 1-A.   Combos rápidos (alimentadores y tipo de elemento)
   * ---------------------------------------------------------------- */
  const $selAli   = $('#fAli');
  const $selTipoE = $('#fTipoEl');

  // • Alimentadores (desde API)
  fetch('/api/incidencias/alimentadores')
    .then(r => r.json())
    .then(arr => {
      arr.forEach(o => $selAli.append(
        `<option value="${o.value}">${o.label}</option>`
      ));
    });
  // • Tipos de elemento (estático; multiselección con TomSelect)
  ELEMENT_TYPES.forEach(t =>
    $selTipoE.append(`<option value="${t}">${t}</option>`)
  );
  /* ----------------------------------------------------------------
   * 1-B.   Inicializar DataTable
   * ---------------------------------------------------------------- */
  tbl = $('#tblInc').DataTable({
    language : { processing:'<div class="spinner-border text-primary"></div>',
                 search:'Buscar código&nbsp:' },
    dom      : 'frtip',
    processing: true,
    serverSide: true,
    pageLength: 10,
    order    : [[0,'asc']],
    ajax: {
      url : '/api/incidencias/data',
      data: d => {
        /* filtros */
        d.estado  = $('#fEstado').val();
        d.ali     = $selAli.val();
        d.crit    = $('#fCrit').val();
        d.f_ini   = $('#fIni').val();
        d.f_fin   = $('#fFin').val();
        const t   = $selTipoE.val();              // TomSelect => array | null
        d.tipo_el = Array.isArray(t) ? t.join(',') : (t||'');

        /* ordenamiento (traducimos índice→columna BD) */
        if (d.order?.length) {
          const idx = d.order[0].column, dir = d.order[0].dir,
                map = ['id','codigo','ali','desc','area','tipo','criticidad','estado','fecha_ocurrencia'];
          d.order_col = map[idx]; d.order_dir = dir;
        }
      }
    },
    columns: [
      {data:'id'}, {data:'codigo', searchable:true},
      {data:'ali'}, {data:'desc'}, {data:'area'}, {data:'tipo'},
      {data:'criticidad', render:v=>{
        const pct = Math.round(v*100);
        const lvl = v>=0.85?'alta':v>=0.7?'media':v>=0.5?'baja':'leve';
        const col = {alta:'#dc3545',media:'#fd7e14',baja:'#ffc107',leve:'#198754'}[lvl];
        return `<div class="progress" style="height:8px">
                  <div class="progress-bar" style="width:${pct}%;background:${col}"
                       title="${lvl} – ${pct}%"></div></div>`;
      }},
      {data:'estado'}, {data:'fecha_ocurrencia', searchable:false},
      {data:null, orderable:false, render:d=>
        d.estado==='Cerrado'
        ? '<span class="badge bg-success">✓ Cerrado</span>'
        : `<button class="btn btn-sm btn-primary btnEditar" data-id="${d.id}">Editar</button>
           <button class="btn btn-sm btn-warning btnCerrar" data-id="${d.id}">Levantar</button>`
      }
    ],
    rowCallback: (row)=>{
      if (!$(row).hasClass('dt-hasChild')) {
        $('td:eq(0)',row).addClass('show-details')
          .css('cursor','pointer')
          .attr('title','Ver detalles');
      }
    },
    drawCallback: function(){
      /* resumen por tipo – didáctico */
      const stats = this.api().rows({search:'applied'}).data().toArray()
        .reduce((m,r)=>{ m[r.tipo]=(m[r.tipo]||0)+1; return m; }, {});
      $('#statsTipos').html(
        Object.entries(stats)
          .map(([k,v])=>`<span class="badge bg-secondary me-1">${k}: ${v}</span>`)
          .join('')
      );
    }
  });

  /* ------ listeners que recargan la tabla ------ */
  [
    '#fEstado', '#fAli', '#fCrit', '#fIni', '#fFin', '#fTipoEl'
  ].forEach(sel => $(sel).on('change', () => tbl.ajax.reload()));

  $('#btnFiltrar').on('click', ()=> tbl.ajax.reload());

  /* buscar sólo al pulsar ENTER */
  $('#tblInc_filter input')
    .attr('placeholder','Ejem. COD0123')
    .off()
    .on('keypress', function(e){ if(e.which===13) tbl.search(this.value).draw(); });

  /* ----------------------------------------------------------------
   * 1-C.   Fila detalle (child)
   * ---------------------------------------------------------------- */
  $('#tblInc tbody').on('click','td.show-details', function(){
    const tr=$(this).closest('tr'), row=tbl.row(tr);
    if(row.child.isShown()){ row.child.hide(); tr.removeClass('table-active'); }
    else{
      fetch(`/api/incidencias/${row.data().id}/detalle`)
        .then(r=>r.json())
        .then(j=>{
          row.child(`
            <div class="p-3 bg-light">
              <div><strong>Ocurrencia:</strong><br>${j.ocurrencia}</div>
              <div class="mt-2"><strong>Tareas cierre:</strong><br>${j.tareas_cierre||'-'}</div>
              <div class="row mt-2">
                <div class="col-md-6"><strong>Reporte</strong><br>${j.img_rep||'Sin imágenes'}</div>
                <div class="col-md-6"><strong>Cierre</strong><br>${j.img_cie||'Sin imágenes'}</div>
              </div>
              <small class="text-muted">
                Fecha ocurrencia: ${j.f_ocu}<br>Fecha levantamiento: ${j.f_cie||'-'}
              </small>
            </div>`).show();
          tr.addClass('table-active');
        });
    }
  });

  /* ----------------------------------------------------------------
   * 1-D.   Modal LEVANTAR / cierre
   * ---------------------------------------------------------------- */
  let selID = null;
  $('#tblInc').on('click', '.btnCerrar', function(){
    selID = $(this).data('id');
    $('#lblID').text(`#${selID}`);
    $('#formCierre')[0].reset();
    new bootstrap.Modal('#mdlCierre').show();
  });

  $('#formCierre').on('submit', function(e){
    e.preventDefault();
    const $btn = $('#btnGuardar');
    if ($btn.prop('disabled')) return;
    $btn.prop('disabled', true);
    fetch(`/api/incidencias/${selID}/cerrar`, {method:'POST', body:new FormData(this)})
      .then(r=>r.json())
      .then(()=>{
        bootstrap.Modal.getInstance('#mdlCierre').hide();
        tbl.ajax.reload(null,false);
      })
      .catch(err=>alert('Error: '+err))
      .finally(()=> $btn.prop('disabled',false));
  });

});  // jQuery ready


/* ------------------------------------------------------------------
 * 2.   Modal de EDICIÓN
 * ------------------------------------------------------------------ */
let editarID=null, edtCodigoTS=null, tsIniEdit=null, tsFinEdit=null;

const grupoEditVano   = $('#grupo_editar_vano');
const grupoEditCodigo = $('#grupo_editar_codigo_unico');

$('#tblInc').on('click','.btnEditar', function(){
  editarID = $(this).data('id');
  $('#editID').text('#'+editarID);
  $('#edt_id').val(editarID);

  /* ---- (re)llenar select tipo ---- */
  const $tipo = $('#edt_tipo').empty().append('<option value="">— Seleccione —</option>');
  ELEMENT_TYPES.forEach(t => $tipo.append(`<option value="${t}">${t}</option>`));

  /* ---- TomSelect código único ---- */
  if (!edtCodigoTS){
    edtCodigoTS = new TomSelect('#edt_codigo',{
      valueField:'codigo', labelField:'codigo', searchField:'codigo',
      options:[], create:false, placeholder:'Escribe o busca código...', maxItems:1,
      load:(q,cb)=>{
        const t=$tipo.val(); if(!t) return cb([]);
        fetch(`/api/autocomplete_codigo?tipo=${encodeURIComponent(t)}&term=${encodeURIComponent(q)}`)
          .then(r=>r.json()).then(list=>cb(list.map(c=>({codigo:c}))))
          .catch(()=>cb([]));
      }
    });
  }

  /* ---- TomSelect inicio / fin (Vano) ---- */
  if (!tsIniEdit){
    const cfg={valueField:'codigo',labelField:'codigo',searchField:'codigo',
               create:false, preload:'focus',
               load:(q,cb)=>{
                 fetch(`/api/autocomplete_codigo?tipo=Estructura%20MT&term=${encodeURIComponent(q)}`)
                   .then(r=>r.json()).then(arr=>cb(arr.map(c=>({codigo:c}))))
                   .catch(()=>cb([]));
               }};
    tsIniEdit = new TomSelect('#edt_ini', cfg);
    tsFinEdit = new TomSelect('#edt_fin', cfg);
  }

  /* ---- mostrar grupo adecuado ---- */
  $tipo.off('change').on('change', function(){
    if (this.value==='Vano') { grupoEditCodigo.hide(); grupoEditVano.show(); }
    else                     { grupoEditVano.hide();  grupoEditCodigo.show(); }
    edtCodigoTS.clear(); tsIniEdit.clear(); tsFinEdit.clear();
  });

  /* ---- abrir modal ---- */
  new bootstrap.Modal('#mdlEditar').show();

  /* ---- precargar registro ---- */
  fetch(`/api/incidencias/${editarID}/detalle`)
    .then(r=>r.json())
    .then(d=>{
      $tipo.val(d.tipo_elemento).trigger('change');
      $('#edt_ocurrencia').val(d.ocurrencia||'');

      if (d.tipo_elemento==='Vano'){
        const [ini='',fin=''] = (d.codigo_elemento||'').split('–').map(s=>s.trim());
        if (ini){ tsIniEdit.addOption({codigo:ini}); tsIniEdit.setValue(ini); }
        if (fin){ tsFinEdit.addOption({codigo:fin}); tsFinEdit.setValue(fin); }
      }else if (d.codigo_elemento){
        edtCodigoTS.addOption({codigo:d.codigo_elemento});
        edtCodigoTS.setValue(d.codigo_elemento);
      }

      const cont=$('#preview_evidencias').empty();
      (d.img_rep||[]).forEach(h=>cont.append(`<div>${h}</div>`));
    });
});

/* ---- submit edición ---- */
$('#formEditar').on('submit', function(e){
  e.preventDefault();

  const tipo = $('#edt_tipo').val().trim();
  const ocur = $('#edt_ocurrencia').val().trim();
  if (!tipo || !ocur){
    alert('Tipo de elemento y ocurrencia son obligatorios.'); return;
  }

  const fd = new FormData(this);

  if (tipo==='Vano'){
    const ini=tsIniEdit.getValue(), fin=tsFinEdit.getValue();
    if (!ini || !fin){
      alert('Debe indicar código inicio y fin.'); return;
    }
    fd.set('tipo_elemento','Vano');
    fd.set('codigo_inicio',ini); fd.set('codigo_fin',fin);
    fd.delete('codigo_elemento');              // no aplica
  }else{
    const codigo=$('#edt_codigo').val().trim();
    if (!codigo){
      alert('Código del elemento es obligatorio.'); return;
    }
    fd.set('codigo_elemento',codigo);
  }

  fetch(`/api/incidencias/${editarID}`, {method:'POST', body:fd})
    .then(r=>{ if(!r.ok) throw 'Error actualizando'; return r.json(); })
    .then(()=>{
      bootstrap.Modal.getInstance('#mdlEditar').hide();
      tbl.ajax.reload(null,false);
    })
    .catch(err=>alert(err));
});
