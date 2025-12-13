# Sistema de OS/Vendas - DIPCELL

Sistema de gestão de Ordens de Serviço (OS) e Vendas para assistência técnica de celulares.

## Funcionalidades

- ✅ Cadastro de Ordens de Serviço (OS) e Vendas
- ✅ Checklist completo para aparelhos
- ✅ Geração automática de PDFs
- ✅ Gestão de garantias (30 ou 90 dias)
- ✅ Atualização de situação, valores e pagamentos
- ✅ Busca por número de documento
- ✅ Interface moderna com tema escuro

## Requisitos

- Python 3.7+
- Tkinter (geralmente já vem com Python)
- ReportLab
- Pillow (PIL)

## Instalação

```bash
pip install reportlab pillow
```

## Como Usar

Execute o arquivo `Os.py`:

```bash
python Os.py
```

## Compilar para Executável

Use PyInstaller:

```bash
pyinstaller --onefile --windowed --icon=logo.ico --add-data "logo.png;." Os.py
```

## Tecnologias

- Python
- Tkinter (Interface Gráfica)
- SQLite (Banco de Dados)
- ReportLab (Geração de PDFs)
- Pillow (Manipulação de Imagens)

## Licença

Este projeto é de uso privado.

