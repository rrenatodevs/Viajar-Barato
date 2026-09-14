"""
Viajar Barato — Buscador de Passagens Aéreas (versão com tela gráfica)
------------------------------------------------------------------------
Mesma lógica do app.py (terminal), só que com uma interface gráfica
feita em Tkinter, biblioteca que já vem junto com o Python.

Autor: Renato
"""

import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox

from dotenv import load_dotenv
import requests

# ==============================================================
# CONFIGURAÇÃO INICIAL
# ==============================================================

load_dotenv()
TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN")


# ==============================================================
# FUNÇÕES DE CONVERSÃO: NOME DE LUGAR <-> CÓDIGO IATA
# (mesma lógica do app.py, só que a escolha entre várias opções
#  agora abre uma janela, em vez de perguntar no terminal)
# ==============================================================

def buscar_opcoes_cidade(nome_lugar):
    """
    Busca na API de autocomplete todas as cidades parecidas com o
    texto digitado. Não decide sozinha qual é a certa — só traz a
    lista bruta, para a interface gráfica decidir o que fazer.

    Retorna:
        list[dict]: lista de cidades encontradas (pode estar vazia).
    """
    url = "https://autocomplete.travelpayouts.com/places2"
    params = {"term": nome_lugar, "locale": "pt", "types[]": "city"}
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json()


