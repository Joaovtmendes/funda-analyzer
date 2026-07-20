"""Gera o dashboard HTML com o ranking de imóveis.

Produz um único arquivo .html autocontido (abre em qualquer navegador, sem
servidor). Usa Plotly (via CDN) para um gráfico interativo e uma tabela
ordenável. O template fica embutido aqui com Jinja2 para o projeto continuar
sendo de arquivo único e fácil de mover.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from ..models import ScoredListing

_TEMPLATE = Template(
    """<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="utf-8">
<title>Funda Analyzer — Ranking</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
  :root { --bg:#0f1720; --card:#17212b; --ink:#e6edf3; --muted:#8b98a5; --accent:#3fb950; }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--bg); color:var(--ink);
         font-family: -apple-system, Segoe UI, Roboto, sans-serif; }
  header { padding:24px 32px; border-bottom:1px solid #212c38; }
  h1 { margin:0; font-size:20px; }
  .sub { color:var(--muted); font-size:13px; margin-top:4px; }
  .wrap { padding:24px 32px; }
  #chart { background:var(--card); border-radius:12px; padding:8px; margin-bottom:24px; }
  table { width:100%; border-collapse:collapse; background:var(--card); border-radius:12px; overflow:hidden; }
  th, td { padding:10px 12px; text-align:left; font-size:13px; border-bottom:1px solid #212c38; }
  th { background:#1c2732; cursor:pointer; user-select:none; position:sticky; top:0; }
  th:hover { color:var(--accent); }
  tr:hover td { background:#1c2732; }
  .score { font-weight:700; color:var(--accent); }
  .num { text-align:right; font-variant-numeric: tabular-nums; }
  a { color:#58a6ff; text-decoration:none; }
  .badge { display:inline-block; background:#21323f; color:#9fd6ff; border-radius:6px;
           padding:2px 6px; font-size:11px; margin:1px; }
  .reno { display:inline-block; border-radius:6px; padding:2px 8px; font-size:11px;
          font-weight:600; text-transform:capitalize; }
  .reno-baixo { background:#132e1c; color:#3fb950; }
  .reno-medio { background:#332a12; color:#d6a23f; }
  .reno-alto  { background:#3a1a1a; color:#f07171; }
  .src { display:inline-block; background:#2a2136; color:#c9a9ff; border-radius:6px;
         padding:1px 6px; font-size:10px; margin-left:6px; vertical-align:middle; }
  .filters { display:flex; gap:12px; align-items:end; flex-wrap:wrap; margin-bottom:20px; }
  .filters label { display:flex; flex-direction:column; font-size:11px; color:var(--muted); gap:4px; }
  .filters select, .filters input { background:#0f1720; color:var(--ink); border:1px solid #2a3742;
      border-radius:8px; padding:7px 9px; font-size:13px; min-width:130px; }
  .filters button { background:#21323f; color:#9fd6ff; border:1px solid #2a3742; border-radius:8px;
      padding:8px 12px; font-size:13px; cursor:pointer; }
  .filters button:hover { background:#283a48; }
  #tbl tbody tr { cursor:pointer; }
  /* seção de ajuda */
  .help { background:var(--card); border:1px solid #212c38; border-radius:12px; padding:0 16px; margin-bottom:20px; }
  .help summary { cursor:pointer; padding:14px 0; font-weight:600; color:#9fd6ff; list-style:none; }
  .help summary::-webkit-details-marker { display:none; }
  .help summary::before { content:'ⓘ '; }
  .help-body { padding:0 0 16px; font-size:13px; color:var(--ink); line-height:1.6; }
  .help-body h4 { margin:14px 0 6px; font-size:13px; color:var(--accent); }
  .help-body dl { display:grid; grid-template-columns:auto 1fr; gap:4px 12px; margin:0; }
  .help-body dt { color:#9fd6ff; white-space:nowrap; }
  .help-body dd { margin:0; color:var(--muted); }
  /* modal de detalhes */
  .modal { display:none; position:fixed; inset:0; background:#000a; z-index:50;
           align-items:center; justify-content:center; padding:20px; }
  .modal.open { display:flex; }
  .modal-card { background:var(--card); border:1px solid #2a3742; border-radius:14px;
                max-width:640px; width:100%; max-height:88vh; overflow:auto; padding:22px 24px; position:relative; }
  .modal-x { position:absolute; top:12px; right:14px; background:none; border:none; color:var(--muted);
             font-size:26px; cursor:pointer; line-height:1; }
  .modal-x:hover { color:var(--ink); }
  .modal h2 { margin:0 6px 2px 0; font-size:19px; }
  .modal .msub { color:var(--muted); font-size:13px; margin-bottom:16px; }
  .mgrid { display:grid; grid-template-columns:1fr 1fr; gap:10px 20px; }
  .mgrid .cell { display:flex; flex-direction:column; gap:2px; }
  .mgrid .k { font-size:11px; color:var(--muted); }
  .mgrid .v { font-size:15px; font-weight:600; }
  .bar-row { display:flex; align-items:center; gap:8px; margin:5px 0; font-size:12px; }
  .bar-row .bl { width:120px; color:var(--muted); }
  .bar-track { flex:1; background:#0f1720; border-radius:6px; height:8px; overflow:hidden; }
  .bar-fill { height:100%; background:var(--accent); }
  .mphoto { width:100%; border-radius:10px; margin:14px 0; object-fit:cover; max-height:240px; }
  .mopen { display:inline-block; margin-top:14px; background:#21323f; color:#9fd6ff; padding:9px 14px;
           border-radius:8px; font-size:13px; }
</style>
</head>
<body>
<header>
  <h1>Funda Analyzer — Potencial de compra</h1>
  <div class="sub"><span id="vcount">{{ count }}</span> de {{ count }} imóveis · gerado em {{ generated }} · fonte: {{ source }}</div>
</header>
<div class="wrap">
  <div class="filters">
    <label>Cidade
      <select id="fCity"><option value="">Todas</option>
      {% for c in cities %}<option value="{{ c|lower }}">{{ c }}</option>{% endfor %}
      </select>
    </label>
    <label>Preço mín (€)<input id="fMin" type="number" placeholder="0"></label>
    <label>Preço máx (€)<input id="fMax" type="number" placeholder="sem limite"></label>
    <button id="fReset">Limpar filtros</button>
  </div>

  <details class="help">
    <summary>Como ler este relatório (score e colunas)</summary>
    <div class="help-body">
      <p>O <b>Score</b> (0–100) mede o <b>potencial de compra</b>: quanto maior, mais o imóvel
      parece barato frente às avaliações e ao mercado. Ele combina cinco sinais, com estes pesos:</p>
      <dl>
        <dt>Preço vs WOZ — {{ w.woz }}%</dt><dd>preço pedido abaixo da avaliação fiscal (WOZ)</dd>
        <dt>Preço vs vendas — {{ w.sales }}%</dt><dd>preço abaixo de vendas reais comparáveis (Kadaster)</dd>
        <dt>Preço/m² — {{ w.ppm2 }}%</dt><dd>preço por m² abaixo da mediana do BAIRRO (código postal)</dd>
        <dt>Tempo no mercado — {{ w.days }}%</dt><dd>imóvel parado há mais tempo = mais margem de negociação</dd>
        <dt>Label energético — {{ w.energy }}%</dt><dd>eficiência energética (A melhor, G pior)</dd>
      </dl>
      <h4>Colunas da tabela</h4>
      <dl>
        <dt>Preço €</dt><dd>preço pedido no Funda</dd>
        <dt>€/m²</dt><dd>preço dividido pela área habitável</dd>
        <dt>vs Bairro</dt><dd>€/m² do imóvel ÷ mediana do bairro (PC4). Abaixo de 100% = mais barato que a vizinhança</dd>
        <dt>WOZ €</dt><dd>avaliação fiscal oficial (hoje estimada)</dd>
        <dt>Venda ref. €</dt><dd>mediana de vendas reais comparáveis, Kadaster (hoje estimada)</dd>
        <dt>Preço/Venda</dt><dd>preço ÷ venda de referência. Abaixo de 100% = abaixo do mercado</dd>
        <dt>Preço/WOZ</dt><dd>preço ÷ WOZ. Abaixo de 100% = abaixo da avaliação fiscal</dd>
        <dt>Reforma</dt><dd>esforço estimado de reforma: baixo / médio / alto</dd>
        <dt>Destaques</dt><dd>bandeiras que puxaram o score (ex.: abaixo do WOZ, dias no mercado)</dd>
      </dl>
      <p style="color:var(--muted)">Dica: clique em qualquer imóvel na tabela para ver todos os dados coletados dele.</p>
    </div>
  </details>

  <div id="chart"></div>
  <table id="tbl">
    <thead><tr>
      <th data-i="0">#</th>
      <th data-i="1" class="num">Score</th>
      <th data-i="2">Endereço</th>
      <th data-i="3" class="num">Preço €</th>
      <th data-i="4" class="num">€/m²</th>
      <th data-i="5" class="num">vs Bairro</th>
      <th data-i="6" class="num">WOZ €</th>
      <th data-i="7" class="num">Venda ref. €</th>
      <th data-i="8" class="num">Preço/Venda</th>
      <th data-i="9" class="num">Preço/WOZ</th>
      <th data-i="10">Reforma</th>
      <th data-i="11">Destaques</th>
    </tr></thead>
    <tbody>
    {% for r in rows %}
      <tr data-city="{{ r.city|lower }}" data-price="{{ r.price_num }}" data-idx="{{ loop.index0 }}" onclick="openModal(this.dataset.idx)">
        <td class="num">{{ loop.index }}</td>
        <td class="num score">{{ r.score }}</td>
        <td><a href="{{ r.url }}" target="_blank" onclick="event.stopPropagation()">{{ r.address }}</a>
            <span class="src">{{ r.source }}</span></td>
        <td class="num">{{ r.price }}</td>
        <td class="num">{{ r.ppm2 }}</td>
        <td class="num">{{ r.nb_pct }}</td>
        <td class="num">{{ r.woz }}</td>
        <td class="num">{{ r.kadaster }}</td>
        <td class="num">{{ r.pct_sales }}</td>
        <td class="num">{{ r.pct }}</td>
        <td><span class="reno reno-{{ r.reno_effort }}">{{ r.reno_effort }}</span></td>
        <td>{% for n in r.notes %}<span class="badge">{{ n }}</span>{% endfor %}</td>
      </tr>
    {% endfor %}
    </tbody>
  </table>
</div>

<div id="modal" class="modal" onclick="if(event.target===this)closeModal()">
  <div class="modal-card">
    <button class="modal-x" onclick="closeModal()">&times;</button>
    <div id="modal-body"></div>
  </div>
</div>

<script>
  // Todos os dados coletados de cada imóvel (para o painel de detalhes)
  var details = {{ details|safe }};

  function cell(k, v){ return v==null||v===''||v==='-' ? '' :
    '<div class="cell"><span class="k">'+k+'</span><span class="v">'+v+'</span></div>'; }
  function bar(label, val){
    var w = Math.max(0, Math.min(100, val||0));
    return '<div class="bar-row"><span class="bl">'+label+'</span>'
      + '<span class="bar-track"><span class="bar-fill" style="width:'+w+'%"></span></span>'
      + '<span>'+Math.round(val||0)+'</span></div>';
  }
  function openModal(idx){
    var d = details[idx]; if(!d) return;
    var h = '<h2>'+d.address+'</h2>'
      + '<div class="msub">'+(d.city||'')+(d.postal_code?' · '+d.postal_code:'')+' · fonte: '+d.source+'</div>';
    if(d.photo) h += '<img class="mphoto" src="'+d.photo+'" alt="" onerror="this.remove()">';
    h += '<div class="mgrid">'
      + cell('Preço', d.price)
      + cell('Área', d.area_m2!=null? d.area_m2+' m²':'')
      + cell('Preço/m²', d.price_per_m2)
      + cell('Mediana do bairro (€/m²)', d.nb_median)
      + cell('€/m² vs bairro', d.nb_pct)
      + cell('Quartos', d.rooms)
      + cell('Dormitórios', d.bedrooms)
      + cell('Ano de construção', d.year_built)
      + cell('Label energético', d.energy_label)
      + cell('WOZ (fiscal)', d.woz)
      + cell('Venda ref. (Kadaster)', d.kadaster)
      + cell('Preço/WOZ', d.pct_woz)
      + cell('Preço/Venda', d.pct_sales)
      + cell('Reforma', d.reno_effort)
      + '</div>';
    h += '<h4 style="color:var(--accent);margin:18px 0 6px;font-size:13px">Composição do score — '+d.score+'</h4>';
    h += bar('Preço vs WOZ', d.sc_woz) + bar('Preço vs vendas', d.sc_sales)
       + bar('Preço/m²', d.sc_ppm2) + bar('Tempo no mercado', d.sc_days)
       + bar('Label energético', d.sc_energy);
    if(d.reno_summary) h += '<p style="color:var(--muted);font-size:13px;margin-top:12px">'+d.reno_summary+'</p>';
    if(d.notes && d.notes.length) h += '<div style="margin-top:8px">'
       + d.notes.map(function(n){return '<span class="badge">'+n+'</span>';}).join(' ') + '</div>';
    h += '<a class="mopen" href="'+d.url+'" target="_blank">Abrir no Funda ↗</a>';
    document.getElementById('modal-body').innerHTML = h;
    document.getElementById('modal').classList.add('open');
  }
  function closeModal(){ document.getElementById('modal').classList.remove('open'); }
  document.addEventListener('keydown', function(e){ if(e.key==='Escape') closeModal(); });

  // Gráfico: preço/m² (x) vs score (y), tamanho = área. Redesenha conforme o filtro.
  var chartData = {{ chart_data|safe }};
  function drawChart(mask){
    var x=[],y=[],t=[],a=[];
    for(var i=0;i<chartData.score.length;i++){
      if(mask && !mask(chartData.city[i], chartData.price[i])) continue;
      x.push(chartData.ppm2[i]); y.push(chartData.score[i]);
      t.push(chartData.labels[i]); a.push(chartData.area[i]);
    }
    Plotly.react('chart', [{
      x:x, y:y, text:t, mode:'markers',
      marker:{ size:a, sizemode:'area', sizeref:0.5, color:y, colorscale:'YlGn',
               showscale:true, colorbar:{title:'Score'} },
      type:'scatter', hovertemplate:'%{text}<br>€/m²: %{x}<br>Score: %{y}<extra></extra>'
    }], {
      paper_bgcolor:'#17212b', plot_bgcolor:'#17212b', font:{color:'#e6edf3'},
      margin:{t:20,r:20,b:50,l:50}, height:380,
      xaxis:{title:'Preço por m² (€)', gridcolor:'#212c38'},
      yaxis:{title:'Score de potencial', gridcolor:'#212c38'}
    }, {displayModeBar:false, responsive:true});
  }

  // Filtros de cidade e faixa de preço (client-side, sem recoletar)
  var fCity=document.getElementById('fCity'),
      fMin=document.getElementById('fMin'),
      fMax=document.getElementById('fMax');
  function applyFilters(){
    var city=fCity.value, mn=parseFloat(fMin.value), mx=parseFloat(fMax.value);
    var mask=function(c,p){
      if(city && c!==city) return false;
      if(!isNaN(mn) && p<mn) return false;
      if(!isNaN(mx) && p>mx) return false;
      return true;
    };
    var tb=document.querySelector('#tbl tbody'), shown=0;
    [].slice.call(tb.rows).forEach(function(r){
      var ok=mask(r.dataset.city, +r.dataset.price);
      r.style.display = ok?'':'none'; if(ok) shown++;
    });
    document.getElementById('vcount').innerText=shown;
    drawChart(mask);
  }
  [fCity,fMin,fMax].forEach(function(el){ el.addEventListener('input', applyFilters); });
  document.getElementById('fReset').addEventListener('click', function(){
    fCity.value=''; fMin.value=''; fMax.value=''; applyFilters();
  });

  drawChart(null); // desenho inicial (sem filtro)

  // Ordenação de tabela ao clicar no cabeçalho
  document.querySelectorAll('#tbl th').forEach(function(th){
    th.addEventListener('click', function(){
      var tb=document.querySelector('#tbl tbody'), i=+th.dataset.i;
      var rows=[].slice.call(tb.rows);
      var asc=th._asc=!th._asc;
      rows.sort(function(a,b){
        var x=a.cells[i].innerText.replace(/[^0-9.\\-]/g,''),
            y=b.cells[i].innerText.replace(/[^0-9.\\-]/g,'');
        var nx=parseFloat(x), ny=parseFloat(y);
        if(!isNaN(nx)&&!isNaN(ny)) return asc?nx-ny:ny-nx;
        return asc?a.cells[i].innerText.localeCompare(b.cells[i].innerText)
                  :b.cells[i].innerText.localeCompare(a.cells[i].innerText);
      });
      rows.forEach(function(r){tb.appendChild(r);});
    });
  });
</script>
</body>
</html>"""
)


def _fmt(n) -> str:
    return f"{n:,.0f}".replace(",", ".") if n is not None else "-"


def build_dashboard(items: list[ScoredListing], out_path: str | Path,
                    source: str = "mock", scoring=None) -> Path:
    rows, details = [], []
    chart = {"ppm2": [], "score": [], "area": [], "labels": [], "city": [], "price": []}
    for s in items:
        l = s.listing
        rows.append({
            "score": f"{s.score:.0f}",
            "url": l.url,
            "address": l.address,
            "city": l.city or "",
            "price_num": l.price or 0,
            "price": _fmt(l.price),
            "ppm2": _fmt(l.price_per_m2),
            "nb_pct": f"{s.ppm2_vs_neighborhood_pct:.0f}%" if s.ppm2_vs_neighborhood_pct else "-",
            "woz": _fmt(s.woz.woz_value if s.woz else None),
            "kadaster": _fmt(s.kadaster_median),
            "pct_sales": f"{s.price_vs_sales_pct:.0f}%" if s.price_vs_sales_pct else "-",
            "pct": f"{s.price_vs_woz_pct:.0f}%" if s.price_vs_woz_pct else "-",
            "source": l.source,
            "reno_effort": s.renovation.effort if s.renovation else "-",
            "notes": (s.renovation.flags[:2] if s.renovation else []) + s.notes[:2],
        })
        # dados completos para o painel de detalhes (ao clicar no imóvel)
        details.append({
            "address": l.address,
            "url": l.url,
            "source": l.source,
            "city": l.city,
            "postal_code": l.postal_code,
            "price": _fmt(l.price) + " €" if l.price else None,
            "area_m2": l.area_m2,
            "price_per_m2": (_fmt(l.price_per_m2) + " €") if l.price_per_m2 else None,
            "rooms": l.rooms,
            "bedrooms": l.bedrooms,
            "year_built": l.year_built,
            "energy_label": l.energy_label,
            "neighborhood": l.postal_code[:4] if l.postal_code else None,
            "nb_median": (_fmt(s.neighborhood_ppm2_median) + " €/m²") if s.neighborhood_ppm2_median else None,
            "nb_pct": f"{s.ppm2_vs_neighborhood_pct:.0f}%" if s.ppm2_vs_neighborhood_pct else None,
            "woz": (_fmt(s.woz.woz_value) + " €") if (s.woz and s.woz.woz_value) else None,
            "kadaster": (_fmt(s.kadaster_median) + " €") if s.kadaster_median else None,
            "pct_woz": f"{s.price_vs_woz_pct:.0f}%" if s.price_vs_woz_pct else None,
            "pct_sales": f"{s.price_vs_sales_pct:.0f}%" if s.price_vs_sales_pct else None,
            "score": f"{s.score:.0f}",
            "sc_woz": round(s.score_price_vs_woz),
            "sc_sales": round(s.score_price_vs_sales),
            "sc_ppm2": round(s.score_price_per_m2),
            "sc_days": round(s.score_days_on_market),
            "sc_energy": round(s.score_energy_label),
            "reno_effort": s.renovation.effort if s.renovation else None,
            "reno_summary": s.renovation.summary if s.renovation else None,
            "notes": (s.renovation.flags if s.renovation else []) + s.notes,
            "photo": l.photos[0] if l.photos else None,
        })
        if l.price_per_m2:
            chart["ppm2"].append(l.price_per_m2)
            chart["score"].append(s.score)
            chart["area"].append(l.area_m2 or 60)
            chart["labels"].append(l.address)
            chart["city"].append((l.city or "").lower())
            chart["price"].append(l.price or 0)

    # pesos do score (em %), para a seção de ajuda
    if scoring is not None:
        w = {
            "woz": round(scoring.weight_price_vs_woz * 100),
            "sales": round(scoring.weight_price_vs_sales * 100),
            "ppm2": round(scoring.weight_price_per_m2 * 100),
            "days": round(scoring.weight_days_on_market * 100),
            "energy": round(scoring.weight_energy_label * 100),
        }
    else:
        w = {"woz": 30, "sales": 25, "ppm2": 25, "days": 12, "energy": 8}

    cities = sorted({s.listing.city for s in items if s.listing.city})
    html = _TEMPLATE.render(
        rows=rows,
        details=json.dumps(details, ensure_ascii=False),
        w=w,
        cities=cities,
        count=len(items),
        generated=datetime.now().strftime("%d/%m/%Y %H:%M"),
        source=source,
        chart_data=json.dumps(chart),
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
    return out_path
