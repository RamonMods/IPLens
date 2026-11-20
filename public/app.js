/* --- IPLens: consulta de IP e montagem do dossiê. --- */

const form = document.getElementById("form-busca");
const campoIp = document.getElementById("ip");
const aviso = document.getElementById("aviso");
const carregando = document.getElementById("carregando");
const resultado = document.getElementById("resultado");
const cards = document.getElementById("cards");
const jsonResultado = document.getElementById("json-resultado");
const botao = form.querySelector("button[type=submit]");

function escapar(valor) {
  return String(valor === null || valor === undefined ? "" : valor)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function texto(valor, vazio = "—") {
  return valor === null || valor === undefined || valor === "" ? vazio : String(valor);
}

function linha(rotulo, valor, classe) {
  return '<div class="linha"><span>' + escapar(rotulo) + "</span><span"
    + (classe ? ' class="' + classe + '"' : "") + ">" + escapar(texto(valor)) + "</span></div>";
}

function simNao(valor) {
  return valor ? "sim" : "não";
}

function cartao(titulo, linhas) {
  return '<article class="cartao"><h4>' + escapar(titulo) + "</h4>" + linhas.join("") + "</article>";
}

function valorTexto(valor) {
  if (valor === null || valor === undefined || valor === "") return "";
  if (typeof valor === "object") {
    try { return JSON.stringify(valor); } catch (e) { return String(valor); }
  }
  return String(valor);
}

let mapaAtual = null;
let relogioAtual = null;

function bandeira(codigo) {
  if (!codigo || String(codigo).length !== 2) return "";
  return String(codigo).toUpperCase().split("").map(c =>
    String.fromCodePoint(127397 + c.charCodeAt(0))).join("");
}

function nivelRisco(seg) {
  let nota = 0;
  const motivos = [];
  if (seg.is_vpn || seg.is_proxy || seg.is_tor || seg.is_relay) {
    nota += 35; motivos.push("anonimato");
  }
  if (seg.is_hosting) { nota += 20; motivos.push("hosting"); }
  const abuso = Number(seg.abuse_score || 0);
  if (abuso > 50) { nota += 30; motivos.push("abuse " + abuso); }
  if (seg.is_mobile) nota = Math.max(0, nota - 5);
  nota = Math.max(0, Math.min(100, nota));
  const classe = nota >= 60 ? "risco-alto" : nota >= 25 ? "risco-medio" : "risco-baixo";
  const texto = nota >= 60 ? "ALTO" : nota >= 25 ? "MÉDIO" : "BAIXO";
  return { nota: nota, classe: classe, texto: texto, motivos: motivos.join(", ") || "sem sinais" };
}

function iniciarRelogio(fuso) {
  if (relogioAtual) clearInterval(relogioAtual);
  const alvo = document.getElementById("relatorio-hora");
  if (!alvo) return;
  if (!fuso) { alvo.textContent = "fuso não informado"; return; }
  const mostrarHora = () => {
    try {
      alvo.textContent = new Intl.DateTimeFormat("pt-BR", {
        timeZone: fuso, hour: "2-digit", minute: "2-digit", second: "2-digit",
      }).format(new Date()) + " no destino · " + fuso;
    } catch (e) {
      alvo.textContent = "fuso: " + fuso;
    }
  };
  mostrarHora();
  relogioAtual = setInterval(mostrarHora, 1000);
}

function desenharMapa(lat, lon) {
  const el = document.getElementById("mapa");
  if (!el) return;
  if (!window.L || !lat || !lon || !Number.isFinite(Number(lat)) || !Number.isFinite(Number(lon))) {
    el.innerHTML = '<p class="sem-mapa">mapa indisponível (coordenadas ou rede ausentes)</p>';
    return;
  }
  if (mapaAtual) { mapaAtual.remove(); mapaAtual = null; }
  mapaAtual = L.map(el, { scrollWheelZoom: false }).setView([Number(lat), Number(lon)], 10);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: '&copy; OpenStreetMap contributors', maxZoom: 18,
  }).addTo(mapaAtual);
  L.circleMarker([Number(lat), Number(lon)], {
    radius: 8, color: "#2B5CFF", weight: 3, fillColor: "#2B5CFF", fillOpacity: .9,
  }).addTo(mapaAtual);
}

