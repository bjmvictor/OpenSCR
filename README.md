<a id="readme-top"></a>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
[![Windows][windows-shield]][windows-url]

<br />

<div align="center">
  <a href="https://github.com/bjmvictor/OpenSCR">
    <img src="assets/splash.png" alt="OpenSCR" width="400" height="400">
  </a>

  <h2 align="center">OpenSCR</h2>

  <p align="center">
    <strong>Open-source Windows Screensaver Creator</strong>
    <br />
    Crie protetores de tela personalizados para Windows com imagens, textos dinâmicos, variáveis e efeitos de transição.
    <br />
    <br />
    <a href="https://github.com/bjmvictor/OpenSCR/issues">Reportar problema</a>
    ·
    <a href="https://github.com/bjmvictor/OpenSCR/issues">Solicitar funcionalidade</a>
  </p>
</div>

---

## Sobre o projeto

O **OpenSCR** é uma aplicação open source para criação de protetores de tela personalizados para Windows.

O projeto busca oferecer uma alternativa gratuita, moderna e simples às ferramentas proprietárias de criação de arquivos `.scr`, permitindo configurar todo o protetor de tela através de uma interface gráfica.

Entre os principais objetivos estão:

- simplificar a criação de screensavers para Windows;
- permitir personalização sem necessidade de programação;
- oferecer efeitos e transições configuráveis;
- permitir textos e informações dinâmicas na tela;
- disponibilizar uma ferramenta aberta para uso pessoal, corporativo e comunitário;
- evoluir para um editor visual completo de protetores de tela.

> O OpenSCR está em desenvolvimento ativo. Recursos, formatos de projeto e métodos de exportação podem sofrer alterações durante as versões iniciais.

```Atenção: Apenas imagens (PNG, JPG, etc.) são suportadas. Não tem suporte para arquivos de vídeo no momento.```

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Principais funcionalidades

### Slideshow

- Seleção de múltiplas imagens.
- Controle do tempo de exibição.
- Ajuste da imagem para preencher ou conter na tela.
- Suporte a múltiplos monitores.
- Fundo configurável.

### Transições

- Fade.
- Degradê.
- Slide para esquerda.
- Slide para direita.
- Slide para cima.
- Slide para baixo.
- Zoom.
- Seleção aleatória de efeitos.
- Controle independente da duração da transição.

### Textos dinâmicos

O OpenSCR permite adicionar textos sobre o protetor de tela utilizando conteúdo personalizado e variáveis que são atualizadas durante a execução.

Exemplo:

```text
Hoje é {weekday}, {date}
{time_seconds}

Computador: {computer}
```

Entre as variáveis disponíveis estão:

```text
{date}
{time}
{time_seconds}
{date_time}

{day}
{weekday}
{month}
{month_name}
{year}

{computer}
{user}
{os}
```

Também é possível configurar:

- posição;
- tamanho;
- cor;
- margem;
- exibição ou ocultação do texto.

Na caixa de texto, selecione um trecho e use os controles de formatação para
aplicar negrito, itálico ou tamanho diferente. O formato é salvo no projeto e
interpretado pelo runtime nativo com estas marcações:

```text
[b]negrito[/b]
[i]itálico[/i]
[size=48]texto maior[/size]
```

### Preview

As configurações podem ser visualizadas em tela cheia antes da exportação.

O preview reproduz as imagens, textos, variáveis e transições configuradas no projeto.

### Exportação

O OpenSCR gera protetores de tela executáveis pelo Windows.

Na arquitetura atual, uma exportação utiliza:

```text
MeuProtetor.scr
```

O arquivo `.scr` é autocontido: o runtime, a configuração e as imagens são
embutidos como recursos no próprio executável. Nenhuma pasta `.data` ou arquivo
adicional precisa acompanhar a exportação.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Tecnologias

O OpenSCR é desenvolvido principalmente com:

[![Python][Python]][Python-url]
[![PySide6][PySide6]][PySide6-url]
[![PyInstaller][PyInstaller]][PyInstaller-url]
[![Windows][WindowsTech]][WindowsTech-url]

- **Python** — aplicação, configuração e engine.
- **PySide6 / Qt** — interface gráfica e renderização.
- **PyInstaller** — criação dos executáveis distribuíveis.
- **Windows Screen Saver API** — integração com o formato `.scr`.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Primeiros passos

### Pré-requisitos

Para executar o projeto em ambiente de desenvolvimento:

- Python 3
- Git
- Windows >= 10

