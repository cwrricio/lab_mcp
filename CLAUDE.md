# CLAUDE.md — MCP Lab Sentinel

Este arquivo orienta o Claude Code a desenvolver o projeto **MCP Lab Sentinel**, um servidor MCP para diagnóstico de infraestrutura acadêmica/laboratorial com Raspberry Pi, PCs Linux e hosts acessíveis por SSH.
Utilize UV, Docker, Implemente um README simples. Implemente um teste mínimo.
## Visão geral do projeto

O **MCP Lab Sentinel** é um laboratório prático usando o protocolo **MCP (Model Context Protocol)** para resolver um problema aplicável: diagnosticar dispositivos de um laboratório de redes, IoT ou pesquisa sem depender de comandos manuais repetitivos.

A ideia é permitir que um assistente de IA consulte ferramentas reais e seguras para responder perguntas como:

- Quais máquinas estão online?
- Qual sistema operacional cada Raspberry Pi usa?
- O acesso SSH está funcionando?
- Algum host está com pouco disco ou pouca memória?
- O arquivo `~/.ssh/config` tem inconsistências?
- Gere um relatório do estado atual do laboratório.

O projeto deve ser implementado como um servidor MCP local, expondo ferramentas que executam apenas ações de leitura e diagnóstico.

---

## Objetivo do laboratório

Criar um servidor MCP chamado `lab-sentinel-mcp` que conecte uma IA a ferramentas de diagnóstico de infraestrutura.

O laboratório deve demonstrar:

1. uso real do protocolo MCP;
2. integração com sistema operacional e rede;
3. execução controlada de comandos;
4. análise de hosts cadastrados;
5. geração de relatório técnico;
6. preocupação com segurança.

---

## Problema que o projeto resolve

Em laboratórios acadêmicos, ambientes de IoT e salas com múltiplos Raspberry Pi ou PCs Linux, é comum perder tempo verificando manualmente:

- se os dispositivos estão ligados;
- se respondem na rede;
- qual IP ou alias SSH usar;
- qual sistema operacional está instalado;
- se o SSH está ativo;
- se o disco está quase cheio;
- se há divergência entre os nomes das máquinas e as chaves SSH usadas;
- se o laboratório está pronto para uma aula, experimento ou demonstração.

O **MCP Lab Sentinel** resolve isso criando uma camada padronizada de ferramentas acessíveis por IA.

---

## Stack recomendada

Use preferencialmente:

- Python 3.11+
- MCP Python SDK
- `subprocess` para comandos locais controlados
- `paramiko` para conexões SSH
- `PyYAML` para ler inventário de hosts
- `pytest` para testes
- Markdown para relatórios
- Docker opcional

---

## Estrutura sugerida do projeto

```text
lab-sentinel-mcp/
├── CLAUDE.md
├── README.md
├── pyproject.toml
├── requirements.txt
├── hosts.yaml
├── src/
│   └── lab_sentinel/
│       ├── __init__.py
│       ├── server.py
│       ├── config.py
│       ├── tools.py
│       ├── ssh_client.py
│       ├── diagnostics.py
│       └── report.py
├── tests/
│   ├── test_config.py
│   ├── test_diagnostics.py
│   └── test_report.py
└── examples/
    └── relatorio-exemplo.md
```

---

## Arquivo de inventário

Criar um arquivo `hosts.yaml` com os hosts permitidos.

Exemplo:

```yaml
hosts:
  - name: raspi1-109
    host: 200.132.136.134
    user: emanuel
    port: 22
    identity_file: ~/.ssh/id_ed25519_109
    tags:
      - raspberry
      - laboratorio-109

  - name: raspi1-209
    host: 200.132.136.139
    user: emanuel
    port: 22
    identity_file: ~/.ssh/id_ed25519_209
    tags:
      - raspberry
      - laboratorio-209

  - name: pc209
    host: 200.132.136.139
    user: emanuel
    port: 22
    identity_file: ~/.ssh/id_ed25519_209
    tags:
      - pc
      - laboratorio-209
```

Regra importante: o servidor MCP só pode atuar sobre hosts cadastrados nesse arquivo. Nunca aceitar IP arbitrário enviado diretamente pelo modelo.

---

## Ferramentas MCP obrigatórias

Implementar inicialmente estas ferramentas:

### 1. `list_hosts`

Lista os hosts cadastrados no `hosts.yaml`.

Entrada esperada:

```json
{}
```

Saída esperada:

```json
{
  "hosts": [
    {
      "name": "raspi1-109",
      "host": "200.132.136.134",
      "user": "emanuel",
      "port": 22,
      "tags": ["raspberry", "laboratorio-109"]
    }
  ]
}
```

Não retornar conteúdo sensível, como caminho completo de chaves privadas, se não for necessário.

---

### 2. `ping_host`

Verifica se um host cadastrado responde ao ping.

Entrada:

```json
{
  "name": "raspi1-109"
}
```

Saída:

```json
{
  "name": "raspi1-109",
  "online": true,
  "latency_ms": 23
}
```