def obter_nome_cidade(codigo_iata, cache):
    """
    Converte um código IATA (ex: "RIO") de volta para o nome legível
    da cidade (ex: "Rio de Janeiro"), usando cache para não repetir
    buscas desnecessárias.
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
        pass

    cache[codigo_iata] = codigo_iata
    return codigo_iata


# ==============================================================
# FUNÇÕES DE BUSCA E TRATAMENTO DE DADOS DA API DE PREÇOS
# (idênticas ao app.py — a lógica de negócio não muda com a tela)
# ==============================================================

def buscar_precos_baratos(origem, token, destino=None, moeda="brl"):
    url = "https://api.travelpayouts.com/v1/prices/cheap"
    headers = {"X-Access-Token": token}
    params = {"origin": origem, "currency": moeda}
    if destino:
        params["destination"] = destino
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def transformar_em_lista(resposta_api, origem):
    voos = []
    destinos = resposta_api["data"]
    for codigo_destino, opcoes in destinos.items():
        for detalhes in opcoes.values():
            voos.append({
                "origem": origem,
                "destino": codigo_destino,
                "preco": detalhes["price"],
                "data_ida": detalhes["departure_at"],
                "data_volta": detalhes.get("return_at"),
                "companhia_aerea": detalhes["airline"]
            })
    return voos


def filtrar_por_preco(lista_voos, preco_maximo):
    return [voo for voo in lista_voos if voo["preco"] <= preco_maximo]


# ==============================================================
# JANELA DE ESCOLHA (aparece quando há mais de uma cidade parecida)
# ==============================================================

class JanelaEscolha(tk.Toplevel):
    """
    Janela pop-up simples que mostra uma lista de cidades encontradas
    e deixa o usuário clicar na que ele quis dizer.
    """
    def __init__(self, master, opcoes):
        super().__init__(master)
        self.title("Qual cidade você quis dizer?")
        self.resultado = None  # aqui vai ficar o código IATA escolhido

        tk.Label(self, text="Encontrei várias cidades parecidas:").pack(padx=10, pady=10)

        lista = tk.Listbox(self, width=50, height=8)
        for item in opcoes:
            lista.insert(tk.END, f"{item['name']} ({item['code']}) - {item['country_name']}")
        lista.pack(padx=10, pady=5)

        def confirmar():
            selecionado = lista.curselection()
            if selecionado:
                indice = selecionado[0]
                self.resultado = opcoes[indice]["code"]
            self.destroy()

        tk.Button(self, text="Confirmar", command=confirmar).pack(pady=10)

        # Trava a janela principal até essa janela ser fechada
        self.grab_set()
        self.wait_window()


# ==============================================================
# APLICAÇÃO PRINCIPAL (a janela do programa)
# ==============================================================

class AppViajarBarato(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viajar Barato — Buscador de Passagens")
        self.geometry("650x500")

        self.cache_nomes = {}  # cache compartilhado entre as buscas de nome

        # Fila usada para a thread de busca "entregar" resultados com segurança
        # para a thread principal — nunca se deve mexer na tela direto de
        # dentro de outra thread, então tudo passa por aqui.
        self.fila_resultados = queue.Queue()

        self._montar_tela()

        # Inicia o loop que fica checando a fila periodicamente (rodando
        # sempre na thread principal, por isso é seguro)
        self._verificar_fila()

    def _montar_tela(self):
        """Cria e organiza todos os campos, botões e a área de resultado."""

        frame_topo = ttk.Frame(self, padding=10)
        frame_topo.pack(fill="x")

        # --- Campo: origem ---
        ttk.Label(frame_topo, text="De onde você vai partir?").grid(row=0, column=0, sticky="w")
        self.campo_origem = ttk.Entry(frame_topo, width=30)
        self.campo_origem.grid(row=0, column=1, padx=5, pady=5)

        # --- Campo: destino ---
        ttk.Label(frame_topo, text="Para onde? (opcional)").grid(row=1, column=0, sticky="w")
        self.campo_destino = ttk.Entry(frame_topo, width=30)
        self.campo_destino.grid(row=1, column=1, padx=5, pady=5)

        # --- Campo: preço máximo ---
        ttk.Label(frame_topo, text="Preço máximo (R$)").grid(row=2, column=0, sticky="w")
        self.campo_preco = ttk.Entry(frame_topo, width=30)
        self.campo_preco.grid(row=2, column=1, padx=5, pady=5)

        # --- Checkbox: aplicar filtro de preço ---
        self.var_filtrar = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            frame_topo, text="Aplicar filtro de preço", variable=self.var_filtrar
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=5)

        # --- Botão de busca ---
        self.botao_buscar = ttk.Button(frame_topo, text="Buscar voos", command=self._iniciar_busca)
        self.botao_buscar.grid(row=4, column=0, columnspan=2, pady=10)

        # --- Área de resultados (com barra de rolagem) ---
        frame_resultado = ttk.Frame(self, padding=10)
        frame_resultado.pack(fill="both", expand=True)

        self.area_resultado = tk.Text(frame_resultado, wrap="word")
        self.area_resultado.pack(side="left", fill="both", expand=True)

        barra_rolagem = ttk.Scrollbar(frame_resultado, command=self.area_resultado.yview)
        barra_rolagem.pack(side="right", fill="y")
        self.area_resultado["yscrollcommand"] = barra_rolagem.set

    def _verificar_fila(self):
        """
        Roda periodicamente (a cada 100ms), sempre na thread principal,
        verificando se a thread de busca deixou algum resultado ou erro
        pronto na fila. Esse é o único ponto seguro de contato entre a
        thread de busca e a interface gráfica.
        """
        try:
            tipo, conteudo = self.fila_resultados.get_nowait()
            if tipo == "erro":
                self._mostrar_erro(conteudo)
            elif tipo == "resultado":
                self._mostrar_resultado(conteudo)
        except queue.Empty:
            pass  # não tem nada novo — normal, só continua o loop

        self.after(100, self._verificar_fila)

    def _resolver_cidade(self, nome_lugar):
        """
        Busca o código IATA de um nome de cidade. Se houver mais de
        uma opção, abre a JanelaEscolha para o usuário decidir.
        """
        opcoes = buscar_opcoes_cidade(nome_lugar)

        if not opcoes:
            return None
        if len(opcoes) == 1:
            return opcoes[0]["code"]

        janela = JanelaEscolha(self, opcoes[:5])
        return janela.resultado

    def _iniciar_busca(self):
        """
        Chamado quando o botão "Buscar voos" é clicado. Desativa o
        botão (evita clique duplo) e roda a busca em uma thread
        separada, para a tela não travar durante a espera da API.
        """
        self.botao_buscar.config(state="disabled")
        self.area_resultado.delete("1.0", tk.END)
        self.area_resultado.insert(tk.END, "Buscando...\n")

        thread = threading.Thread(target=self._executar_busca)
        thread.start()

    def _executar_busca(self):
        """
        Faz o trabalho pesado (chamadas de rede) fora da thread da
        interface gráfica. No final, manda o resultado de volta para
        a tela principal com self.after (necessário porque só a
        thread principal pode mexer nos widgets do Tkinter).
        """
        nome_origem = self.campo_origem.get().strip()
        nome_destino = self.campo_destino.get().strip()
        texto_preco = self.campo_preco.get().strip()

        if not nome_origem:
            self.fila_resultados.put(("erro", "Digite a cidade de origem."))
            return

        try:
            preco_maximo = float(texto_preco) if texto_preco else None
        except ValueError:
            self.fila_resultados.put(("erro", "Preço inválido. Digite só números."))
            return

        origem = self._resolver_cidade(nome_origem)
        if not origem:
            self.fila_resultados.put(("erro", "Não encontrei essa cidade de origem."))
            return

        destino = self._resolver_cidade(nome_destino) if nome_destino else None

        try:
            resultado = buscar_precos_baratos(origem, TOKEN, destino=destino)
            lista_voos = transformar_em_lista(resultado, origem)

            if self.var_filtrar.get() and preco_maximo is not None:
                lista_voos = filtrar_por_preco(lista_voos, preco_maximo)

            texto_final = self._montar_texto_resultado(lista_voos)
            self.fila_resultados.put(("resultado", texto_final))

        except requests.exceptions.RequestException as e:
            self.fila_resultados.put(("erro", f"Erro ao buscar voos: {e}"))

    def _montar_texto_resultado(self, lista_voos):
        """Monta o texto final a ser exibido na área de resultado."""
        if not lista_voos:
            return "Nenhum voo encontrado."

        voos_ordenados = sorted(lista_voos, key=lambda v: v["preco"])
        linhas = [f"✈️  {len(voos_ordenados)} passagem(ns) encontrada(s), da mais barata pra mais cara:\n"]

        for voo in voos_ordenados:
            nome_origem = obter_nome_cidade(voo["origem"], self.cache_nomes)
            nome_destino = obter_nome_cidade(voo["destino"], self.cache_nomes)
            data_volta = voo["data_volta"] if voo["data_volta"] else "não disponível"

            linhas.append(
                f"{nome_origem} → {nome_destino} | {voo['companhia_aerea']} | "
                f"R$ {voo['preco']:.2f} | Ida: {voo['data_ida']} | Volta: {data_volta}"
            )

        return "\n".join(linhas)

    def _mostrar_resultado(self, texto):
        """Atualiza a área de texto com o resultado final e reativa o botão."""
        self.area_resultado.delete("1.0", tk.END)
        self.area_resultado.insert(tk.END, texto)
        self.botao_buscar.config(state="normal")

    def _mostrar_erro(self, mensagem):
        """Mostra uma caixinha de erro e reativa o botão de busca."""
        self.area_resultado.delete("1.0", tk.END)
        messagebox.showerror("Erro", mensagem)
        self.botao_buscar.config(state="normal")


# ==============================================================
# PONTO DE ENTRADA DO PROGRAMA
# ==============================================================

if __name__ == "__main__":
    app = AppViajarBarato()
    app.mainloop()