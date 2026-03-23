"""
Prova Técnica - NASAJON
Autor: (seu nome aqui)
Descrição: Lê input.csv, enriquece com API do IBGE, gera resultado.csv,
           calcula estatísticas e envia para a API de correção.
"""

import csv
import json
import sys
import unicodedata
import difflib
import requests

SEU_EMAIL = "bervieira2006@gmail.com"
SUA_SENHA = "Pantufa2006@"
SEU_NOME  = "Bernardo Creplive Vieira"



SUPABASE_URL      = "https://mynxlubykylncinttggu.supabase.co"
SUPABASE_ANON_KEY = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im15bnhsdWJ5a3luY2ludHRnZ3UiLCJyb2xl"
    "IjoiYW5vbiIsImlhdCI6MTc0NzMwMzMyMiwiZXhwIjoyMDYyODc5MzIyfQ."
    "Z-zqiD6_tjnF2WLU167z7jT5NzZaG72dWH0dpQW1N-Y"
)
EDGE_FUNCTION_URL = "https://mynxlubykylncinttggu.functions.supabase.co/ibge-submit"
IBGE_API_URL      = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

HEADERS_SUPABASE = {
    "Content-Type": "application/json",
    "apikey": SUPABASE_ANON_KEY,
}

INPUT_FILE  = "input.csv"
OUTPUT_FILE = "resultado.csv"


def normalizar(texto: str) -> str:
    """Remove acentos, converte para minúsculas e tira espaços extras."""
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if unicodedata.category(c) != "Mn")
    return sem_acento.lower().strip()


def fazer_signup():
    print("\n[1/5] Fazendo cadastro no Supabase...")
    url  = f"{SUPABASE_URL}/auth/v1/signup"
    body = {
        "email": SEU_EMAIL,
        "password": SUA_SENHA,
        "data": {"nome": SEU_NOME},
    }
    resp = requests.post(url, headers=HEADERS_SUPABASE, json=body, timeout=15)
    if resp.status_code in (200, 201):
        print("  ✅ Cadastro realizado! Verifique seu e-mail e clique no link de confirmação.")
        print("     Após confirmar, rode o script novamente.")
        sys.exit(0)
    elif resp.status_code == 400 and "already registered" in resp.text:
        print("  ℹ️  E-mail já cadastrado. Pulando cadastro.")
    else:
        print(f"  ⚠️  Resposta inesperada no signup: {resp.status_code} – {resp.text}")



def fazer_login() -> str:
    print("\n[2/5] Fazendo login...")
    url  = f"{SUPABASE_URL}/auth/v1/token?grant_type=password"
    body = {"email": SEU_EMAIL, "password": SUA_SENHA}
    resp = requests.post(url, headers=HEADERS_SUPABASE, json=body, timeout=15)
    if resp.status_code != 200:
        print(f"  ❌ Erro no login: {resp.status_code} – {resp.text}")
        print("     Verifique se confirmou o e-mail e se as credenciais estão corretas.")
        sys.exit(1)
    token = resp.json().get("access_token")
    print(f"  ✅ Login OK! Token obtido ({token[:30]}...)")
    return token



def buscar_municipios_ibge() -> list[dict]:
    print("\n[3/5] Buscando municípios do IBGE...")
    try:
        resp = requests.get(IBGE_API_URL, timeout=30)
        resp.raise_for_status()
        municipios = resp.json()
        print(f"  ✅ {len(municipios)} municípios carregados do IBGE.")
        return municipios
    except Exception as exc:
        print(f"  ❌ Erro ao acessar API do IBGE: {exc}")
        sys.exit(1)


def construir_indice(municipios: list[dict]) -> dict:
    """
    Retorna um dicionário:
      chave_normalizada → lista de dicts com nome oficial, UF, região, id_ibge

    Guarda listas para detectar AMBIGUIDADE (mesmo nome em estados diferentes).
    """
    indice: dict[str, list[dict]] = {}
    for m in municipios:
        nome_oficial = m["nome"]
        uf           = m["microrregiao"]["mesorregiao"]["UF"]["sigla"]
        regiao       = m["microrregiao"]["mesorregiao"]["UF"]["regiao"]["nome"]
        id_ibge      = m["id"]

        chave = normalizar(nome_oficial)
        entrada = {
            "municipio_ibge": nome_oficial,
            "uf":             uf,
            "regiao":         regiao,
            "id_ibge":        id_ibge,
        }
        indice.setdefault(chave, []).append(entrada)
    return indice


def encontrar_municipio(nome_input: str, indice: dict) -> tuple[str, dict | None]:
    """
    Retorna (status, dados_do_municipio_ou_None).
    Estratégia:
      1. Busca exata pelo nome normalizado.
      2. Se não achar, busca difusa (fuzzy) com threshold 0.75.
      3. Se o resultado tiver >1 município (mesmo nome em UFs diferentes) → AMBIGUO.
    """
    chave = normalizar(nome_input)

   
    if chave in indice:
        matches = indice[chave]
        if len(matches) == 1:
            return "OK", matches[0]
        else:
            return "AMBIGUO", matches[0]

    todas_as_chaves = list(indice.keys())
    proximas = difflib.get_close_matches(chave, todas_as_chaves, n=3, cutoff=0.75)

    if not proximas:
        return "NAO_ENCONTRADO", None

    melhor_chave = proximas[0]
    matches      = indice[melhor_chave]

    if len(matches) > 1:
        return "AMBIGUO", matches[0]

    return "OK", matches[0]


