# ✈️ Viajar Barato — Buscador de Passagens Aéreas

Programa em Python que busca passagens aéreas reais, permitindo filtrar por preço e destino — sem precisar saber código de aeroporto (IATA), já que o próprio programa converte o nome da cidade digitada automaticamente.

## 📋 Funcionalidades

- Busca de passagens aéreas com preços reais via API
- Conversão automática de nome de cidade para código IATA (ex: "São Paulo" → "SAO")
- Tratamento de ambiguidade: se o nome digitado corresponder a mais de uma cidade, o programa mostra as opções para o usuário escolher
- Filtro por preço máximo
- Filtro opcional por destino específico
- Resultados ordenados do voo mais barato para o mais caro
- Exibição de nomes de cidade legíveis (em vez de códigos crus) nos resultados

## 🛠️ Tecnologias utilizadas

- **Python 3**
- [`requests`](https://pypi.org/project/requests/) — consumo de APIs REST
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) — carregamento seguro de variáveis de ambiente
- **API da [Travelpayouts](https://www.travelpayouts.com/)** (dados do Aviasales) — busca de preços de voos e autocomplete de cidades

## 🚀 Como rodar o projeto

### Pré-requisitos

- Python 3.10 ou superior instalado
- Uma conta gratuita na [Travelpayouts](https://www.travelpayouts.com/), para gerar seu token de API

### Passo a passo

1. Clone o repositório:
   ```bash
   git clone https://github.com/rrenatodevs/Viajar-Barato.git
   cd Viajar-Barato
   ```

2. Instale as dependências:
   ```bash
   pip install requests python-dotenv
   ```

3. Crie um arquivo `.env` na raiz do projeto com o seu token da Travelpayouts:
   ```
   TRAVELPAYOUTS_TOKEN=seu_token_aqui
   ```
   > ⚠️ O arquivo `.env` nunca deve ser enviado ao GitHub — ele já está incluído no `.gitignore` deste projeto.

4. Rode o programa:
   ```bash
   python app.py
   ```

### Usando o programa

O programa vai perguntar, em sequência:
1. De onde você vai partir (nome da cidade)
2. O preço máximo que você quer pagar
3. Para onde você quer ir (opcional — deixe em branco para ver várias opções de destino)
4. Se você quer aplicar o filtro de preço máximo

Se o nome da cidade digitada for ambíguo (por exemplo, "Paris" pode ser a cidade francesa ou outras cidades homônimas ao redor do mundo), o programa lista as opções encontradas para você escolher a correta.

## 📁 Estrutura do projeto

```
Viajar-Barato/
├── app.py          # código principal do programa
├── .env            # suas credenciais (não versionado)
├── .gitignore      # arquivos ignorados pelo Git
└── README.md
```

## 🧠 Sobre o projeto

Este foi meu primeiro projeto prático consumindo uma API real em Python, construído durante meus estudos de Análise e Desenvolvimento de Sistemas. O código foi escrito por mim, e também apliquei conhecimentos de engenharia de prompt para revisar e documentar o código com a ajuda de IA, deixando-o mais legível para outros desenvolvedores.

## 👤 Autor

**Renato Alexandre**

- GitHub: [@rrenatodevs](https://github.com/rrenatodevs)
- LinkedIn: [renato-alexandre](https://www.linkedin.com/in/renato-alexandre-586153324/)
- dev.to: [@rrenatodevs](https://dev.to/rrenatodevs)