Para executar somente uma release já gerada, o usuário final não precisa de
Python, CMake ou Visual Studio. Essas ferramentas são necessárias apenas para
desenvolver e recompilar o runtime nativo.

Para gerar uma release a partir do código-fonte, instale também:

- CMake 3.24 ou superior;
- Visual Studio 2022 Build Tools com o workload de C++ para desktop e Windows SDK;
- ferramentas `cmake` e `msbuild` disponíveis no terminal.

### Instalação

1. Clone o repositório:

```bash
git clone https://github.com/bjmvictor/OpenSCR.git
```

2. Acesse o diretório:

```bash
cd OpenSCR
```

3. Crie um ambiente virtual:

```bash
python -m venv .venv
```

4. Ative o ambiente.

**Windows PowerShell**

```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows CMD**

```cmd
.venv\Scripts\activate.bat
```

5. Instale as dependências:

```bash
pip install -r requirements.txt
```

6. Execute o OpenSCR:

```bash
python creator.py
```

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Build

### Runtime nativo

O runtime é o motor executado pelos protetores de tela criados pelo OpenSCR.

Para compilá-lo:

```powershell
python build_native_runtime.py
```

Serão gerados:

```text
resources/
└── OpenSCRNativeRuntime.exe
```

O executável nativo é usado como base para o preview e para os protetores
exportados. O builder injeta nele a configuração e as imagens e grava um único
arquivo `.scr` autocontido, mantendo o ícone do OpenSCR.

O runtime precisa ser recompilado sempre que `native/runtime/src/main.cpp` ou o
formato binário de `RuntimeConfig`/`TextConfig` mudar:

```powershell
python build_native_runtime.py
```

### Versão portátil

Depois de compilar o runtime nativo, a versão portátil padrão usa o modo
`onedir`, que inicia rapidamente porque não extrai dezenas de MB a cada abertura:

```powershell
python build_openscr.py
```

O executável será criado em:

```text
release/
└── OpenSCR-2.0.2-Portable/
  ├── OpenSCR.exe
  └── _internal/
