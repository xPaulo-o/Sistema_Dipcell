import os
import sys

# ==========================================================
# CONFIGURAÇÃO (tema/cores/fontes/caminhos)
# ==========================================================

# Tema CustomTkinter (chamado em main.py)
APPEARANCE_MODE = "Dark"
COLOR_THEME = "green"


def init_customtkinter():
    import customtkinter as ctk

    ctk.set_appearance_mode(APPEARANCE_MODE)
    ctk.set_default_color_theme(COLOR_THEME)
    return ctk


# Constantes de Cor
COR_FUNDO = "#1C1C1C"  # Um cinza mais escuro, próximo do preto
COR_FRAME = "#2A2D2E"  # Um cinza um pouco mais claro para os frames
COR_TEXTO = "#FFFFFF"
COR_VERDE_PRINCIPAL = "#2E8B57"
COR_VERMELHO = "#DC3545"
COR_AZUL = "#007BFF"
COR_HOVER_VERDE = "#38a366"  # Variação mais clara para o hover, mais moderno
COR_BORDA = "#444444"

# Fontes
FONTE_TITULO = ("Roboto", 20, "bold")
FONTE_NORMAL = ("Roboto", 12)
FONTE_BOLD = ("Roboto", 12, "bold")


# ==========================================================
# FUNÇÕES AUXILIARES PARA COMPATIBILIDADE E ROBUSTEZ
# ==========================================================

def resource_path(relative_path):
    """Obtém o caminho absoluto para o recurso, funciona para desenvolvimento e para PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


def get_app_directory():
    """Retorna o diretório onde o executável está rodando (ou o diretório do script)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # Sobe um nível para sair de 'Components' e pegar a raiz do projeto
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# ==========================================================
# CAMINHOS DO APP
# ==========================================================

APP_DIR = get_app_directory()
DB_NAME = os.path.join(APP_DIR, "os_dipcell.db")
PASTA_OS = os.path.join(APP_DIR, "OS_DIPCELL")
LOGO_PADRAO = resource_path(os.path.join("public", "logo2.png"))
