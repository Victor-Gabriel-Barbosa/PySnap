<div align="center">

# 📸 PySnapper

**Rastreie um site inteiro e capture screenshots de todas as páginas automaticamente.**

[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/powered%20by-Playwright-2EAD33?logo=playwright&logoColor=white)](https://playwright.dev/python/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](#contribuindo)

</div>

---

## 📖 Sobre o projeto

**PySnapper** é uma ferramenta de linha de comando escrita em Python que percorre (crawla) um site a partir de uma URL inicial e tira um **screenshot** de cada página que encontra pelo caminho, usando o [Playwright](https://playwright.dev/python/) para automatizar um navegador Chromium.

Ele funciona como um pequeno "robô de navegação": abre a página inicial, tira o print, extrai todos os links `<a href>` encontrados, coloca-os em uma fila e repete o processo — respeitando limites de profundidade, quantidade máxima de páginas e domínio — até esgotar a fila ou atingir o limite configurado.

É útil para:

- 🗂️ Gerar um inventário visual de todas as páginas de um site;
- 🔍 Auditorias de QA/design (comparar layout entre páginas);
- 🕰️ Documentar o estado de um site em um momento específico (antes de uma migração, por exemplo);
- 🐛 Encontrar páginas quebradas ou com erro de carregamento durante o rastreamento.

## ✨ Funcionalidades

- **Rastreamento em largura (BFS)** a partir de uma URL inicial, com fila de páginas visitadas.
- **Screenshot de página inteira** (`full_page`) ou apenas da área visível (viewport).
- **Controle de profundidade** (`--depth`) e **limite de páginas** (`--max-pages`).
- **Restrição de domínio**: por padrão só segue links do mesmo domínio da URL inicial (`--all-domains` libera outros domínios).
- **Scroll automático até o final da página** antes do print, para acionar lazy loading de imagens/conteúdo (`--scroll-to-bottom`).
- **Viewport configurável** (largura/altura) para simular diferentes resoluções.
- **Modo headless ou visual** (`--no-headless` mostra a janela do navegador).
- **Delay configurável** entre páginas, para não sobrecarregar o servidor de destino.
- **Nomes de arquivo seguros**, derivados automaticamente da URL de cada página.
- **Relatório final** com total de páginas visitadas, screenshots salvos e lista de erros.

## 🧰 Pré-requisitos

- Python **3.10** ou superior (o projeto usa a sintaxe `int | None`, disponível a partir do Python 3.10);
- Acesso à internet para instalar dependências e para rastrear o site de destino.

## 📦 Instalação

Clone o repositório e instale as dependências:

```bash
git clone https://github.com/Victor-Gabriel-Barbosa/PySnapper.git
cd PySnapper

# (opcional, mas recomendado) crie um ambiente virtual
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# instale as dependências do projeto
pip install -r requirements.txt

# baixe o navegador Chromium usado pelo Playwright
playwright install chromium
```

## 🚀 Uso

Uso básico — informe apenas a URL inicial:

```bash
python main.py https://exemplo.com
```

Por padrão, o PySnapper salva os screenshots na pasta `screenshots/`, visita no máximo 50 páginas, tira o print da página inteira e segue apenas links do mesmo domínio.

### Opções disponíveis

| Opção                  | Descrição                                                            | Padrão        |
| ----------------------- | --------------------------------------------------------------------- | -------------- |
| `-o`, `--output`        | Pasta de saída para os screenshots                                   | `screenshots` |
| `-m`, `--max-pages`     | Número máximo de páginas a visitar                                    | `50`          |
| `-d`, `--depth`         | Profundidade máxima de navegação a partir da URL inicial              | sem limite    |
| `--all-domains`         | Permite seguir links para outros domínios                             | desativado    |
| `--no-headless`         | Mostra a janela do navegador em vez de rodar oculto                   | headless      |
| `--viewport-only`       | Tira o print só da área visível, em vez da página inteira             | página inteira |
| `--scroll-to-bottom`    | Faz scroll até o final da página antes do screenshot (lazy loading)    | desativado    |
| `--delay`               | Delay em segundos entre uma página e outra                            | `1.0`         |
| `--width`               | Largura da viewport, em pixels                                        | `1366`        |
| `--height`              | Altura da viewport, em pixels                                         | `768`         |

### Exemplos

Rastrear até 30 páginas, com profundidade máxima de 2 níveis:

```bash
python main.py https://meusite.com.br -o prints -m 30 -d 2
```

Capturar apenas a área visível, em resolução mobile:

```bash
python main.py https://meusite.com.br --viewport-only --width 390 --height 844
```

Ativar scroll até o final da página, útil em sites com carregamento sob demanda (lazy loading):

```bash
python main.py https://meusite.com.br --scroll-to-bottom
```

Ver o navegador em ação (útil para depuração) e seguir links para outros domínios:

```bash
python main.py https://meusite.com.br --no-headless --all-domains
```

## ⚙️ Como funciona

1. A URL inicial entra em uma fila junto com sua profundidade (`0`).
2. Enquanto houver itens na fila e o limite de páginas não tiver sido atingido, o PySnapper:
   - Remove a próxima URL da fila e verifica se já foi visitada ou se excede a profundidade máxima;
   - Carrega a página no Chromium e aguarda a rede ficar ociosa (`networkidle`);
   - (Opcional) Faz scroll incremental até o final da página para acionar lazy loading;
   - Tira o screenshot e salva com um nome de arquivo gerado a partir da URL;
   - Extrai todos os links `<a href>` da página e adiciona à fila os que ainda não foram visitados (respeitando a restrição de domínio, se ativa);
   - Aguarda o delay configurado antes de seguir para a próxima página.
3. Ao final, exibe um resumo com o total de páginas visitadas, screenshots salvos e eventuais erros encontrados.

## 🗃️ Estrutura do projeto

```
PySnapper/
├── main.py          # script principal (CLI + lógica de rastreamento)
├── LICENSE          # licença MIT
├── requirements.txt # dependências
├── .gitattributes
├── .gitignore
└── README.md
```

## 🖼️ Saída

Os screenshots são salvos como arquivos `.png`, com nomes derivados do domínio, caminho e query string da URL (por exemplo, `exemplo_com_sobre.png`). Ao final da execução, um resumo é impresso no terminal com o número de páginas visitadas, screenshots salvos com sucesso e a lista de páginas que falharam (com o respectivo erro).

## ⚠️ Limitações e observações

- Sites que exigem **login/autenticação** não são suportados nativamente.
- O tempo de espera `networkidle` pode deixar o rastreamento mais lento em sites com conexões persistentes (WebSockets, analytics contínuo, etc.).
- Sites muito grandes podem gerar um número elevado de páginas — ajuste `--max-pages` e `--depth` para controlar o escopo do rastreamento.
- Respeite sempre o `robots.txt` e os termos de uso do site de destino antes de rastreá-lo.

## 🤝 Contribuindo

Contribuições são bem-vindas! Para contribuir:

1. Faça um fork do repositório;
2. Crie uma branch para sua feature/correção (`git checkout -b minha-feature`);
3. Commit suas alterações (`git commit -m 'Adiciona minha feature'`);
4. Envie para o seu fork (`git push origin minha-feature`);
5. Abra um Pull Request descrevendo a mudança.

Sinta-se à vontade também para abrir uma [issue](https://github.com/Victor-Gabriel-Barbosa/PySnapper/issues) relatando bugs ou sugerindo melhorias.

## 📄 Licença

Este projeto está licenciado sob os termos da licença **MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👤 Autor

Desenvolvido por [**Victor Gabriel Barbosa**](https://github.com/Victor-Gabriel-Barbosa).

---

<div align="center">

Se este projeto foi útil para você, considere deixar uma ⭐!

</div>
