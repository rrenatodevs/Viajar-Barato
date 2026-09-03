"""
Viajar Barato — Buscador de Passagens Aéreas
------------------------------------------------
Programa de terminal que busca passagens aéreas reais usando a API
da Travelpayouts (dados do Aviasales), permitindo:

- Digitar o nome da cidade de origem e destino (sem precisar saber código IATA)
- Filtrar por preço máximo
- Ver os resultados ordenados do mais barato pro mais caro, com nomes de
  cidade legíveis em vez de códigos crus

Autor: Renato
"""

import os
from dotenv import load_dotenv
import requests

# ==============================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================

# Carrega as variáveis do arquivo .env (onde fica o token da API,
# fora do código-fonte por segurança)
load_dotenv()
TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN")


# ==============================================================
# FUNÇÕES DE CONVERSÃO: NOME DE LUGAR <-> CÓDIGO IATA
# ==============================================================

def buscar_codigo_iata(nome_lugar):
    """
    Converte o nome de uma cidade digitado pelo usuário (ex: "São Paulo")
    no código IATA correspondente (ex: "SAO"), usando a API pública de
    autocomplete da Travelpayouts (não precisa de token).

    Se houver mais de uma cidade parecida com o texto digitado, mostra
    as opções na tela e deixa o usuário escolher qual é a certa.

    Parâmetros:
        nome_lugar (str): nome da cidade digitado pelo usuário.

    Retorna:
        str: código IATA da cidade escolhida, ou None se não encontrar nada.
    """
    url = "https://autocomplete.travelpayouts.com/places2"
    params = {"term": nome_lugar, "locale": "pt", "types[]": "city"}

    response = requests.get(url, params=params)
    response.raise_for_status()
    resultados = response.json()

    if not resultados:
        return None

    # Se só encontrou uma cidade, já retorna direto, sem perguntar nada
    if len(resultados) == 1:
        return resultados[0]["code"]

    # Se encontrou várias, mostra até 5 opções para o usuário escolher
    print("\nEncontrei várias opções, qual você quis dizer?")
    for i, item in enumerate(resultados[:5], start=1):
        print(f"{i}. {item['name']} ({item['code']}) - {item['country_name']}")

    escolha = input("Digite o número da opção: ").strip()
    try:
        return resultados[int(escolha) - 1]["code"]
    except (ValueError, IndexError):
        # Se digitar algo inválido (texto, número fora da lista), retorna None
        return None


def obter_nome_cidade(codigo_iata, cache):
    """
    Faz o caminho inverso de buscar_codigo_iata: recebe um código IATA
    (ex: "RIO") e devolve o nome legível da cidade (ex: "Rio de Janeiro").

    Usa um dicionário de cache para não repetir a mesma busca na API
    várias vezes durante a exibição de uma lista grande de voos.

    Parâmetros:
        codigo_iata (str): código IATA a ser traduzido.
        cache (dict): dicionário compartilhado que guarda códigos já buscados.

    Retorna:
        str: nome da cidade, ou o próprio código como alternativa se a
             busca falhar ou não encontrar nada.
    """
    if codigo_iata in cache:
        return cache[codigo_iata]

    params = {"term": codigo_iata, "locale": "pt", "types[]": "city"}
    try:
        resposta = requests.get("https://autocomplete.travelpayouts.com/places2", params=params)
        resposta.raise_for_status()
        resultados = resposta.json()

        for item in resultados:
            if item["code"] == codigo_iata:
                cache[codigo_iata] = item["name"]
                return item["name"]
    except requests.exceptions.RequestException:
        # Se der erro de rede, não trava o programa — só usa o código puro
        pass

    # Fallback: se não achou o nome, guarda o próprio código no cache
    # (evita tentar buscar de novo o mesmo código que já falhou antes)
    cache[codigo_iata] = codigo_iata
    return codigo_iata


# ==============================================================
# FUNÇÕES DE BUSCA E TRATAMENTO DE DADOS DA API DE PREÇOS
# ==============================================================

