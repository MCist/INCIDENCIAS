// app/static/js/dashboard.js

document.addEventListener('DOMContentLoaded', ()=>{

  const fArea = $('#fArea'),
        fAli  = $('#fAli'),
        fCrit = $('#fCrit'),
        fEst  = $('#fEst'),
        fAnt  = $('input[name="fAnt"]');  // nuevo grupo de radios

  // poblar alimentadores
  fetch('/api/incidencias/alimentadores')
    .then(r=>r.json())
    .then(list=>{
      list.forEach(o=>
        fAli.append(`<option value="${o.value}">${o.label}</option>`)
      );
    });

  // contexts para gráficos
  const ctxAlim = document.getElementById('chartAlimentador').getContext('2d');
  const ctxTipo = document.getElementById('chartPorTipo')?.getContext('2d');
  const ctxMttr = document.getElementById('chartMttrTipo')?.getContext('2d');
  let chartAlim, chartTipo, chartMttr;

  function reload() {
    const params = new URLSearchParams({
      area:        fArea.val(),
      alimentador: fAli.val(),
      criticidad: fCrit.val(),
      estado:      fEst.val(),
      antiguedad:  fAnt.filter(':checked').val()  // enviamos el nuevo filtro
    });

    fetch(`/api/dashboard?${params}`)
      .then(r=>r.json())
      .then(data=>{
        // ── KPIs ─────────────────────
        $('#kpi-total').text(data.kpi.total);
        $('#kpi-ratio').text(`${data.kpi.abierto} / ${data.kpi.cerrado}`);
        $('#kpi-mttr').text(data.kpi.mttr_h);
        $('#kpi-crit').html(
          Object.entries(data.kpi.criticidad)
                .map(([lvl,c])=> `<small>${lvl}: ${c}</small>`).join(' ')
        );

        // ── GLOBAL vs ÚNICO ALIMENTADOR ─────────────────
        if (!fAli.val()) {
          // Modo global: mostrar sólo el chartAlim
          $('#container-por-tipo').hide();
          $('#chartAlimentador').parent().show();

          const { labels, datasets } = data.por_alimentador;
          if (chartAlim) {
            chartAlim.data.labels   = labels;
            chartAlim.data.datasets = datasets;
            chartAlim.update();
          } else {
            chartAlim = new Chart(ctxAlim, {
              type: 'bar',
              data: { labels, datasets },
              options: {
                maintainAspectRatio: false,
                scales: {
                  x: { stacked: true },
                  y: {
                    stacked: true,
                    beginAtZero: true,
                    ticks: { stepSize: 1 }
                  }
                },
                plugins: { legend: { position: 'top' } }
              }
            });
          }

        } else {
          // Modo único alimentador: ocultar global, mostrar por-tipo + mttr
          $('#chartAlimentador').parent().hide();
          $('#container-por-tipo').show();

          // — distribución por tipo
          const { labels: lt, datasets: dsT } = data.por_tipo;
          if (chartTipo) {
            chartTipo.data.labels   = lt;
            chartTipo.data.datasets = dsT;
            chartTipo.update();
          } else {
            chartTipo = new Chart(ctxTipo, {
              type: 'doughnut',
              data: { labels: lt, datasets: dsT },
              options: {
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
              }
            });
          }

          // — MTTR por tipo
          const { labels: lm, datasets: dsM } = data.mttr_por_tipo;
          if (chartMttr) {
            chartMttr.data.labels   = lm;
            chartMttr.data.datasets = dsM;
            chartMttr.update();
          } else {
            chartMttr = new Chart(ctxMttr, {
              type: 'bar',
              data: { labels: lm, datasets: dsM },
              options: {
                maintainAspectRatio: false,
                scales: {
                  y: {
                    beginAtZero: true,
                    ticks: { stepSize: 1 }
                  }
                },
                plugins: { legend: { display: false } }
              }
            });
          }
        }
      });
  }

  // disparar cada vez que cambie cualquier filtro
  [fArea, fAli, fCrit, fEst, fAnt].forEach($grp =>
    $grp.on('change', reload)
  );

  reload();
});