Regras:

- aceitar apenas `name`, não IP arbitrário;
- buscar o IP no `hosts.yaml`;
- usar timeout curto;
- retornar erro amigável se o host não existir.

---

### 3. `check_ssh`

Verifica se o host cadastrado aceita conexão SSH.

Entrada:

```json
{
  "name": "raspi1-109"
}
```

Saída:

```json
{
  "name": "raspi1-109",
  "ssh_ok": true,
  "message": "Conexão SSH estabelecida com sucesso."
}
```

Regras:

- não executar comandos destrutivos;
- timeout curto;
- não imprimir senha, chave ou detalhes sensíveis;
- usar apenas hosts cadastrados.

---

### 4. `get_os_info`

Obtém informações do sistema operacional via SSH.

Comandos permitidos:

```bash
cat /etc/os-release
uname -a
hostnamectl
```

Saída:

```json
{
  "name": "raspi1-109",
  "os": "Raspberry Pi OS",
  "version": "Debian GNU/Linux 12 (bookworm)",
  "kernel": "6.6.x",
  "architecture": "aarch64"
}
```

Regras:

- comandos devem estar em whitelist;
- se `hostnamectl` não existir, usar fallback com `uname`;
- tratar hosts offline.

---

### 5. `get_resource_status`

Coleta dados básicos de saúde do host.

Comandos permitidos:

```bash
df -h /
free -m
uptime
systemctl is-active ssh
```

Saída:

```json
{
  "name": "raspi1-109",
  "disk_used_percent": 82,
  "memory_used_percent": 61,
  "uptime": "3 days",
  "ssh_active": true
}
```

Regras:

- não usar `sudo`;
- não instalar pacotes;
- não alterar serviços;
- apenas leitura.

---

### 6. `generate_report`

Gera um relatório consolidado em Markdown.

Entrada:

```json
{
  "filter_tag": "laboratorio-109"
}
```

Saída:

```json
{
  "report_markdown": "# Relatório do Laboratório..."
}
```

O relatório deve conter:

- data/hora da execução;
- hosts analisados;
- status online/offline;
- status SSH;
- sistema operacional;
- uso de disco;
- uso de memória;
- alertas;
- sugestões de ação.

---

## Ferramentas MCP opcionais

Depois do MVP, adicionar:

### `check_ssh_config`

Analisa o arquivo `~/.ssh/config` local e identifica:

- aliases duplicados;
- hosts sem `IdentityFile`;
- hosts sem `ServerAliveInterval`;
- chaves possivelmente inconsistentes com o nome do host;
- uso de `ProxyJump`;
- portas fora do padrão.

Essa ferramenta deve apenas ler o arquivo. Não modificar nada automaticamente.

---

### `suggest_fix`

Gera sugestões seguras com base nos diagnósticos.

Exemplos:

- host offline: verificar energia, cabo, Wi-Fi, IP ou DNS;
- SSH falhou: verificar usuário, chave, porta, firewall;
- disco alto: verificar logs antigos e arquivos temporários;
- memória alta: verificar processos em execução;
- alias confuso: revisar `~/.ssh/config`.

Não executar as correções automaticamente.

---

## Requisitos de segurança

Este projeto deve ser seguro por padrão.

### Proibições

Nunca executar:

```bash
rm
reboot
shutdown
poweroff
mkfs
dd
chmod -R
chown -R
sudo
apt install
apt remove
systemctl restart
systemctl stop
```

### Regras obrigatórias

- Toda ação deve ser read-only.
- Só permitir hosts cadastrados em `hosts.yaml`.
- Não aceitar comandos arbitrários vindos do usuário/modelo.
- Usar whitelist de comandos.
- Usar timeout em ping e SSH.
- Não exibir chaves privadas.
- Não salvar senhas.
- Não usar `StrictHostKeyChecking=no` por padrão.
- Não modificar `~/.ssh/config` automaticamente.
- Não fazer varredura de rede sem autorização.

---

## Fluxo esperado de uso

Usuário pergunta:

```text
Analise o laboratório 109 e me diga quais máquinas estão online, qual SO elas usam e quais problemas precisam de atenção.
```

O cliente MCP deve chamar:

1. `list_hosts`
2. `ping_host` para cada host filtrado
3. `check_ssh` nos hosts online
4. `get_os_info` nos hosts com SSH funcional
5. `get_resource_status`
6. `generate_report`

Resposta esperada:

```markdown
# Relatório do Laboratório 109

## Resumo
Foram analisadas 3 máquinas.

- Online: 2
- Offline: 1
- SSH funcionando: 2
- Alertas críticos: 1

## Hosts

### raspi1-109
- Status: online
- SSH: funcionando
- SO: Raspberry Pi OS / Debian 12
- Disco: 82%
- Memória: 61%

### raspi2-109
- Status: offline
- SSH: não testado

## Alertas
- raspi2-109 não respondeu ao ping.
- raspi1-109 está com uso de disco acima de 80%.

## Sugestões
- Verificar energia e rede do raspi2-109.
- Conferir logs antigos e arquivos temporários em raspi1-109.
```