function salvarHistorico(dados) {
  try {
    const chave = "iplens_historico";
    const lista = JSON.parse(localStorage.getItem(chave) || "[]");
    const anterior = lista.find(x => x.ip === dados.ip);
    const atual = {
      ip: dados.ip,
      cidade: (dados.localizacao || {}).cidade || "",
      isp: (dados.rede || {}).isp || "",
      asn: (dados.rede || {}).asn || "",
      ts: Date.now(),
    };
    const mudou = anterior && (anterior.isp !== atual.isp || anterior.asn !== atual.asn || anterior.cidade !== atual.cidade);
    lista.unshift(atual);
    localStorage.setItem(chave, JSON.stringify(lista.slice(0, 10)));
    return mudou;
  } catch (e) {
    return false;
  }
}

function pintarHistorico() {
  const el = document.getElementById("historico");
  if (!el) return;
  let lista = [];
  try { lista = JSON.parse(localStorage.getItem("iplens_historico") || "[]"); } catch (e) {}
  if (!lista.length) { el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = "<span>recentes</span>" + lista.slice(0, 6).map(item =>
    '<button type="button" class="chip-historico" data-ip="' + escapar(item.ip) + '">'
    + escapar(item.ip) + "</button>").join("");
}

function mostrar(dados) {
  const loc = dados.localizacao || {};
  const rede = dados.rede || {};
  const org = dados.organizacao || {};
  const seg = dados.seguranca || {};
  const contato = dados.contatos || {};
  const rdap = dados.rdap || {};
  const extras = dados.extras || {};
  const fontes = dados.fontes || {};
  const bandeiraPais = bandeira(loc.codigo_pais);
  const risco = nivelRisco(seg);
  const mudou = salvarHistorico(dados);

  document.getElementById("resultado-ip").textContent = dados.ip || "—";
  document.getElementById("res-nome").textContent =
    (bandeiraPais ? bandeiraPais + " " : "") + (dados.hostname || dados.ip || "IP identificado");
  document.getElementById("res-sub").textContent =
    texto(loc.cidade) + " · " + texto(loc.pais) + " · " + texto(rede.asn || org.nome)
    + (mudou ? " · mudou de rede" : "");

  const selo = document.getElementById("selo-risco");
  selo.textContent = "RISCO " + risco.texto;
  selo.className = "resultado-selo " + risco.classe;
  selo.title = risco.nota + "/100 · " + risco.motivos;

  iniciarRelogio(extras.fuso_id || loc.fuso);

  const timeline = (rdap.eventos || []).map(ev => {
    const data = ev.eventDate ? new Date(ev.eventDate) : null;
    return "<li><span>" + (data && !Number.isNaN(data.getTime()) ? data.toLocaleDateString("pt-BR") : "—")
      + "</span>" + escapar(ev.eventAction || "evento") + "</li>";
  }).join("");

  const barras = Object.keys(fontes).map(nome => {
    const f = fontes[nome] || {};
    const dadosFonte = f.dados || {};
    const campos = typeof dadosFonte === "object" ? Object.keys(dadosFonte).length : 0;
    const largura = f.disponivel && !f.vazio ? Math.min(100, 18 + campos * 4) : 4;
    return '<div class="barra-fonte"><span>' + escapar(nome) + "</span>"
      + '<div class="barra"><i style="width:' + largura + '%"></i></div>'
      + "<b>" + (f.disponivel ? (f.vazio ? "vazia" : campos + " campos") : "falhou") + "</b></div>";
  }).join("");

  cards.innerHTML = [
    '<article class="cartao cartao-mapa"><h4>Mapa</h4><div id="mapa"></div></article>',
    cartao("Localização", [
      linha("Cidade", loc.cidade),
      linha("Região", loc.regiao),
      linha("Código da região", loc.codigo_regiao),
      linha("País", bandeiraPais ? bandeiraPais + " " + (loc.pais || "") : loc.pais),
      linha("Código do país", loc.codigo_pais),
      linha("Continente", loc.continente),
      linha("Código do continente", extras.continente_codigo),
      linha("Latitude", loc.latitude),
      linha("Longitude", loc.longitude),
      linha("Coordenadas", loc.loc),
      linha("Fuso", loc.fuso),
      linha("Hora no destino", extras.fuso_atual),
      linha("Offset", loc.offset),
      linha("CEP", loc.cep),
      linha("Moeda", valorTexto(extras.moeda)),
      linha("Telefone", loc.codigo_telefone),
      linha("Bandeira", extras.bandeira_emoji),
      linha("Idiomas", valorTexto(loc.idiomas)),
      linha("União Europeia", loc.e_uniao_europeia === null || loc.e_uniao_europeia === undefined
        ? "" : simNao(loc.e_uniao_europeia)),
    ]),
    cartao("Rede", [
      linha("Hostname", dados.hostname),
      linha("ISP", rede.isp),
      linha("Organização", rede.organizacao),
      linha("ASN", rede.asn),
      linha("Nome ASN", rede.asn_nome),
      linha("AS completo", rede.as_string),
      linha("Domínio", rede.dominio),
      linha("Bloco", rede.bloco),
      linha("Reverso", rede.reverso),
      linha("Consulta", rede.consulta),
      linha("Status", rede.status),
      linha("Mensagem", rede.mensagem),
    ]),
    cartao("Segurança", [
      linha("Risco", risco.nota + "/100 (" + risco.texto + ")"),
      linha("Motivos", risco.motivos),
      linha("Mobile", simNao(seg.is_mobile), seg.is_mobile ? "sim" : "nao"),
      linha("VPN", simNao(seg.is_vpn), seg.is_vpn ? "sim" : "nao"),
      linha("Proxy", simNao(seg.is_proxy), seg.is_proxy ? "sim" : "nao"),
      linha("Tor", simNao(seg.is_tor), seg.is_tor ? "sim" : "nao"),
      linha("Relay", simNao(seg.is_relay), seg.is_relay ? "sim" : "nao"),
      linha("Hosting", simNao(seg.is_hosting), seg.is_hosting ? "sim" : "nao"),
      linha("Abuse score", seg.abuse_score),
      linha("Total de reports", seg.abuse_total_reports),
      linha("Último reporte", seg.abuse_last_reported),
      linha("Uso", seg.abuse_usage_type),
      linha("Domínio abuso", seg.abuse_domain),
      linha("ISP abuso", seg.abuse_isp),
      linha("Categorias", valorTexto(seg.abuse_categories)),
    ]),
    cartao("Organização", [
      linha("Nome", org.nome),
      linha("ISP", org.isp),
      linha("Domínio", org.dominio),
      linha("Tipo", org.tipo),
      linha("ASN", org.asn),
      linha("Nome ASN", org.asn_nome),
      linha("ASN ipwho", safeObj(extras.conexao, "asn")),
      linha("Org ipwho", safeObj(extras.conexao, "org")),
      linha("ISP ipwho", safeObj(extras.conexao, "isp")),
      linha("Domínio ipwho", safeObj(extras.conexao, "domain")),
      linha("Handle RDAP", org.bloco_rdap),
      linha("País RDAP", org.pais_rdap),
      linha("Proxy ip2location", simNao(safeObj(extras.ip2location, "is_proxy"))),
    ]),
    cartao("Contatos", [
      linha("Abuso", contato.abuse_email),
      linha("Técnico", contato.tech_email),
      linha("Telefone", contato.abuse_phone),
      linha("Entidades RDAP", (contato.entidades || []).length),
    ]),
    cartao("RDAP", [
      linha("Handle", rdap.handle),
      linha("Nome", rdap.nome),
      linha("Tipo", rdap.tipo),
      linha("Início", rdap.inicio),
      linha("Fim", rdap.fim),
      linha("País", rdap.pais),
      linha("Eventos", (rdap.eventos || []).length),
      linha("Observações", (rdap.observacoes || []).length),
      linha("Links", (rdap.links || []).length),
    ]),
    '<article class="cartao"><h4>Linha do tempo RDAP</h4>'
      + (timeline ? '<ol class="timeline">' + timeline + "</ol>" : '<p class="vazio">sem eventos</p>')
      + "</article>",
    '<article class="cartao"><h4>Completude por fonte</h4>' + barras + "</article>",
    cartao("Fontes", Object.keys(fontes).map(nome =>
      linha(nome, fontes[nome].disponivel ? (fontes[nome].vazio ? "vazia" : "ok") : "falhou"))),
  ].join("");

  jsonResultado.textContent = JSON.stringify(dados, null, 2);
  resultado.hidden = false;
  pintarHistorico();
  setTimeout(() => desenharMapa(loc.latitude, loc.longitude), 80);
}

function safeObj(obj, chave) {
  return obj && obj[chave] !== undefined ? obj[chave] : "";
}

async function consultar(ip) {
  aviso.hidden = true;
  carregando.hidden = false;
  resultado.hidden = true;
  botao.disabled = true;

  try {
    const resposta = await fetch("/lookup?ip=" + encodeURIComponent(ip), {
      headers: { Accept: "application/json" },
    });
    const dados = await resposta.json().catch(() => null);
    if (!resposta.ok || !dados) {
      aviso.textContent = (dados && dados.detail) || "Não foi possível consultar esse IP agora.";
      aviso.hidden = false;
      return;
    }
    mostrar(dados);
  } catch (erro) {
    aviso.textContent = "A API não respondeu. Verifique se o serviço está no ar.";
    aviso.hidden = false;
  } finally {
    carregando.hidden = true;
    botao.disabled = false;
  }
}

form.addEventListener("submit", (evento) => {
  evento.preventDefault();
  const ip = campoIp.value.trim();
  if (!ip) { aviso.textContent = "Digite um IP para continuar."; aviso.hidden = false; return; }
  consultar(ip);
});

document.querySelectorAll(".exemplo").forEach((item) => {
  item.addEventListener("click", () => {
    campoIp.value = item.dataset.ip;
    consultar(item.dataset.ip);
  });
});

document.getElementById("historico").addEventListener("click", (evento) => {
  const chip = evento.target.closest(".chip-historico");
  if (!chip) return;
  campoIp.value = chip.dataset.ip;
  consultar(chip.dataset.ip);
});

campoIp.addEventListener("input", () => {
  campoIp.value = campoIp.value.replace(/[^0-9a-fA-F.:]/g, "").slice(0, 45);
});

/* --- copiar JSON --- */
document.addEventListener("click", async (evento) => {
  const botaoCopia = evento.target.closest(".botao-copy[data-alvo]");
  if (!botaoCopia) return;
  const alvo = document.getElementById(botaoCopia.dataset.alvo);
  if (!alvo) return;
  try {
    await navigator.clipboard.writeText(alvo.textContent);
    const textoOriginal = botaoCopia.textContent;
    botaoCopia.textContent = "copiado";
    setTimeout(() => { botaoCopia.textContent = textoOriginal; }, 1300);
  } catch (erro) {
    botaoCopia.textContent = "selecione e copie";
  }
});

/* --- um único movimento: o comando no hero se reescreve. --- */
(function digitar() {
  const alvo = document.getElementById("typing");
  if (!alvo || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const frases = [
    "consulte um ip para começar",
    "geolocalização em tempo real",
    "rede, asn e operadora",
    "sinais de vpn e proxy",
  ];
  let indice = 0;
  let posicao = frases[0].length;
  let apagando = false;
  function passo() {
    alvo.textContent = frases[indice].slice(0, posicao);
    if (!apagando && posicao < frases[indice].length) {
      posicao += 1;
    } else if (!apagando) {
      apagando = true;
    } else if (posicao > 0) {
      posicao -= 1;
    } else {
      apagando = false;
      indice = (indice + 1) % frases.length;
    }
    setTimeout(passo, apagando ? 45 : 90);
  }
  setTimeout(passo, 900);
})();
