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
    <img src="assets/splash.png" alt="OpenSCR" width="400">
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

## Baixar e utilizar

Para **usar o OpenSCR**, basta baixar a **[release oficial mais recente](https://github.com/bjmvictor/OpenSCR/releases/latest)**, extrair o conteúdo e executar no Windows.

### Download

1. Acesse a página de **[Releases do OpenSCR](https://github.com/bjmvictor/OpenSCR/releases/latest)**.
2. Baixe a versão disponibilizada para Windows.
3. Extraia o conteúdo, caso a versão seja distribuída em arquivo compactado.
4. Execute:

```text
OpenSCR.exe
```

> O código-fonte deste repositório é destinado a desenvolvimento, testes e contribuição. Para uso normal da aplicação, utilize uma release oficial.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Sobre o projeto

O **OpenSCR** é uma aplicação open source para criação de protetores de tela personalizados para Windows, distribuída ao público através das releases oficiais do projeto.

O projeto busca oferecer uma alternativa gratuita, moderna e simples às ferramentas proprietárias de criação de arquivos `.scr`, permitindo configurar o protetor de tela através de uma interface gráfica.

Entre os principais objetivos estão:

- simplificar a criação de screensavers para Windows;
- permitir personalização sem necessidade de programação;
- oferecer efeitos e transições configuráveis;
- permitir textos e informações dinâmicas na tela;
- disponibilizar uma ferramenta aberta para uso pessoal, corporativo e comunitário;
- evoluir para um editor visual completo de protetores de tela.

> O OpenSCR está em desenvolvimento ativo. Recursos, formatos de projeto e métodos de exportação podem sofrer alterações durante as versões iniciais.

> **Atenção:** apenas imagens (PNG, JPG, etc.) são suportadas. Não há suporte para arquivos de vídeo no momento.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Principais funcionalidades

### Slideshow

- Seleção de múltiplas imagens.
- Reordenação das imagens por arrastar e soltar.
- Ordem normal, reversa ou aleatória.
- Controle do tempo de exibição.
- Ajuste da imagem para preencher ou conter na tela.
- Suporte a múltiplos monitores.

### Transições

- Fade.
- Degradê.
- Slide.
- Zoom.
- Transição aleatória.
- Controle independente da duração da transição.

### Textos dinâmicos

O OpenSCR permite adicionar texto sobre o protetor de tela utilizando conteúdo personalizado e variáveis atualizadas durante a execução.

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
```

Também é possível configurar:

- posição;
- tamanho;
- cor;
- margem;
- sombra;
- exibição ou ocultação do texto.

### Preview

As configurações podem ser visualizadas em tela cheia antes da exportação.

O preview reproduz imagens, textos, variáveis e transições configuradas no projeto.

### Exportação

O OpenSCR gera protetores de tela executáveis pelo Windows.

Exemplo:

```text
MeuProtetor.scr
```

O arquivo `.scr` é autocontido: o runtime, a configuração e as imagens são embutidos como recursos no próprio executável. Nenhuma pasta `.data` ou arquivo adicional precisa acompanhar a exportação.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Tecnologias

O OpenSCR é desenvolvido principalmente com:

[![Python][Python]][Python-url]
[![PySide6][PySide6]][PySide6-url]
[![PyInstaller][PyInstaller]][PyInstaller-url]
[![Windows][WindowsTech]][WindowsTech-url]

- **Python** — editor, configuração e processo de geração dos screensavers.
- **PySide6 / Qt** — interface gráfica do editor.
- **C++ / Win32** — runtime nativo dos arquivos `.scr`.
- **Direct2D / DirectWrite / WIC** — renderização de imagens e textos no runtime.
- **PyInstaller** — empacotamento do OpenSCR para distribuição.
- **Windows Screen Saver API** — integração com o formato `.scr`.

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Desenvolvimento

### Pré-requisitos

As instruções desta seção são destinadas a quem deseja **desenvolver, modificar, testar ou contribuir com o código-fonte do OpenSCR**.

Para apenas utilizar a aplicação, baixe uma [release oficial](https://github.com/bjmvictor/OpenSCR/releases/latest).

Para executar o projeto em ambiente de desenvolvimento:

- Python 3;
- Git;
- Windows 10 ou superior.

O usuário final **não precisa** de Python, CMake, Visual Studio ou das demais ferramentas descritas abaixo. Elas são necessárias somente para desenvolvimento e recompilação de componentes do projeto.

Para recompilar o runtime nativo ou gerar novas builds a partir do código-fonte, instale também:

- CMake 3.24 ou superior;
- Visual Studio 2022 Build Tools com o workload de C++ para desktop e Windows SDK;
- ferramentas `cmake` e `msbuild` disponíveis no terminal.

### Executando o código-fonte

> Esta não é a forma recomendada para usuários finais. Use este procedimento apenas para desenvolvimento, testes ou contribuição com o projeto.

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

## Build para desenvolvimento

As etapas abaixo são destinadas a mantenedores e desenvolvedores que precisam recompilar o runtime ou gerar uma nova distribuição do OpenSCR.

Para uso normal da aplicação, utilize a [release oficial mais recente](https://github.com/bjmvictor/OpenSCR/releases/latest).

### Runtime nativo

O runtime é o motor executado pelos protetores de tela criados pelo OpenSCR.

Para compilá-lo:

```powershell
python build_native_runtime.py
```

Será gerado:

```text
resources/
└── OpenSCRNativeRuntime.exe
```

O executável nativo é usado como base para o preview e para os protetores exportados. O builder injeta nele a configuração e as imagens e grava um único arquivo `.scr` autocontido.

O runtime deve ser recompilado quando houver alterações no código nativo ou no formato de configuração utilizado entre o editor e o runtime.

### Versão portátil

Depois de compilar o runtime nativo, gere a versão portátil com:

```powershell
python build_openscr.py
```

A saída é criada no diretório:

```text
release/
└── OpenSCR-<versão>-Portable/
    ├── OpenSCR.exe
    └── _internal/
```

A pasta inteira deve ser mantida junta. O arquivo a executar é `OpenSCR.exe`.

A versão portátil contém as dependências necessárias e não exige Python instalado na máquina do usuário.

Para gerar um único `.exe`, aceitando um tempo maior de inicialização devido à extração:

```powershell
$env:OPENSCR_ONEFILE = "1"
python build_openscr.py
```

<p align="right">(<a href="#readme-top">voltar ao topo</a>)</p>

---

## Estrutura do projeto

```text
OpenSCR/
├── assets/
├── installer/
├── native/
│   └── runtime/
│       └── src/
├── resources/
├── runtime/
│
├── builder.py
├── native_builder.py
├── build_native_runtime.py
├── build_worker.py
├── build_openscr.py
├── creator.py
├── openscr_variables.py
├── config.json
├── requirements.txt
├── LICENSE
└── README.md
```

### Creator

Responsável pela interface gráfica, edição das configurações e preview.

### Runtime nativo

Engine em C++ responsável por executar o protetor de tela e renderizar imagens, textos e transições.

### Builder

Prepara o arquivo `.scr` e incorpora a configuração e os recursos necessários para a exportação.

Essa separação mantém o editor independente do runtime utilizado pelos protetores gerados.

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
- [ ] Seleção dos efeitos utilizados no modo aleatório.
- [ ] Ken Burns.
- [ ] Dissolve.
- [ ] Blur.
- [ ] Novos efeitos de transição.

### Elementos

- [x] Texto personalizado.
- [x] Variáveis dinâmicas.
- [x] Cor e tamanho do texto.
- [x] Posicionamento predefinido.
- [x] Sombra configurável.
- [ ] Múltiplos elementos de texto.
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
- C++ / Win32
- Direct2D / DirectWrite / WIC
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