---

## Critérios de aceite do MVP

O projeto será considerado funcional quando:

- `hosts.yaml` for carregado corretamente;
- `list_hosts` retornar os hosts cadastrados;
- `ping_host` identificar host online/offline;
- `check_ssh` testar acesso SSH;
- `get_os_info` retornar informações reais do sistema;
- `generate_report` produzir Markdown legível;
- houver pelo menos 3 testes automatizados;
- o README explicar como rodar o servidor MCP;
- nenhuma ferramenta executar comandos destrutivos.

---

## Comportamento esperado do Claude Code

Ao trabalhar neste projeto:

1. Priorizar implementação incremental.
2. Criar primeiro o MVP.
3. Escrever código simples e legível.
4. Evitar complexidade desnecessária.
5. Criar funções pequenas e testáveis.
6. Usar type hints em Python.
7. Tratar erros com mensagens úteis.
8. Nunca criar comandos perigosos.
9. Nunca assumir que todos os hosts estão online.
10. Nunca hardcodar dados sensíveis.

---

## Convenções de código

- Linguagem principal: Python.
- Estilo: simples, direto e testável.
- Usar `dataclasses` ou `pydantic` para representar hosts.
- Separar lógica MCP da lógica de diagnóstico.
- Manter comandos permitidos em uma constante.
- Escrever testes para parsing de config e geração de relatório.
- Evitar dependências pesadas sem necessidade.

---

## Exemplo de modelo de dados

```python
from dataclasses import dataclass, field
from typing import list

@dataclass
class LabHost:
    name: str
    host: str
    user: str
    port: int = 22
    identity_file: str | None = None
    tags: list[str] = field(default_factory=list)
```

Ajustar imports conforme necessário. Em Python moderno, usar `list[str]` em vez de `List[str]`.

---

## Erros esperados e tratamento

### Host não cadastrado

Mensagem:

```text
Host 'x' não está cadastrado no inventário.
```

### Host offline

Mensagem:

```text
Host cadastrado, mas não respondeu ao ping dentro do tempo limite.
```

### SSH indisponível

Mensagem:

```text
Host respondeu ao ping, mas a conexão SSH falhou.
```

### Comando não permitido

Mensagem:

```text
Comando bloqueado pela política de segurança do MCP Lab Sentinel.
```

---

## README esperado

O `README.md` deve conter:

1. descrição do problema;
2. proposta da solução;
3. arquitetura;
4. instalação;
5. configuração do `hosts.yaml`;
6. como rodar o servidor MCP;
7. ferramentas disponíveis;
8. exemplos de perguntas;
9. política de segurança;
10. limitações;
11. próximos passos.

---

## Demonstração sugerida

Criar uma demonstração com pelo menos 2 ou 3 hosts.

Caso não existam Raspberry Pi disponíveis, simular os hosts usando:

- localhost;
- containers Docker com SSH;
- VMs Linux;
- mocks nos testes.

A demonstração deve mostrar o modelo perguntando em linguagem natural e usando ferramentas MCP para construir uma resposta baseada em dados reais.

---

## Roadmap

### Fase 1 — MVP

- Carregar `hosts.yaml`
- Implementar `list_hosts`
- Implementar `ping_host`
- Implementar `check_ssh`
- Implementar `get_os_info`
- Implementar `generate_report`

### Fase 2 — Diagnóstico avançado

- Implementar `get_resource_status`
- Implementar `check_ssh_config`
- Implementar alertas
- Implementar relatório com severidade

### Fase 3 — DevSecOps

- Dockerizar o projeto
- Adicionar testes automatizados
- Adicionar GitHub Actions
- Adicionar documentação completa

### Fase 4 — Extensões

- Exportar relatório em arquivo `.md`
- Gerar dashboard simples
- Integrar com banco SQLite
- Histórico de diagnósticos
- Comparar estado atual com execuções anteriores

---

## Limitações conhecidas

- O projeto depende de conectividade com os hosts.
- O acesso SSH precisa estar previamente configurado.
- O servidor não deve corrigir problemas automaticamente.
- O laboratório não deve ser usado para varredura não autorizada.
- O objetivo é diagnóstico defensivo e acadêmico.

---

## Tom do projeto

O projeto deve ser apresentado como uma solução de:

- automação segura;
- diagnóstico de infraestrutura;
- DevSecOps;
- IoT;
- redes;
- apoio a laboratórios acadêmicos.

Evitar apresentar como ferramenta ofensiva ou scanner genérico.

---

## Pitch curto

O **MCP Lab Sentinel** é um servidor MCP que permite a um assistente de IA diagnosticar dispositivos de laboratório, como Raspberry Pi e PCs Linux. Ele verifica conectividade, SSH, sistema operacional e recursos básicos, gerando um relatório técnico com alertas e sugestões. A solução é aplicável em aulas de redes, IoT, sistemas operacionais e DevSecOps, mantendo uma política de segurança read-only e baseada em hosts autorizados.
