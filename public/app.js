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

function mostrar(dados) {
  const loc = dados.localizacao || {};
  const rede = dados.rede || {};
  const org = dados.organizacao || {};
  const seg = dados.seguranca || {};
  const contato = dados.contatos || {};
  const rdap = dados.rdap || {};
  const fontes = dados.fontes || {};

  document.getElementById("resultado-ip").textContent = dados.ip || "—";
  document.getElementById("res-nome").textContent = dados.hostname || dados.ip || "IP identificado";
  document.getElementById("res-sub").textContent =
    texto(loc.cidade) + " · " + texto(loc.pais) + " · " + texto(rede.asn || org.nome);

  cards.innerHTML = [
    cartao("Localização", [
      linha("Cidade", loc.cidade),
      linha("Região", loc.regiao),
      linha("Código da região", loc.codigo_regiao),
      linha("País", loc.pais),
      linha("Código do país", loc.codigo_pais),
      linha("Continente", loc.continente),
      linha("Código do continente", loc.codigo_continente),
      linha("Latitude", loc.latitude),
      linha("Longitude", loc.longitude),
      linha("Coordenadas", loc.loc),
      linha("Fuso", loc.fuso),
      linha("Offset", loc.offset),
      linha("CEP", loc.cep),
      linha("Moeda", loc.moeda),
      linha("Telefone", loc.codigo_telefone),
      linha("Bandeira", loc.bandeira),
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
      linha("Handle RDAP", org.bloco_rdap),
      linha("País RDAP", org.pais_rdap),
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
    cartao("Fontes", Object.keys(fontes).map((nome) =>
      linha(nome, fontes[nome].disponivel ? (fontes[nome].vazio ? "vazia" : "ok") : "falhou"))),
  ].join("");

  jsonResultado.textContent = JSON.stringify(dados, null, 2);
  resultado.hidden = false;
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