```

A pasta inteira deve ser mantida junta. O arquivo a executar é `OpenSCR.exe`.
A versão portátil contém as dependências necessárias e não exige Python local.

Para gerar um único `.exe`, aceitando o tempo maior de inicialização da extração:

```powershell
$env:OPENSCR_ONEFILE = "1"
python build_openscr.py
```

Uma release funcional deve incluir o executável portátil gerado em `release/`
e, se também for distribuir o criador de `.scr`, o runtime nativo presente em
`resources/OpenSCRNativeRuntime.exe` durante o build. Assim a versão final não
vai precisar executar CMake ou instalar compiladores.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Estrutura do projeto

```text
OpenSCR/
├── assets/
│   ├── OpenSCR.ico
│   └── logo.png
│
├── resources/
│   └── OpenSCRNativeRuntime.exe
│
├── runtime/
│   ├── __init__.py
│   └── variables.py
│
├── builder.py
├── native_builder.py
├── build_native_runtime.py
├── build_worker.py
├── build_openscr.py
├── creator.py
├── requirements.txt
├── LICENSE
└── README.md
```

### Creator

Responsável pela interface gráfica, edição das configurações e preview.

### Runtime nativo

Engine responsável por executar o protetor de tela.

### Builder

Prepara o arquivo `.scr`, configuração e recursos necessários para a exportação.

Essa separação mantém o editor independente do runtime utilizado pelos protetores gerados.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Segurança e antivírus

Arquivos `.scr` são executáveis do Windows e podem receber tratamento mais rigoroso de soluções de segurança.

Executáveis gerados durante o desenvolvimento também podem eventualmente produzir falsos positivos em antivírus.

O projeto busca reduzir esse comportamento através de builds transparentes e código-fonte público.

Não é recomendado desativar permanentemente o antivírus para utilizar o OpenSCR.

Caso uma versão oficial seja detectada incorretamente, recomenda-se reportar o arquivo como falso positivo ao fornecedor da solução de segurança.

O formato single-file reduz a necessidade de arquivos auxiliares e evita a
estrutura antiga `.scr` + `.data`, mas não garante ausência de falsos positivos.
Uma release pública deve ser assinada digitalmente e distribuída por um canal
confiável; assinatura, reputação do arquivo e submissão aos fornecedores de
antivírus são importantes para reduzir alertas.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Roadmap

O OpenSCR está em evolução contínua.

### Base

- [x] Interface gráfica.
- [x] Slideshow de imagens.
- [x] Preview em tela cheia.
- [x] Suporte a múltiplos monitores.
- [x] Controle de duração das imagens.
- [x] Controle da duração das transições.
- [x] Saída por teclado, clique ou movimento do mouse.
- [x] Geração de arquivos `.scr`.

### Aparência

- [x] Fade.
- [x] Slide.
- [x] Zoom.
- [x] Degradê.
- [x] Transição aleatória.
- [x] Seleção dos efeitos utilizados no modo aleatório.
- [ ] Ken Burns.
- [ ] Dissolve.
- [ ] Blur.
- [ ] Novos efeitos de transição.

### Elementos

- [x] Texto personalizado.
- [x] Variáveis dinâmicas.
- [x] Cor e tamanho do texto.
- [x] Posicionamento predefinido.
- [x] Múltiplos elementos de texto.
- [x] Sombra configuráveis (parcialmente completo).
- [ ] Logos e imagens sobrepostas.
- [ ] Editor visual por arrastar e soltar.
- [ ] Fontes personalizadas.

### Formatos e integração

- [x] Exportação `.scr` em arquivo único.
- [ ] Suporte a vídeos.
- [ ] Templates.
- [ ] Preview nativo `/p` do Windows.
- [ ] Instalação do screensaver diretamente pelo OpenSCR.
- [ ] Instalador do OpenSCR.
- [ ] Assinatura digital dos releases.
- [ ] Builds automatizados com GitHub Actions.
- [ ] Internacionalização.

Veja as [issues abertas](https://github.com/bjmvictor/OpenSCR/issues) para acompanhar melhorias, correções e funcionalidades propostas.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Contribuindo

Contribuições são bem-vindas.

Para propor uma alteração:

1. Faça um fork do projeto.
2. Crie uma branch:

```bash
git checkout -b feature/minha-funcionalidade
```

3. Faça suas alterações.

4. Crie um commit:

```bash
git commit -m "Adiciona nova funcionalidade"
```

5. Envie a branch:

```bash
git push origin feature/minha-funcionalidade
```

6. Abra um Pull Request.

Bugs, sugestões e novas ideias também podem ser registrados nas [issues do projeto](https://github.com/bjmvictor/OpenSCR/issues).

### Contribuidores

<a href="https://github.com/bjmvictor/OpenSCR/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=bjmvictor/OpenSCR" alt="Contribuidores do OpenSCR" />
</a>

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Licença

Distribuído sob a licença **MIT**.

Consulte o arquivo [`LICENSE`](LICENSE) para mais informações.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Autor

**Benjamin Victor**

Projeto: [github.com/bjmvictor/OpenSCR](https://github.com/bjmvictor/OpenSCR)

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Referências e recursos

- Python
- Qt for Python / PySide6
- PyInstaller
- Microsoft Windows Screen Savers
- Shields.io

---

<!-- MARKDOWN LINKS & IMAGES -->

[contributors-shield]: https://img.shields.io/github/contributors/bjmvictor/OpenSCR.svg?style=for-the-badge
[contributors-url]: https://github.com/bjmvictor/OpenSCR/graphs/contributors

[forks-shield]: https://img.shields.io/github/forks/bjmvictor/OpenSCR.svg?style=for-the-badge
[forks-url]: https://github.com/bjmvictor/OpenSCR/network/members

[stars-shield]: https://img.shields.io/github/stars/bjmvictor/OpenSCR.svg?style=for-the-badge
[stars-url]: https://github.com/bjmvictor/OpenSCR/stargazers

[issues-shield]: https://img.shields.io/github/issues/bjmvictor/OpenSCR.svg?style=for-the-badge
[issues-url]: https://github.com/bjmvictor/OpenSCR/issues

[license-shield]: https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge
[license-url]: https://github.com/bjmvictor/OpenSCR/blob/main/LICENSE

[windows-shield]: https://img.shields.io/badge/Platform-Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white
[windows-url]: https://www.microsoft.com/windows

[Python]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/

[PySide6]: https://img.shields.io/badge/PySide6-41CD52?style=for-the-badge&logo=qt&logoColor=white
[PySide6-url]: https://doc.qt.io/qtforpython-6/

[PyInstaller]: https://img.shields.io/badge/PyInstaller-4B8BBE?style=for-the-badge&logo=python&logoColor=white
[PyInstaller-url]: https://pyinstaller.org/

[WindowsTech]: https://img.shields.io/badge/Windows-0078D4?style=for-the-badge&logo=windows&logoColor=white
[WindowsTech-url]: https://learn.microsoft.com/windows/