def buscar_precos_baratos(origem, token, destino=None, moeda="brl"):
    """
    Consulta a API de preços mais baratos da Travelpayouts para uma
    origem específica, opcionalmente filtrando por um destino.

    Parâmetros:
        origem (str): código IATA da cidade de origem.
        token (str): token de acesso à API (vem do .env).
        destino (str, opcional): código IATA do destino. Se None,
                                  retorna preços para vários destinos.
        moeda (str): moeda dos preços retornados (padrão: real brasileiro).

    Retorna:
        dict: resposta bruta da API em formato JSON.
    """
    url = "https://api.travelpayouts.com/v1/prices/cheap"
    headers = {"X-Access-Token": token}
    params = {"origin": origem, "currency": moeda}

    if destino:
        params["destination"] = destino

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def transformar_em_lista(resposta_api, origem):
    """
    Converte a resposta bruta da API (um dicionário aninhado, agrupado
    por destino) em uma lista simples de voos, mais fácil de filtrar
    e exibir.

    Parâmetros:
        resposta_api (dict): resposta de buscar_precos_baratos().
        origem (str): código IATA da origem (a API não devolve isso
                      de volta, então precisamos informar manualmente).

    Retorna:
        list[dict]: lista de voos, cada um no formato:
                     {"origem", "destino", "preco", "data_ida",
                      "data_volta", "companhia_aerea"}
    """
    voos = []
    destinos = resposta_api["data"]

    for codigo_destino, opcoes in destinos.items():
        for detalhes in opcoes.values():
            voos.append({
                "origem": origem,
                "destino": codigo_destino,
                "preco": detalhes["price"],
                "data_ida": detalhes["departure_at"],
                "data_volta": detalhes.get("return_at"),  # pode não existir
                "companhia_aerea": detalhes["airline"]
            })
    return voos


def filtrar_por_preco(lista_voos, preco_maximo):
    """
    Filtra uma lista de voos, mantendo apenas os que custam até
    o preço máximo informado.

    Parâmetros:
        lista_voos (list[dict]): lista de voos no formato de transformar_em_lista().
        preco_maximo (float): valor máximo que o usuário quer pagar.

    Retorna:
        list[dict]: apenas os voos dentro do orçamento.
    """
    voos_filtrados = []
    for voo in lista_voos:
        if voo["preco"] <= preco_maximo:
            voos_filtrados.append(voo)
    return voos_filtrados


# ==============================================================
# FUNÇÃO DE EXIBIÇÃO
# ==============================================================

def exibir_voos(lista_voos):
    """
    Mostra a lista de voos no terminal, ordenados do mais barato
    para o mais caro, trocando os códigos IATA por nomes de cidade
    legíveis.

    Parâmetros:
        lista_voos (list[dict]): lista de voos a serem exibidos.
    """
    if not lista_voos:
        print("\nNenhum voo encontrado.")
        return

    # Cache local: guarda os nomes de cidade já descobertos nesta exibição,
    # evitando repetir buscas para o mesmo código várias vezes
    cache_nomes = {}

    voos_ordenados = sorted(lista_voos, key=lambda v: v["preco"])
    print(f"\n✈️  {len(voos_ordenados)} passagem(ns) encontrada(s), da mais barata pra mais cara:\n")

    for voo in voos_ordenados:
        nome_origem = obter_nome_cidade(voo["origem"], cache_nomes)
        nome_destino = obter_nome_cidade(voo["destino"], cache_nomes)

        # Se não tiver data de volta (voo só de ida), mostra um texto no lugar
        data_volta = voo["data_volta"] if voo["data_volta"] else "não disponível"

        print(f"{nome_origem} → {nome_destino} | {voo['companhia_aerea']} | "
              f"R$ {voo['preco']:.2f} | "
              f"Ida: {voo['data_ida']} | Volta: {data_volta}")


# ==============================================================
# PROGRAMA PRINCIPAL
# ==============================================================

def main():
    """
    Loop principal do programa: pergunta origem, destino e preço máximo,
    busca os voos e exibe os resultados. Repete até o usuário decidir sair.
    """
    while True:
        # --- Etapa 1: origem ---
        nome_origem = input("\nDe onde você vai partir? (cidade): ").strip()
        origem = buscar_codigo_iata(nome_origem)

        if not origem:
            print("Não encontrei essa cidade. Tente novamente.")
            continue

        # --- Etapa 2: preço máximo ---
        try:
            preco_maximo = float(input("Digite o preço máximo que deseja pagar (em R$): ").strip())
        except ValueError:
            print("Preço inválido. Tente novamente.")
            continue

        # --- Etapa 3: destino (opcional) ---
        nome_destino = input(
            "Para onde você quer ir? (cidade, ou deixe em branco para ver várias opções): "
        ).strip()
        filtro_destino = buscar_codigo_iata(nome_destino) if nome_destino else None

        # --- Etapa 4: decide se aplica o filtro de preço ---
        deseja_filtrar = input("Deseja aplicar o filtro de preço máximo? (s/n): ").strip().lower() == 's'

        # --- Etapa 5: busca, filtra e exibe ---
        try:
            resultado = buscar_precos_baratos(origem, TOKEN, destino=filtro_destino)
            lista_voos = transformar_em_lista(resultado, origem)

            if deseja_filtrar:
                lista_voos = filtrar_por_preco(lista_voos, preco_maximo)

            exibir_voos(lista_voos)
        except requests.exceptions.RequestException as e:
            print(f"Erro ao buscar voos: {e}")

        # --- Etapa 6: pergunta se quer repetir ---
        print("\nDeseja buscar outro voo? (s/n)")
        if input().strip().lower() != 's':
            break


if __name__ == "__main__":
    main()
