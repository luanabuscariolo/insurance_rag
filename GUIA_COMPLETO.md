# Guia Completo — Insurance Claims RAG API

> Este guia explica **cada passo, cada arquivo, cada decisão** do projeto.
> O objetivo não é só fazer funcionar — é entender o **porquê** de cada escolha.
> Leia na ordem. Cada etapa depende da anterior.

---

## Índice

1. [O que este projeto é — e o que não é](#1-o-que-este-projeto-é--e-o-que-não-é)
2. [Conceitos fundamentais antes de começar](#2-conceitos-fundamentais-antes-de-começar)
3. [Pré-requisitos e instalações do sistema](#3-pré-requisitos-e-instalações-do-sistema)
4. [Estrutura de pastas — por que cada uma existe](#4-estrutura-de-pastas--por-que-cada-uma-existe)
5. [Etapa 1 — Dependências Python](#5-etapa-1--dependências-python-requirementstxt)
6. [Etapa 2 — Modelos de dados](#6-etapa-2--modelos-de-dados-appmodelsclaimpython)
7. [Etapa 3 — Banco de dados](#7-etapa-3--banco-de-dados-appdatabasepy)
8. [Etapa 4 — Serviço de sinistros](#8-etapa-4--serviço-de-sinistros-appservicesclaim_servicepy)
9. [Etapa 5 — Serviço RAG](#9-etapa-5--serviço-rag-appservicesrag_servicepy)
10. [Etapa 6 — Rotas da API](#10-etapa-6--rotas-da-api-approutes)
11. [Etapa 7 — Aplicação principal](#11-etapa-7--aplicação-principal-appmainy)
12. [Etapa 8 — Documentos de exemplo](#12-etapa-8--documentos-de-exemplo-datapolicies)
13. [Etapa 9 — Docker](#13-etapa-9--docker)
14. [Como rodar o projeto](#14-como-rodar-o-projeto)
15. [Testando tudo na ordem certa](#15-testando-tudo-na-ordem-certa)
16. [O que acontece por baixo quando você faz uma pergunta](#16-o-que-acontece-por-baixo-quando-você-faz-uma-pergunta)
17. [Erros comuns e como resolver](#17-erros-comuns-e-como-resolver)
18. [O que estudar em seguida](#18-o-que-estudar-em-seguida)

---

## 1. O que este projeto é — e o que não é

### O que é

Uma API REST que faz duas coisas distintas:

**Parte 1 — Gestão de sinistros (backend tradicional)**
Cria, lista, atualiza e remove registros de sinistros de seguro. Dados estruturados num banco SQL. Isso é o que qualquer sistema de seguro faz.

**Parte 2 — Busca inteligente por linguagem natural (RAG)**
Você faz upload de documentos de apólices (em texto). O sistema os processa, armazena o "significado" deles vetorialmente, e permite que você faça perguntas em português e receba respostas baseadas nesses documentos.

### O que não é

Não é um chatbot. Não tem memória de conversa. Não treina nenhum modelo. Não usa machine learning no sentido tradicional. É **engenharia de IA aplicada** — montar peças prontas de forma inteligente.

### Por que o domínio de seguros?

Seguros é um domínio rico em documentos longos e específicos (apólices, manuais, regulamentos), perguntas frequentes dos clientes, e dados estruturados (sinistros, valores, status). É perfeito para demonstrar RAG numa entrevista porque é um caso de uso corporativo real e fácil de explicar.

---

## 2. Conceitos fundamentais antes de começar

Antes de tocar no código, você precisa entender estes conceitos. São o vocabulário da vaga.

### O que é uma API REST

Uma API é uma forma de dois programas conversarem via HTTP. REST é um conjunto de convenções para organizar essa comunicação.

```
Cliente (você, Swagger, app)
        │
        │  HTTP Request: POST /claims
        │  Body: { "claimant_name": "Maria", ... }
        ▼
    Servidor (FastAPI)
        │
        │  Processa, salva no banco
        │
        ▼
    HTTP Response: 201 Created
    Body: { "id": 1, "status": "pending", ... }
```

Os verbos HTTP que usamos:
- `GET` — buscar dados (não muda nada no servidor)
- `POST` — criar algo novo
- `PATCH` — atualizar parcialmente algo existente
- `DELETE` — remover algo

### O que é async/await e por que usamos

Python normalmente executa uma linha de cada vez. Quando precisa esperar algo (banco de dados, API externa), fica parado esperando. Com `async/await`, ele pode fazer outra coisa enquanto espera.

```python
# Síncrono — RUIM para APIs
def get_claim(id):
    result = db.query(id)   # para tudo e espera o banco
    return result           # só aí continua

# Assíncrono — BOM para APIs
async def get_claim(id):
    result = await db.query(id)  # libera o processo enquanto espera
    return result
```

Numa API com 100 usuários simultâneos, isso faz diferença enorme. FastAPI foi construído para isso.

### O que é ORM (SQLAlchemy)

ORM significa Object-Relational Mapper. Em vez de escrever SQL na mão, você trabalha com classes Python e o ORM traduz para SQL automaticamente.

```python
# Sem ORM — SQL na mão
cursor.execute("INSERT INTO claims (name, value) VALUES (?, ?)", ["Maria", 5000])

# Com ORM — Python puro
claim = ClaimDB(claimant_name="Maria", amount_claimed=5000)
db.add(claim)
```

O ORM cuida de criar as tabelas, traduzir os tipos, prevenir SQL injection. Menos código, mais seguro.

### O que é RAG (Retrieval Augmented Generation)

RAG é uma técnica para fazer um LLM (modelo de linguagem como o GPT) responder com base em **seus** documentos, não só no que ele aprendeu durante o treinamento.

Problema sem RAG:
> Você pergunta ao GPT sobre a cláusula 7.3 da sua apólice específica. Ele nunca viu esse documento. Ou inventa (alucinação) ou diz que não sabe.

Solução com RAG:
> Você indexa sua apólice. O sistema encontra o trecho relevante e envia ao GPT como contexto. O GPT responde com base nesse contexto real.

```
SEM RAG:
  Pergunta → LLM → Resposta (possivelmente inventada)

COM RAG:
  Pergunta → Busca nos seus documentos → Trecho relevante → LLM → Resposta fundamentada
```

### O que são Embeddings

Embedding é a representação numérica do **significado** de um texto. Um modelo de embeddings transforma texto em um vetor (lista de números).

```
"prazo para acionar seguro"   → [0.23, -0.71, 0.44, 0.09, ...]  (384 números)
"tempo para comunicar sinistro" → [0.21, -0.68, 0.47, 0.11, ...] (384 números)
"receita de bolo de cenoura"  → [0.89, 0.31, -0.55, 0.72, ...]  (384 números)
```

As duas primeiras frases têm significados parecidos, então os vetores são próximos matematicamente. A terceira é diferente, então o vetor é distante.

Isso permite buscar por **significado**, não por palavras exatas.

### O que é um Vector Database (ChromaDB)

Um banco de dados vetorial armazena embeddings e permite buscar os mais próximos de um embedding dado.

```
Pergunta: "quanto tempo tenho para acionar o seguro?"
    │
    ▼
Embedding da pergunta: [0.23, -0.71, 0.44, ...]
    │
    ▼
ChromaDB compara com todos os embeddings armazenados
    │
    ▼
Retorna os 4 chunks com vetores mais próximos (mais similares em significado)
```

### O que é Chunking

Documentos longos não cabem num único embedding (há limites de tamanho). E mesmo que coubessem, um embedding de um documento inteiro perde precisão — mistura todos os tópicos.

A solução é dividir o documento em pedaços menores (chunks), gerar um embedding para cada chunk, e armazenar separadamente.

```
Apólice completa (5000 chars)
    │
    ▼
Chunk 1: "O seguro cobre colisão, incêndio e roubo..." (500 chars)
Chunk 2: "Para acionar, ligue em até 72 horas..." (500 chars)
Chunk 3: "Os documentos necessários são..." (500 chars)
    ...
    │
    ▼
Embedding de cada chunk → armazenado no ChromaDB
```

O overlap (sobreposição) entre chunks garante que informações na "borda" de um chunk não se percam.

---

## 3. Pré-requisitos e instalações do sistema

### O que você precisa ter instalado no computador

#### Python 3.11 ou superior

Por que 3.11? É a versão com melhor suporte a async, typing moderno (`list[str]` em vez de `List[str]`), e compatível com todas as bibliotecas do projeto.

**Verificar se já tem:**
```bash
python --version
# ou
python3 --version
```

**Instalar (se não tiver):**
- Windows: baixe em https://www.python.org/downloads/ — marque "Add to PATH"
- macOS: `brew install python@3.11`
- Linux (Ubuntu/Debian): `sudo apt install python3.11 python3.11-venv python3-pip`

#### Git

Para versionar o código e publicar no GitHub (essencial para o portfólio).

**Verificar:**
```bash
git --version
```

**Instalar:**
- Windows: https://git-scm.com/download/win
- macOS: `brew install git`
- Linux: `sudo apt install git`

#### Docker Desktop

Para rodar o projeto em container. Opcional para desenvolvimento, mas necessário para simular produção.

**Instalar:**
- Windows e macOS: https://www.docker.com/products/docker-desktop
- Linux: https://docs.docker.com/engine/install/ubuntu/

**Verificar após instalar:**
```bash
docker --version
docker compose version
```

#### Editor de código

Recomendado: **VS Code** (gratuito) com as extensões:
- Python (Microsoft)
- Pylance
- Docker
- REST Client (para testar APIs)

Download: https://code.visualstudio.com/

### Configuração inicial do projeto

```bash
# 1. Crie uma pasta para o projeto
mkdir insurance-rag
cd insurance-rag

# 2. Inicie o git
git init

# 3. Crie o ambiente virtual Python
# Por que ambiente virtual? Para isolar as dependências deste projeto
# das outras instalações Python do seu computador
python -m venv .venv

# 4. ATIVE o ambiente virtual (precisa fazer isso toda vez que abrir o terminal)
# Linux / macOS:
source .venv/bin/activate

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Windows (CMD):
.venv\Scripts\activate.bat

# Você saberá que funcionou quando o terminal mostrar (.venv) no início:
# (.venv) $ _
```

---

## 4. Estrutura de pastas — por que cada uma existe

```
insurance-rag/
│
├── app/                    ← todo o código Python da aplicação
│   ├── __init__.py         ← diz ao Python: "esta pasta é um pacote"
│   ├── main.py             ← ponto de entrada: cria e configura o FastAPI
│   ├── database.py         ← configuração do banco de dados async
│   │
│   ├── models/             ← definição dos dados (forma, tipos, validações)
│   │   ├── __init__.py
│   │   └── claim.py        ← modelo do banco + schemas de request/response
│   │
│   ├── services/           ← lógica de negócio (o que o sistema FAZ)
│   │   ├── __init__.py
│   │   ├── claim_service.py ← operações com sinistros
│   │   └── rag_service.py   ← chunking, embeddings, retrieval, geração
│   │
│   └── routes/             ← endpoints HTTP (o que a API EXPÕE)
│       ├── __init__.py
│       ├── claims.py        ← /claims — CRUD de sinistros
│       ├── documents.py     ← /documents — ingestão de apólices
│       └── search.py        ← /ask — perguntas em linguagem natural
│
├── data/
│   ├── policies/           ← documentos .txt de apólices (input do RAG)
│   │   ├── policy_auto.txt
│   │   ├── policy_home.txt
│   │   └── policy_health.txt
│   ├── chroma/             ← gerado automaticamente: índice vetorial
│   └── insurance.db        ← gerado automaticamente: banco SQLite
│
├── .env.example            ← modelo do arquivo de variáveis de ambiente
├── .env                    ← suas variáveis reais (NUNCA commitar no git)
├── .gitignore              ← lista de arquivos que o git deve ignorar
├── Dockerfile              ← receita para construir a imagem Docker
├── docker-compose.yml      ← configuração para rodar com docker compose
├── requirements.txt        ← lista de dependências Python
├── README.md               ← documentação pública do projeto
└── GUIA_COMPLETO.md        ← este arquivo
```

### Por que separar em models / services / routes?

Esta é a arquitetura em camadas. Cada camada tem uma responsabilidade única:

```
Request HTTP
    │
    ▼
routes/     ← recebe o request, valida com Pydantic, chama o service
    │
    ▼
services/   ← contém a lógica de negócio, acessa o banco/chromadb
    │
    ▼
models/     ← define a estrutura dos dados
    │
    ▼
database    ← persiste no SQLite ou ChromaDB
```

**Por que isso importa?** Se você quiser trocar o banco de dados de SQLite para PostgreSQL, só muda o `database.py`. As rotas e services não mudam. Se quiser mudar a lógica de aprovação de sinistros, só muda o `claim_service.py`. Isso é o que chamam de "código manutenível".

---

## 5. Etapa 1 — Dependências Python (`requirements.txt`)

### O arquivo

```
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
sqlalchemy==2.0.30
aiosqlite==0.20.0
chromadb==0.5.0
sentence-transformers==3.0.0
pypdf==4.2.0
openai==1.30.1
python-multipart==0.0.9
python-dotenv==1.0.1
httpx==0.27.0
```

### O que cada uma faz e por que

**`fastapi`** — o framework web. Cuida de receber requests HTTP, rotear para a função certa, serializar responses. Escolhido por ser async nativo, ter validação automática com Pydantic, e gerar documentação Swagger automaticamente.

**`uvicorn[standard]`** — o servidor HTTP que roda o FastAPI. É o ASGI server. O FastAPI não funciona sem um servidor por baixo. O `[standard]` instala extras para melhor performance (watchfiles, httptools).

**`pydantic`** — validação de dados. Quando chega um JSON no request, o Pydantic verifica se os campos estão corretos, se os tipos batem, e converte automaticamente. Se algo estiver errado, retorna um erro 422 automaticamente sem você precisar escrever código.

**`pydantic-settings`** — extensão do Pydantic para ler variáveis de ambiente. Usamos para carregar `OPENAI_API_KEY` do arquivo `.env`.

**`sqlalchemy`** — ORM para o banco de dados relacional. Permite trabalhar com o banco via Python em vez de SQL puro.

**`aiosqlite`** — adaptador async para SQLite. O SQLite padrão é síncrono. Este pacote permite usar SQLite com async/await, que é necessário para o FastAPI async funcionar corretamente.

**`chromadb`** — o banco de dados vetorial. Armazena embeddings e permite busca por similaridade. Persiste os dados em disco na pasta `data/chroma/`.

**`sentence-transformers`** — biblioteca para gerar embeddings localmente, sem API key, sem custo. O modelo `all-MiniLM-L6-v2` é leve (80MB), rápido, e funciona bem em português e inglês.

**`pypdf`** — para extrair texto de arquivos PDF. Não usamos diretamente neste projeto mas está disponível para evolução futura.

**`openai`** — SDK oficial da OpenAI para chamar o GPT. Opcional: sem a API key, o sistema retorna o contexto recuperado em vez da resposta gerada.

**`python-multipart`** — necessário para o FastAPI aceitar upload de arquivos. Sem este pacote, o endpoint `POST /documents/ingest/file` não funciona.

**`python-dotenv`** — lê o arquivo `.env` e carrega as variáveis de ambiente. Permite ter `OPENAI_API_KEY=sk-...` no `.env` e acessar com `os.getenv("OPENAI_API_KEY")`.

**`httpx`** — cliente HTTP async. O OpenAI SDK usa internamente.

### Como instalar

```bash
# certifique-se que o ambiente virtual está ativo (veja o (.venv) no terminal)
pip install -r requirements.txt

# isso vai demorar um pouco na primeira vez
# o sentence-transformers baixa o modelo (~80MB) na primeira execução
```

---

## 6. Etapa 2 — Modelos de dados (`app/models/claim.py`)

### Por que este arquivo existe

Antes de criar o banco ou a API, você precisa definir **o que é um sinistro**. Este arquivo é o contrato: define os campos, tipos, validações, e como os dados trafegam entre as camadas.

### O que o arquivo contém

**`Base` (SQLAlchemy DeclarativeBase)**

```python
class Base(DeclarativeBase):
    pass
```

Classe base que todas as tabelas do banco precisam herdar. O SQLAlchemy a usa para descobrir quais tabelas criar.

**`ClaimDB` (modelo do banco de dados)**

```python
class ClaimDB(Base):
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, autoincrement=True)
    policy_number = Column(String(50), nullable=False, index=True)
    ...
```

Esta classe representa a **tabela `claims` no banco SQLite**. Cada atributo é uma coluna.

Detalhes importantes:
- `primary_key=True` — identificador único de cada linha
- `autoincrement=True` — o banco gera o número automaticamente (1, 2, 3...)
- `nullable=False` — campo obrigatório, não pode ser vazio
- `index=True` no `policy_number` — cria um índice SQL para buscas por número de apólice serem rápidas

**Por que ter dois modelos (ClaimDB e ClaimCreate)?**

É a separação entre o que existe no banco e o que o usuário envia/recebe.

```
Usuário envia (ClaimCreate):
{
  "policy_number": "POL-001",
  "claimant_name": "Maria",
  "claim_type": "auto",
  "description": "Colisão...",
  "amount_claimed": 8500.00
  # sem id (gerado pelo banco)
  # sem status (começa como "pending")
  # sem created_at (gerado automaticamente)
}

Banco armazena (ClaimDB):
  id: 1
  policy_number: "POL-001"
  claimant_name: "Maria"
  claim_type: "auto"
  description: "Colisão..."
  amount_claimed: 8500.00
  amount_approved: null
  status: "pending"
  created_at: 2024-01-15 10:30:00
  updated_at: 2024-01-15 10:30:00

API responde (ClaimResponse):
  todos os campos acima
```

**`ClaimType` e `ClaimStatus` (Enums)**

```python
class ClaimType(str, Enum):
    auto = "auto"
    home = "home"
    health = "health"
```

Enum é uma lista de valores permitidos. Se o usuário enviar `"carro"` no campo `claim_type`, o Pydantic rejeita automaticamente e retorna um erro claro. Sem Enum, você precisaria validar manualmente.

**`model_config = {"from_attributes": True}` no ClaimResponse**

Isso diz ao Pydantic para aceitar objetos SQLAlchemy como entrada (não só dicionários). Sem isso, `ClaimResponse.model_validate(claim_db_object)` falharia.

---

## 7. Etapa 3 — Banco de dados (`app/database.py`)

### O que o arquivo faz

Configura a conexão com o banco SQLite e define como as sessões são criadas e destruídas.

### Linha por linha

```python
DATABASE_URL = "sqlite+aiosqlite:///./data/insurance.db"
```

A URL de conexão tem um formato específico: `dialeto+driver://caminho`. 
- `sqlite` — tipo do banco
- `aiosqlite` — driver async
- `///./data/insurance.db` — caminho relativo ao arquivo do banco

```python
engine = create_async_engine(DATABASE_URL, echo=False)
```

O engine é a "conexão base" com o banco. `echo=False` desativa o log de SQL no terminal. Mude para `True` durante o desenvolvimento para ver exatamente o SQL gerado — é muito útil para aprender.

```python
AsyncSessionLocal = async_sessionmaker(bind=engine, ...)
```

Factory (fábrica) de sessões. Cada request da API recebe uma sessão própria. Sessão = contexto de trabalho com o banco (equivale a uma transação).

```python
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

Cria as tabelas no banco se não existirem. Chamado uma vez na inicialização da aplicação. `Base.metadata.create_all` examina todas as classes que herdam de `Base` e cria as tabelas correspondentes.

```python
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

Esta é a **Dependency Injection** do FastAPI. O `yield` é o ponto onde o código da rota executa. Se tudo der certo, faz `commit` (salva). Se der erro, faz `rollback` (desfaz). O FastAPI injeta este objeto em cada rota que precisar do banco.

---

## 8. Etapa 4 — Serviço de sinistros (`app/services/claim_service.py`)

### Por que existe uma camada de service?

A rota só deve fazer: receber o request, chamar o service, devolver a response. A lógica de negócio (como calcular, o que validar, o que consultar) fica no service.

Isso facilita testes: você pode testar a lógica do service sem precisar fazer requests HTTP.

### Métodos principais

**`create`**
```python
async def create(self, payload: ClaimCreate) -> ClaimResponse:
    claim = ClaimDB(**payload.model_dump())
    self.db.add(claim)
    await self.db.flush()
    await self.db.refresh(claim)
    return ClaimResponse.model_validate(claim)
```

- `payload.model_dump()` — converte o Pydantic model para dicionário Python
- `ClaimDB(**dict)` — cria instância do ORM com os dados
- `db.add(claim)` — adiciona à sessão (ainda não salvou no banco)
- `db.flush()` — envia para o banco mas não commita (nos dá o `id` gerado)
- `db.refresh(claim)` — busca os dados atualizados do banco (incluindo `id`, `created_at`)

**`list_claims` — demonstra query SQL com filtros**
```python
query = select(ClaimDB)
if status:
    query = query.where(ClaimDB.status == status.value)
```

Isso traduz para: `SELECT * FROM claims WHERE status = 'pending'`. O SQLAlchemy monta a query incrementalmente — você adiciona filtros condicionalmente sem precisar de string concatenation.

**`get_stats` — demonstra GROUP BY com SQLAlchemy**
```python
select(
    ClaimDB.status,
    func.count(ClaimDB.id).label("count"),
    func.sum(ClaimDB.amount_claimed).label("total_claimed"),
    func.avg(ClaimDB.amount_claimed).label("avg_claimed"),
).group_by(ClaimDB.status)
```

SQL equivalente:
```sql
SELECT status, COUNT(id), SUM(amount_claimed), AVG(amount_claimed)
FROM claims
GROUP BY status;
```

---

## 9. Etapa 5 — Serviço RAG (`app/services/rag_service.py`)

Este é o arquivo mais importante para a vaga. Leia com atenção.

### Configurações globais

```python
CHROMA_PATH = "./data/chroma"     # onde o índice vetorial é salvo em disco
EMBED_MODEL = "all-MiniLM-L6-v2" # modelo de embedding gratuito
CHUNK_SIZE = 500                  # tamanho de cada pedaço do documento
CHUNK_OVERLAP = 80                # sobreposição entre chunks
TOP_K = 4                         # quantos chunks retornar por busca
```

**Por que `all-MiniLM-L6-v2`?**
- É gratuito (roda localmente, sem API key)
- Tamanho pequeno (~80MB)
- Gera vetores de 384 dimensões — bom equilíbrio entre qualidade e velocidade
- Funciona bem em português e inglês
- Em produção, você trocaria por `text-embedding-3-small` da OpenAI

### `__init__` — inicialização

```python
def __init__(self) -> None:
    self._embedder = SentenceTransformer(EMBED_MODEL)
    
    self._chroma = chromadb.PersistentClient(path=CHROMA_PATH)
    self._collection = self._chroma.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
```

O modelo de embedding é carregado uma vez quando o servidor inicia e fica em memória. Carregar a cada request seria lento demais.

`{"hnsw:space": "cosine"}` — define o algoritmo de similaridade. Cosseno mede o ângulo entre vetores (ignora magnitude, foca direção). É o mais usado para comparação de textos.

### Método `_split_into_chunks` — Chunking

```python
def _split_into_chunks(self, text: str) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()  # normaliza espaços
    chunks = []
    start = 0

    while start < len(text):
        end = start + CHUNK_SIZE
        chunk = text[start:end]

        # tenta terminar no fim de uma frase
        last_period = max(chunk.rfind(". "), chunk.rfind(".\n"), chunk.rfind("! "))
        if last_period > CHUNK_SIZE * 0.5:
            end = start + last_period + 1
            chunk = text[start:end]

        chunks.append(chunk.strip())
        start = end - CHUNK_OVERLAP   # ← aqui está o overlap

    return [c for c in chunks if len(c) > 50]
```

**Por que terminar no fim de uma frase?** Um chunk que termina no meio de uma frase perde contexto. "O prazo para acionar é de 72" — 72 quê? Se terminar em ". ", o chunk fica completo.

**Por que o overlap?** Se uma informação está no final do chunk 3 e no início do chunk 4, sem overlap só um dos chunks a teria. Com overlap de 80 chars, essa borda aparece em ambos. Quando a pergunta é sobre essa informação, pelo menos um dos chunks é recuperado.

### Método `ingest_document` — Ingestão

```python
async def ingest_document(self, content, source_name, policy_type):
    chunks = self._split_into_chunks(content)       # divide em pedaços
    embeddings = self._embed(chunks)                 # transforma em vetores
    
    self._collection.add(
        documents=chunks,       # texto original de cada chunk
        embeddings=embeddings,  # vetor numérico de cada chunk
        metadatas=metadatas,    # info extra: fonte, tipo de apólice
        ids=ids,                # id único de cada chunk
    )
```

O ChromaDB armazena três coisas juntas:
1. O texto original do chunk (para você poder ler a resposta)
2. O embedding (para buscar por similaridade)
3. Os metadados (para filtrar por tipo de apólice)

### Método `retrieve` — Retrieval

```python
def retrieve(self, query: str, policy_type=None, n_results=TOP_K):
    query_embedding = self._embed([query])   # transforma a pergunta em vetor
    
    results = self._collection.query(
        query_embeddings=query_embedding,
        n_results=n_results,
        where=where_filter,                  # opcional: filtra por tipo
        include=["documents", "metadatas", "distances"],
    )
    
    # distance é de 0 a 2 em cosseno; convertemos para relevância (0 a 1)
    "relevance_score": round(1 - dist, 4)
```

**Como funciona a busca?**

O ChromaDB usa HNSW (Hierarchical Navigable Small World), um algoritmo de busca aproximada em vetores de alta dimensão. Ele não compara o vetor da query com todos os vetores armazenados (isso seria lento com milhões de chunks). Em vez disso, navega por uma estrutura de grafo hierárquica para encontrar os mais próximos rapidamente.

### Método `answer` — O pipeline RAG completo

```python
async def answer(self, question, policy_type=None):
    # 1. Recupera chunks relevantes
    retrieved_chunks = self.retrieve(question, policy_type)
    
    # 2. Monta o contexto
    context = "\n\n---\n\n".join(
        f"[Fonte: {c['source']}]\n{c['content']}"
        for c in retrieved_chunks
    )
    
    # 3. Gera resposta
    if OPENAI_API_KEY:
        answer_text = await self._generate_with_openai(question, context)
    else:
        answer_text = "Contexto recuperado:\n\n" + context
    
    return {"question": question, "answer": answer_text, "sources": [...]}
```

### Método `_generate_with_openai` — Geração com grounding

```python
messages=[
    {
        "role": "system",
        "content": (
            "Você é um assistente especializado em seguros. "
            "Responda APENAS com base no contexto fornecido. "   # ← grounding
            "Se a resposta não estiver no contexto, diga que não encontrou."
            f"CONTEXTO:\n{context}"
        ),
    },
    {"role": "user", "content": question},
]
```

**O que é grounding?** A instrução "Responda APENAS com base no contexto" é o grounding. Sem ela, o GPT poderia misturar o contexto dos seus documentos com coisas que aprendeu durante o treinamento — o que pode causar alucinações ou respostas incorretas para o seu caso específico.

`temperature=0.1` — controla a "criatividade" do modelo. 0 = determinístico (sempre a mesma resposta). 1 = mais criativo/randômico. Para respostas factuais sobre apólices, queremos baixa temperatura.

---

## 10. Etapa 6 — Rotas da API (`app/routes/`)

### Como funciona o roteamento

Cada arquivo de route é um `APIRouter` — um conjunto de endpoints relacionados. O `main.py` inclui todos os routers na app principal.

### `claims.py` — CRUD de sinistros

**Dependency Injection em ação:**

```python
def get_service(db: AsyncSession = Depends(get_db)) -> ClaimService:
    return ClaimService(db)

@router.post("")
async def create_claim(
    payload: ClaimCreate,
    service: ClaimService = Depends(get_service),
) -> ClaimResponse:
    return await service.create(payload)
```

O FastAPI lê os parâmetros com `Depends(...)` e os resolve automaticamente antes de chamar a função:

1. Chama `get_db()` → cria sessão de banco
2. Passa a sessão para `get_service()` → cria `ClaimService`
3. Passa o service para `create_claim()` → você usa normalmente
4. Quando a função termina, `get_db()` faz commit ou rollback

**Por que `response_model=ClaimResponse`?**

Garante que a resposta seja serializada exatamente como definido no Pydantic model. Se o serviço retornar campos extras, eles são removidos. Se campos obrigatórios estiverem faltando, dá erro. Aparece no Swagger como documentação automática.

**Filtros de query:**

```python
@router.get("")
async def list_claims(
    status: Optional[ClaimStatus] = Query(None),
    claim_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
):
```

`Query(None)` diz ao FastAPI que este parâmetro vem da query string da URL (`?status=pending&limit=10`), não do corpo do request. `ge=0` (greater or equal) e `le=100` (less or equal) são validações automáticas.

### `documents.py` — Ingestão de documentos

```python
@router.post("/ingest/seed")
async def ingest_seed_data():
    txt_files = list(policies_dir.glob("*.txt"))
    for file_path in txt_files:
        content = file_path.read_text(encoding="utf-8")
        # infere tipo pelo nome do arquivo
        if "auto" in name:
            policy_type = "auto"
```

Este endpoint lê todos os `.txt` da pasta `data/policies/` e os indexa. É um atalho para testar sem precisar fazer uploads manuais. A inferência do tipo pelo nome é simples mas funcional para o projeto.

### `search.py` — Perguntas RAG

```python
@router.get("/retrieve")
async def retrieve_only(q: str, policy_type=None, n: int = 4):
    chunks = rag.retrieve(q, policy_type, n)
    return {"query": q, "chunks_retrieved": len(chunks), "chunks": chunks}
```

Este endpoint de debug é muito útil para entender o que está acontecendo. Antes de gastar tokens com o GPT, você pode ver exatamente quais chunks seriam enviados como contexto. Se a relevância for baixa (`< 0.5`), seus documentos provavelmente não têm informação sobre aquela pergunta.

---

## 11. Etapa 7 — Aplicação principal (`app/main.py`)

### O Lifespan

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- código aqui roda NA INICIALIZAÇÃO ---
    Path("./data/policies").mkdir(parents=True, exist_ok=True)
    await init_db()

    yield  # ← a aplicação fica rodando aqui

    # --- código aqui roda NO ENCERRAMENTO ---
    print("Encerrando...")
```

O `lifespan` substitui os antigos `@app.on_event("startup")` e `shutdown`. Tudo antes do `yield` executa quando o servidor inicia. Tudo depois executa quando o servidor para.

### CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
```

CORS (Cross-Origin Resource Sharing) é uma política de segurança do navegador que bloqueia requests para domínios diferentes. Durante o desenvolvimento, `allow_origins=["*"]` aceita qualquer origem. Em produção, você listaria apenas os domínios do seu frontend.

---

## 12. Etapa 8 — Documentos de exemplo (`data/policies/`)

### O que são

Três arquivos `.txt` que simulam apólices reais de seguros:

- `policy_auto.txt` — cobertura, prazos, franquias, documentos necessários para seguro auto
- `policy_home.txt` — cobertura residencial, procedimentos, exclusões
- `policy_health.txt` — coberturas obrigatórias ANS, carências, reembolso

### Por que arquivos de texto e não PDF?

PDF requer extração de texto (a biblioteca `pypdf` faz isso), o que adiciona complexidade. Para o projeto de aprendizado, `.txt` é suficiente para demonstrar o RAG. Em produção, você adicionaria a extração de PDF.

### Como adicionar seus próprios documentos

Crie um arquivo `.txt` em `data/policies/` com o nome seguindo a convenção:

```
policy_auto_2024.txt    → será identificado como tipo "auto"
policy_home_premium.txt → será identificado como tipo "home"
policy_health_plus.txt  → será identificado como tipo "health"
outro_documento.txt     → será identificado como tipo "general"
```

Depois chame `POST /documents/ingest/seed` novamente.

---

## 13. Etapa 9 — Docker

### O que o Docker resolve

"Funciona na minha máquina" é um problema clássico. Docker cria um ambiente idêntico em qualquer computador ou servidor. Você descreve o ambiente no `Dockerfile` e o Docker garante que vai funcionar igual em qualquer lugar.

### `Dockerfile` — linha por linha

```dockerfile
FROM python:3.11-slim AS builder
```

Usa a imagem oficial do Python 3.11 "slim" (sem ferramentas desnecessárias) como base. `AS builder` nomeia este estágio para o multi-stage build.

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential gcc
```

Instala compiladores necessários para algumas dependências Python (como `chromadb`) que têm código C por baixo. `--no-install-recommends` evita pacotes desnecessários.

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
```

Instala as dependências. Isso é feito antes de copiar o código por um motivo importante: o Docker cacheia camadas. Se você mudar só o código (não o `requirements.txt`), o Docker reutiliza a camada de dependências instaladas — o rebuild fica muito mais rápido.

```dockerfile
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
```

Segundo estágio: nova imagem limpa, copiando apenas o que foi instalado (sem compiladores). A imagem final fica menor (~40% menor que se fosse num único estágio).

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"
```

O Docker verifica periodicamente se o container está saudável. O `start-period=60s` dá tempo para o modelo de embeddings carregar na primeira inicialização.

### `docker-compose.yml`

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"      # porta_do_host:porta_do_container
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    volumes:
      - ./data:/app/data  # sincroniza a pasta local com o container
```

`volumes: - ./data:/app/data` é crucial. Sem ele, o banco SQLite e o índice ChromaDB existem apenas dentro do container. Quando o container é reiniciado, tudo se perde. Com o volume, os dados ficam na sua pasta local e persistem entre reinicializações.

---

## 14. Como rodar o projeto

### Opção A — Sem Docker (mais simples para desenvolvimento)

```bash
# 1. Ative o ambiente virtual
source .venv/bin/activate   # Linux/macOS
# ou
.venv\Scripts\activate      # Windows

# 2. Instale as dependências (só na primeira vez)
pip install -r requirements.txt

# 3. Configure variáveis de ambiente
cp .env.example .env
# edite o .env se tiver API key da OpenAI

# 4. Crie as pastas necessárias
mkdir -p data/policies data/chroma

# 5. Copie os documentos de exemplo para data/policies/
# (se estiver usando o projeto gerado, já estão lá)

# 6. Inicie a API
uvicorn app.main:app --reload --port 8000
# --reload: reinicia automaticamente quando você salva um arquivo Python
```

### Opção B — Com Docker

```bash
# 1. Construa a imagem e inicie
docker compose up --build

# --build: reconstrói a imagem (necessário quando muda requirements.txt ou Dockerfile)
# na próxima vez, pode rodar só: docker compose up

# Para rodar em background (sem travar o terminal):
docker compose up -d

# Para ver os logs:
docker compose logs -f

# Para parar:
docker compose down
```

### Verificando que funcionou

Abra o navegador em `http://localhost:8000/docs`

Você deve ver o Swagger UI com todos os endpoints documentados. Se aparecer, a API está funcionando.

---

## 15. Testando tudo na ordem certa

### Passo 1 — Verificar saúde da API

```bash
curl http://localhost:8000/health
```

Resposta esperada: `{"status": "ok", "service": "insurance-rag-api"}`

### Passo 2 — Indexar os documentos de exemplo

```bash
curl -X POST http://localhost:8000/documents/ingest/seed
```

Resposta esperada:
```json
{
  "seeded": 3,
  "details": [
    {"source": "policy_auto.txt", "chunks_created": 14, "total_chars": 3847},
    {"source": "policy_home.txt", "chunks_created": 16, "total_chars": 4201},
    {"source": "policy_health.txt", "chunks_created": 18, "total_chars": 4530}
  ]
}
```

### Passo 3 — Verificar o índice vetorial

```bash
curl http://localhost:8000/documents/stats
```

Resposta: `{"total_chunks": 48, "collection": "insurance_policies", "embed_model": "all-MiniLM-L6-v2"}`

### Passo 4 — Testar o retrieval (sem gerar resposta)

```bash
curl "http://localhost:8000/ask/retrieve?q=prazo+para+acionar+seguro+auto"
```

Veja os chunks retornados e as notas de relevância. Scores acima de 0.7 indicam boa correspondência.

### Passo 5 — Fazer uma pergunta completa (RAG)

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Qual o prazo para comunicar um sinistro de colisão?", "policy_type": "auto"}'
```

### Passo 6 — Criar sinistros

```bash
curl -X POST http://localhost:8000/claims \
  -H "Content-Type: application/json" \
  -d '{
    "policy_number": "POL-2024-001",
    "claimant_name": "Maria Silva",
    "claim_type": "auto",
    "description": "Colisão traseira na Av. Paulista. Danos no para-choque e mala.",
    "amount_claimed": 8500.00
  }'
```

### Passo 7 — Listar com filtros

```bash
# todos os sinistros pendentes
curl "http://localhost:8000/claims?status=pending"

# sinistros de auto com paginação
curl "http://localhost:8000/claims?claim_type=auto&skip=0&limit=5"
```

### Passo 8 — Atualizar status

```bash
curl -X PATCH http://localhost:8000/claims/1/status \
  -H "Content-Type: application/json" \
  -d '{"status": "approved", "amount_approved": 7200.00}'
```

### Passo 9 — Ver estatísticas SQL

```bash
curl http://localhost:8000/claims/stats/summary
```

---

## 16. O que acontece por baixo quando você faz uma pergunta

Rastrear uma pergunta do início ao fim é o melhor exercício para entender o sistema:

```
POST /ask
Body: {"question": "O seguro cobre alagamento?", "policy_type": "home"}

    │
    ▼
app/routes/search.py
└─ ask_question(payload)
   └─ payload.question = "O seguro cobre alagamento?"
   └─ payload.policy_type = "home"
   └─ chama rag.answer(...)

    │
    ▼
app/services/rag_service.py
└─ answer(question, policy_type)
   │
   ├─ retrieve(question, policy_type="home")
   │  ├─ _embed(["O seguro cobre alagamento?"])
   │  │  └─ SentenceTransformer processa o texto
   │  │  └─ retorna: [0.21, -0.43, 0.67, ...]  (384 números)
   │  │
   │  ├─ ChromaDB.query(
   │  │    query_embeddings=[[0.21, -0.43, 0.67, ...]],
   │  │    n_results=4,
   │  │    where={"policy_type": "home"}
   │  │  )
   │  │  └─ compara com todos os embeddings do tipo "home"
   │  │  └─ retorna os 4 chunks com menor distância de cosseno
   │  │
   │  └─ retorna: [
   │       {content: "A cobertura de alagamento cobre...", relevance: 0.89},
   │       {content: "Para acionar a cobertura de alagamento...", relevance: 0.81},
   │       ...
   │     ]
   │
   ├─ monta contexto:
   │  "[Fonte: policy_home.txt]
   │  A cobertura de alagamento cobre danos causados pela entrada de água...
   │  ---
   │  [Fonte: policy_home.txt]
   │  Para acionar a cobertura de alagamento, é necessário..."
   │
   └─ _generate_with_openai(question, context)
      ├─ system: "Responda APENAS com base no contexto: [contexto acima]"
      ├─ user: "O seguro cobre alagamento?"
      └─ GPT-4o-mini gera resposta baseada no contexto

    │
    ▼
Response HTTP 200:
{
  "question": "O seguro cobre alagamento?",
  "answer": "Sim, o seguro residencial cobre alagamento como cobertura opcional...",
  "sources": [{"source": "policy_home.txt", "relevance": 0.89}]
}
```

---

## 17. Erros comuns e como resolver

### `ModuleNotFoundError: No module named 'fastapi'`

O ambiente virtual não está ativo.

```bash
source .venv/bin/activate   # Linux/macOS
```

### `Address already in use` (porta 8000)

Outro processo está usando a porta.

```bash
# descubra quem está usando
lsof -i :8000   # Linux/macOS
netstat -ano | findstr :8000   # Windows

# mate o processo (substitua PID pelo número encontrado)
kill -9 PID   # Linux/macOS

# ou simplesmente use outra porta
uvicorn app.main:app --port 8001
```

### `RuntimeError: asyncio.run() cannot be called from a running event loop`

Você está tentando rodar código async de forma síncrona. Use `await` dentro de funções `async def`, não `asyncio.run()`.

### O modelo de embeddings demora para carregar

Normal. Na primeira inicialização, o `sentence-transformers` baixa o modelo (~80MB). Subsequentes inicializações são rápidas (carrega do cache). Com Docker, o `start-period=60s` no healthcheck dá tempo para isso.

### ChromaDB retorna 0 resultados

Você ainda não indexou nada. Execute:

```bash
curl -X POST http://localhost:8000/documents/ingest/seed
```

### `422 Unprocessable Entity`

O Pydantic rejeitou o payload. Leia o corpo da resposta de erro — ele diz exatamente qual campo falhou e por quê.

```json
{
  "detail": [
    {
      "loc": ["body", "amount_claimed"],
      "msg": "Input should be greater than 0",
      "type": "greater_than"
    }
  ]
}
```

---

## 18. O que estudar em seguida

Depois de fazer este projeto funcionar e entender cada parte, estes são os próximos passos naturais:

### Melhorias no RAG

**Hybrid Search** — combinar busca vetorial (semântica) com busca BM25 (por palavras-chave). Nem sempre a busca semântica é superior; às vezes o usuário usa um termo técnico exato e a busca por keyword funciona melhor. A combinação dos dois é o estado da arte atual.

**Reranking** — após recuperar os top-10 chunks por embedding, usar um modelo de reranking (ex: `cross-encoder/ms-marco-MiniLM-L-6-v2`) para reordenar pelo mais relevante para a pergunta específica. Melhora muito a qualidade da resposta.

**Avaliação do RAG** — como saber se o sistema está funcionando bem? Bibliotecas como `RAGAs` permitem medir métricas como faithfulness (a resposta está no contexto?) e answer relevancy (a resposta responde a pergunta?).

### Melhorias na infraestrutura

**PostgreSQL + pgvector** — em produção, substituir SQLite por PostgreSQL e ChromaDB por pgvector (extensão do Postgres que faz busca vetorial). Elimina um banco e simplifica o deployment.

**Autenticação JWT** — proteger os endpoints com tokens. O FastAPI tem excelente suporte para OAuth2 com JWT.

**Testes com pytest** — escrever testes unitários para os services e testes de integração para as rotas. O FastAPI tem o `TestClient` que permite testar sem subir o servidor real.

**LangSmith ou Phoenix** — ferramentas de observabilidade para RAG. Permitem ver cada chamada ao LLM, o contexto enviado, e rastrear problemas.

### Frameworks de orquestração (o que a vaga pede)

Depois de entender o RAG do zero neste projeto, estudar:

- **LangGraph** — para sistemas com múltiplos agentes e fluxos condicionais
- **Semantic Kernel** — solução da Microsoft, bem integrada com Azure
- **AutoGen** — para sistemas multiagente com comunicação entre agentes

A diferença entre este projeto e esses frameworks é que aqui você fez tudo manualmente. Os frameworks abstraem o chunking, embedding, retrieval e orquestração — mas sem entender o que está por baixo (que agora você entende), usar os frameworks é difícil.

### Recursos recomendados

- Documentação oficial do FastAPI: https://fastapi.tiangolo.com
- SQLAlchemy async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- ChromaDB docs: https://docs.trychroma.com
- Curso RAG — DeepLearning.AI (gratuito): https://www.deeplearning.ai/short-courses/langchain-chat-with-your-data/
- Azure AI Search docs: https://learn.microsoft.com/azure/search/