def processar_municipios(indice: dict) -> list[dict]:
    print("\n[4/5] Processando municípios...")
    resultados = []

    with open(INPUT_FILE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            nome_input = row["municipio"].strip()
            populacao  = int(row["populacao"].strip())

            status, dados = encontrar_municipio(nome_input, indice)

            if dados:
                linha = {
                    "municipio_input":  nome_input,
                    "populacao_input":  populacao,
                    "municipio_ibge":   dados["municipio_ibge"],
                    "uf":               dados["uf"],
                    "regiao":           dados["regiao"],
                    "id_ibge":          dados["id_ibge"],
                    "status":           status,
                }
            else:
                linha = {
                    "municipio_input":  nome_input,
                    "populacao_input":  populacao,
                    "municipio_ibge":   "",
                    "uf":               "",
                    "regiao":           "",
                    "id_ibge":          "",
                    "status":           status,
                }

            resultados.append(linha)
            emoji = "✅" if status == "OK" else ("⚠️ " if status == "AMBIGUO" else "❌")
            print(f"  {emoji} {nome_input:20s} → {status:15s}  [{dados['municipio_ibge'] if dados else ''}]")

    return resultados


def salvar_resultado(resultados: list[dict]):
    campos = ["municipio_input", "populacao_input", "municipio_ibge",
              "uf", "regiao", "id_ibge", "status"]
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        writer.writerows(resultados)
    print(f"\n  💾 '{OUTPUT_FILE}' salvo com {len(resultados)} linhas.")


def calcular_estatisticas(resultados: list[dict]) -> dict:
    total_municipios     = len(resultados)
    total_ok             = sum(1 for r in resultados if r["status"] == "OK")
    total_nao_encontrado = sum(1 for r in resultados if r["status"] == "NAO_ENCONTRADO")
    total_erro_api       = sum(1 for r in resultados if r["status"] == "ERRO_API")
    pop_total_ok         = sum(r["populacao_input"] for r in resultados if r["status"] == "OK")

    pop_por_regiao: dict[str, list[int]] = {}
    for r in resultados:
        if r["status"] == "OK" and r["regiao"]:
            pop_por_regiao.setdefault(r["regiao"], []).append(r["populacao_input"])

    medias_por_regiao = {
        regiao: round(sum(pops) / len(pops), 2)
        for regiao, pops in pop_por_regiao.items()
    }

    stats = {
        "total_municipios":     total_municipios,
        "total_ok":             total_ok,
        "total_nao_encontrado": total_nao_encontrado,
        "total_erro_api":       total_erro_api,
        "pop_total_ok":         pop_total_ok,
        "medias_por_regiao":    medias_por_regiao,
    }

    print("\n  📊 Estatísticas calculadas:")
    for k, v in stats.items():
        print(f"     {k}: {v}")

    return stats


def enviar_resultados(stats: dict, access_token: str):
    print("\n[5/5] Enviando para a API de correção...")
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {access_token}",
    }
    payload = {"stats": stats}

    try:
        resp = requests.post(EDGE_FUNCTION_URL, headers=headers, json=payload, timeout=30)
        resposta = resp.json()
        print("\n" + "=" * 50)
        print("  🏆 RESULTADO DA CORREÇÃO:")
        print(f"     Score    : {resposta.get('score', 'N/A')}")
        print(f"     Feedback : {resposta.get('feedback', 'N/A')}")
        if "components" in resposta:
            print(f"     Detalhes : {json.dumps(resposta['components'], indent=6, ensure_ascii=False)}")
        print("=" * 50 + "\n")
    except Exception as exc:
        print(f"  ❌ Erro ao enviar resultados: {exc}")
        print(f"     Resposta bruta: {resp.text if 'resp' in dir() else 'sem resposta'}")



def main():
    print("=" * 50)
    print("  NASAJON – Prova Técnica")
    print("=" * 50)

    # Validação básica
    if "SEU_EMAIL_AQUI" in SEU_EMAIL:
        print("\n❌ ATENÇÃO: Preencha SEU_EMAIL, SUA_SENHA e SEU_NOME no início do script!")
        sys.exit(1)

    # 1. Signup (na primeira vez para e criar conta)
    fazer_signup()

    # 2. Login
    access_token = fazer_login()

    # 3. Buscar IBGE
    municipios = buscar_municipios_ibge()
    indice     = construir_indice(municipios)

    # 4. Processar municípios
    resultados = processar_municipios(indice)
    salvar_resultado(resultados)

    # 5. Calcular estatísticas
    stats = calcular_estatisticas(resultados)

    # 6. Enviar para API de correção
    enviar_resultados(stats, access_token)


if __name__ == "__main__":
    main()
