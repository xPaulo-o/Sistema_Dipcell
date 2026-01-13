# SISTEMA DE OS DIPCELL (COM CHECKLIST, ATUALIZAÇÃO, VALOR E FUNÇÃO VENDAS)

import os
import sys 
import sqlite3
from datetime import datetime, timedelta
import tkinter as tk # Manter tkinter para constantes (tk.END) e Treeview
from tkinter import ttk, messagebox
import threading
import json

# NOVO: Importa CustomTkinter
import customtkinter as ctk

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

from reportlab.pdfgen import canvas
from reportlab.lib.colors import grey

from PIL import Image as PILImage, ImageTk

# ==========================================================
# CONFIGURAÇÃO CUSTOMTKINTER
# ==========================================================

# Define a aparência padrão como "Dark" (Escuro) e o tema padrão como "green"
ctk.set_appearance_mode("Dark") 
ctk.set_default_color_theme("green") 

# Constantes de Cor
COR_FUNDO = "#1C1C1C" # Um cinza mais escuro, próximo do preto
COR_FRAME = "#2A2D2E" # Um cinza um pouco mais claro para os frames
COR_TEXTO = "#FFFFFF"
COR_VERDE_PRINCIPAL = '#2E8B57' 
COR_VERMELHO = "#DC3545" 
COR_AZUL = "#007BFF" 
COR_HOVER_VERDE = "#38a366" # Variação mais clara para o hover, mais moderno
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
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def abrir_arquivo(caminho):
    """Abre um arquivo de forma compatível com Windows, Linux e Mac."""
    try:
        if sys.platform == "win32":
            os.startfile(caminho)
        elif sys.platform == "darwin":  # macOS
            os.system(f"open '{caminho}'")
        else:  # Linux e outros
            os.system(f"xdg-open '{caminho}'")
    except Exception as e:
        try:
            import subprocess
            subprocess.Popen([caminho], shell=True)
        except Exception as e2:
            try:
                messagebox.showerror("Erro", f"Não foi possível abrir o arquivo:\n{caminho}\n\nErro: {str(e2)}")
            except:
                print(f"Erro ao abrir arquivo {caminho}: {str(e2)}")

# ==========================================================

# Caminhos usando o diretório do aplicativo
APP_DIR = get_app_directory()
DB_NAME = os.path.join(APP_DIR, "os_dipcell.db")
PASTA_OS = os.path.join(APP_DIR, "OS_DIPCELL")
LOGO_PADRAO = resource_path("logo.png") 


# ==========================================================
# BANCO DE DADOS + MIGRAÇÃO (SEM ALTERAÇÕES)
# ==========================================================

def criar_banco():
    # Código da função criar_banco (mantido inalterado)
    try:
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS os (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                numero TEXT,
                cliente TEXT,
                telefone TEXT,
                modelo TEXT,
                imei TEXT,
                senha TEXT,
                acessorios TEXT,
                problemas TEXT,
                situacao TEXT,
                valor TEXT,
                entrada TEXT,
                saida TEXT,
                garantia TEXT,
                arquivo TEXT,
                tipo_garantia TEXT,
                metodo_pagamento TEXT,
                checklist TEXT,
                dias_garantia INTEGER,
                tipo_documento TEXT 
            )
        ''')
        conn.commit()

        # Verificar colunas e adicionar caso faltem (MIGRAÇÃO)
        c.execute("PRAGMA table_info(os)")
        cols = [row[1] for row in c.fetchall()]

        obrig = {
            "garantia": "TEXT",
            "saida": "TEXT",
            "tipo_garantia": "TEXT",
            "metodo_pagamento": "TEXT",
            "checklist": "TEXT", 
            "dias_garantia": "INTEGER",
            "tipo_documento": "TEXT",
            "parcelas": "INTEGER",
            "detalhes_parcelas": "TEXT"
        }

        for col, tipo in obrig.items():
            if col not in cols:
                try:
                    if col == "dias_garantia":
                        default_val = "90"
                    elif col == "tipo_documento":
                        default_val = "'OS'"
                    elif col == "parcelas":
                        default_val = "1"
                    else:
                        default_val = "'Com Garantia'"
                        
                    c.execute(f"ALTER TABLE os ADD COLUMN {col} {tipo} DEFAULT {default_val}")
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Aviso: Não foi possível adicionar coluna {col}: {e}")
                    pass

        # Adicionar índices para melhor performance
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_numero ON os (numero)",
            "CREATE INDEX IF NOT EXISTS idx_cliente ON os (cliente)",
            "CREATE INDEX IF NOT EXISTS idx_modelo ON os (modelo)",
            "CREATE INDEX IF NOT EXISTS idx_imei ON os (imei)",
            "CREATE INDEX IF NOT EXISTS idx_problemas ON os (problemas)",
            "CREATE INDEX IF NOT EXISTS idx_tipo_documento ON os (tipo_documento)",
            "CREATE INDEX IF NOT EXISTS idx_situacao ON os (situacao)",
            "CREATE INDEX IF NOT EXISTS idx_entrada ON os (entrada)"
        ]
        for idx in indices:
            try:
                c.execute(idx)
                conn.commit()
            except sqlite3.Error as e:
                print(f"Aviso: Não foi possível criar índice: {e}")

        conn.close()
    except sqlite3.Error as e:
        messagebox.showerror("Erro Crítico", 
            f"Erro ao criar/acessar o banco de dados:\n{str(e)}\n\n"
            f"Verifique se você tem permissões de escrita no diretório:\n{APP_DIR}")
        sys.exit(1)
    except Exception as e:
        messagebox.showerror("Erro Crítico", 
            f"Erro inesperado ao inicializar o banco de dados:\n{str(e)}")
        sys.exit(1)


# ==========================================================
# FUNÇÕES AUXILIARES (mantidas)
# ==========================================================

def parse_monetario_to_float(txt):
    if not txt:
        return 0.0
    txt = txt.replace(",", ".")
    return float(txt.replace(".", "", txt.count(".") - 1) or 0) 

def formatar_monetario(v):
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def aplicar_mascara_tel(raw):
    nums = "".join(ch for ch in raw if ch.isdigit())
    if len(nums) <= 2:
        return f"({nums}"
    if len(nums) <= 6:
        return f"({nums[:2]}) {nums[2:]}"
    if len(nums) <= 10:
        return f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
    nums = nums[:11]
    return f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"


# ==========================================================
# GERAR PDF (mantida)
# ==========================================================

def gerar_documento(dados, valor_texto, total_float, tipo_garantia, metodo_pagamento, checklist_str, tipo_documento, dias_garantia_num, parcelas_info=None):
    # Código da função gerar_documento (mantido inalterado)
    
    # 1. Tratamento de campos vazios para N/A
    for k, v in dados.items():
        if v is None or (isinstance(v, str) and v.strip() == ""):
            dados[k] = "N/A"
            
    try:
        if not os.path.exists(PASTA_OS):
            try:
                os.makedirs(PASTA_OS, exist_ok=True)
            except OSError as e:
                messagebox.showerror("Erro", 
                    f"Não foi possível criar a pasta de documentos:\n{PASTA_OS}\n\n"
                    f"Erro: {str(e)}\n\n"
                    f"Verifique as permissões do diretório.")
                return None
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao verificar/criar pasta: {str(e)}")
        return None

    pdf_path = os.path.join(PASTA_OS, f"{tipo_documento}_{dados['numero'].split('-')[1]}.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2*cm,
        rightMargin=2*cm,
        topMargin=1.5*cm, 
        bottomMargin=1.5*cm 
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    titulo_doc = "Ordem de Serviço" if tipo_documento == "OS" else "Comprovante de Venda"

    titulo = Paragraph(
        f"<b>DIPCELL<br/>{titulo_doc}</b>",
        ParagraphStyle("t", parent=styles["Heading1"], alignment=1, fontSize=22)
    )

    if os.path.exists(LOGO_PADRAO):
        img = Image(LOGO_PADRAO, width=120, height=120) 
    else:
        img = Paragraph("", normal)

    header = Table([[img, titulo]], colWidths=[160, 330])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    story = [header, Spacer(1, 10)] 

    def bloco(titulo, lista):
        story.append(Paragraph(
            f"<b>{titulo}</b>",
            ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14)
        ))

        rows = [[Paragraph(f"<b>{k}</b>"), Paragraph(str(v))] for k, v in lista]

        tbl = Table(rows, colWidths=[160, 330])
        tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, 0), 0.6, colors.grey),
            ("GRID", (0, 1), (-1, -1), 0.6, colors.grey),
            ("BACKGROUND", (0, 0), ( -1, 0), colors.whitesmoke)
        ]))

        story.append(tbl)
        story.append(Spacer(1, 4)) 

    def bloco_checklist(titulo, checklist_str):
        story.append(Paragraph(
            f"<b>{titulo}</b>",
            ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14)
        ))
        
        rows = []
        itens = [item.split(':') for item in checklist_str.split(';') if item.strip()]

        NUM_COLUNAS = 3
        
        num_itens = len(itens)
        if num_itens == 0:
            return
            
        num_linhas = (num_itens + NUM_COLUNAS - 1) // NUM_COLUNAS
        
        itens_preenchidos = itens + [("", "")] * (num_linhas * NUM_COLUNAS - num_itens)
            
        rows = []
        
        for i in range(num_linhas):
            row_data = []
            for j in range(NUM_COLUNAS):
                idx = i + j * num_linhas
                
                item, status = itens_preenchidos[idx]
                
                if item:
                    check_char = "X" if status == "Sim" else " "
                    
                    paragrafo = Paragraph(
                        f"<font size='8'>[{check_char}] <b>{item}</b></font>", 
                        ParagraphStyle("s", parent=normal, alignment=0, leading=8) 
                    )
                else:
                    paragrafo = Paragraph("", normal)

                row_data.append(paragrafo)
            
            rows.append(row_data)

        col_widths = [5.66*cm] * NUM_COLUNAS 
        
        tbl = Table(rows, colWidths=col_widths)
        tbl.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 0), (-1, -1), 0.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
        ]))
        
        story.append(tbl)
        story.append(Spacer(1, 4)) 

    def bloco_parcelas(detalhes_parcelas_json):
        try:
            lista_parcelas = json.loads(detalhes_parcelas_json)
        except:
            return

        story.append(Paragraph(
            f"<b>Parcelamento (Crediário)</b>",
            ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14)
        ))

        # Cabeçalho da tabela
        rows = [["Parcela", "Vencimento", "Valor", "Situação"]]
        
        for p in lista_parcelas:
            # Cria um espaço visual para marcar PG ou N/PG
            status_visual = "  (  ) PG    (  ) N/PG  "
            rows.append([f"{p['numero']}x", p['vencimento'], f"R$ {p['valor']}", status_visual])

        tbl = Table(rows, colWidths=[60, 100, 100, 230])
        tbl.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.6, colors.grey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story.append(tbl)
        story.append(Spacer(1, 4))

    bloco("Dados do Cliente", [
        (f"Número {tipo_documento}", dados["numero"]), 
        ("Cliente", dados["cliente"]),
        ("Telefone", dados["telefone"]),
        ("Data", dados["entrada"])
    ])

    if tipo_documento == "OS":
        bloco("Aparelho", [
            ("Modelo", dados["modelo"]),
            ("IMEI", dados["imei"]),
            ("Acessórios", dados["acessorios"]),
            ("Senha/Padrão", dados["senha"])
        ])
        
        bloco_checklist("Lista de Checagem do Aparelho", checklist_str)
        
        problema_titulo = "Problemas / Detalhe"
    
    else: 
        bloco("Produto Vendido", [
            ("Produto", dados["modelo"]), 
            ("Detalhes", dados["acessorios"]) 
        ])
        
        problema_titulo = "Detalhe (Venda)"


    bloco(titulo_doc, [ 
        (problema_titulo, dados["problemas"] if tipo_documento == "OS" else "Ver Produto Vendido"), 
        ("Situação" if tipo_documento == "OS" else "Status", dados["situacao"]),
        ("Valor (R$)", valor_texto),
        ("Total (R$)", formatar_monetario(total_float)),
        ("Método Pgto.", metodo_pagamento), 
        ("Saída", dados["saida"] if dados["saida"] else "N/A"), # Alterado para N/A se vazio
        ("Garantia até", dados["garantia"]),
        ("Tipo de Garantia", tipo_garantia) 
    ])

    if metodo_pagamento == "PARCELADO NO CREDIÁRIO" and parcelas_info:
        bloco_parcelas(parcelas_info)

    AVISO_PAGAMENTO = "NÃO SERÁ ENTREGUE O APARELHO/PRODUTO SEM ANTES ACERTAR O PAGAMENTO. "
    dias_garantia_texto = f"{dias_garantia_num} dias" if dias_garantia_num > 0 else "legal"
    termo_texto = ""
    
    if tipo_documento == "OS":
        if dados["situacao"] == "CONCLUÍDA" and tipo_garantia == "Com Garantia": # Condição alterada
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO}</b> A garantia cobre exclusivamente o **serviço** realizado pelo período de **{dias_garantia_texto}** informado nesta OS. "
                "Não cobre danos causados por mau uso, queda, oxidação, danos líquidos, tela quebrada ou violação do lacre. "
                "O aparelho deve ser retirado em até 90 dias após a conclusão do serviço.</font>"
            )
        else: 
            termo_texto = ( # Se não for Concluída ou for Sem Garantia
                f"<font size='8'><b>{AVISO_PAGAMENTO} SERVIÇO SEM GARANTIA!</b> Esta OS está como <b>{dados['situacao']}</b>. O cliente está ciente de que o serviço realizado "
                "não possui cobertura de garantia devido à situação, natureza do reparo/peça ou condição do aparelho. "
                "O aparelho deve ser retirado em até 90 dias após a conclusão do serviço.</font>"
            )
            
    else: 
        if dados["situacao"] == "CONCLUÍDA" and tipo_garantia == "Com Garantia": # Condição alterada
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO}</b> A garantia de **{dias_garantia_texto}** cobre somente se o produto apresentar "
                "problemas de fábrica e estiver com a caixa do mesmo. "
                "A garantia **NÃO COBRE** danos por mau uso, queda, oxidação, danos líquidos ou remoção de selos de garantia.</font>"
            )
        else: 
            termo_texto = ( # Se não for Concluída ou for Sem Garantia
                f"<font size='8'><b>{AVISO_PAGAMENTO} PRODUTO VENDIDO SEM GARANTIA!</b> O cliente está ciente de que este produto "
                "não possui cobertura de garantia (Status: {dados['situacao']}).</font>"
            )


    termo = Paragraph(termo_texto, normal)

    story.append(Spacer(1, 3)) 
    story.append(termo)
    story.append(Spacer(1, 3)) 

    assinatura_tbl = Table([
        ["__________________________________", "__________________________________"],
        ["Assinatura do Cliente", "Assinatura da Loja"]
    ], colWidths=[245, 245])

    assinatura_tbl.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))

    story.append(Spacer(1, 2)) 
    story.append(assinatura_tbl)
    story.append(Spacer(1, 3))

    def desenhar_borda(canvas, doc):
        canvas.saveState()
        W, H = A4
        canvas.setStrokeColor(colors.black)
        canvas.setLineWidth(1)
        canvas.rect(12, 12, W - 24, H - 24)
        canvas.setLineWidth(0.8)
        canvas.rect(20, 20, W - 40, H - 40)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(grey)
        canvas.drawCentredString(W/2, 35, "DIPCELL — Sistema de OS/Vendas")
        canvas.restoreState()

    try:
        doc.build(story, onFirstPage=desenhar_borda, onLaterPages=desenhar_borda)
        return pdf_path
    except Exception as e:
        messagebox.showerror("Erro ao Gerar PDF", 
            f"Erro ao gerar o documento PDF:\n{str(e)}\n\n"
            f"Verifique se você tem permissões de escrita no diretório:\n{PASTA_OS}")
        return None


# ==========================================================
# INTERFACE CUSTOMTKINTER
# ==========================================================

class SistemaOS:

    def __init__(self, master):
        # Master agora é um ctk.CTk()
        master.title("DIPCELL - Sistema de OS/Vendas")
        master.geometry("1200x800") # Definir um tamanho inicial maior
        master.configure(fg_color=COR_FUNDO) # Aplicar cor de fundo principal
        
        # Configuração do estilo da Treeview (necessária, pois CTk não a substitui)
        style = ttk.Style()
        style.theme_use('clam') 
        # Cores para a Treeview em modo escuro
        style.configure("Treeview", 
                        background=COR_FRAME, 
                        foreground=COR_TEXTO, 
                        fieldbackground=COR_FRAME, 
                        rowheight=28, 
                        font=FONTE_NORMAL)
        # O tema "green" do CTk cuida do highlight, mas reforçamos o fundo
        style.map('Treeview', background=[('selected', COR_VERDE_PRINCIPAL)]) 
        style.configure("Treeview.Heading", 
                        font=FONTE_BOLD, 
                        background="#333333", # Cabeçalho um pouco mais escuro
                        foreground=COR_TEXTO,
                        relief="flat")
        style.map("Treeview.Heading",
                  background=[('active', '#3c3c3c')])
        # ----------------------------------------------------

        # Container principal agora é um CTkFrame
        self.container = ctk.CTkFrame(master, fg_color="transparent")
        self.container.pack(side="top", fill="both", expand=True, padx=10, pady=10)

        # master.grid_rowconfigure(0, weight=1) # Usando pack agora
        # master.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        self.tipo_documento_var = tk.StringVar(value="OS") 
        self.dias_garantia_var = tk.StringVar(value="90 Dias") 
        # NOVO: Variável para a Data de Entrada, inicializada com a data atual
        self.data_entrada_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        self.parcelas_var = tk.StringVar(value="1x")
        
        # Variáveis para paginação
        self.page_size = 50  # Registros por página
        self.current_page = 1
        self.total_records = 0
        
        self.criar_tela_preenchimento(self.container)
        self.criar_tela_lista(self.container)
        self.criar_tela_editar(self.container)

        self.show_frame("Preenchimento")
        self.gerar_numero_documento() 
        
    # Funções de numeração (mantidas)
    def gerar_numero_os(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT MAX(CAST(SUBSTR(numero, 4) AS INTEGER)) FROM os WHERE tipo_documento='OS'")
        max_os_num = c.fetchone()[0] or 0
        self.numero_documento = f"OS-{max_os_num+1:04d}"
        conn.close()
        
    def gerar_numero_venda(self):
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT MAX(CAST(SUBSTR(numero, 7) AS INTEGER)) FROM os WHERE tipo_documento='VENDA'")
        max_venda_num = c.fetchone()[0] or 0
        self.numero_documento = f"VENDA-{max_venda_num+1:04d}"
        conn.close()
        
    def gerar_numero_documento(self):
        if self.tipo_documento_var.get() == "OS":
            self.gerar_numero_os()
        else:
            self.gerar_numero_venda()

    def show_frame(self, page_name):
        frame = self.frames[page_name]
        frame.tkraise()
        if page_name == "Lista":
            self.carregar_dados_lista(page=self.current_page) 

    def criar_tela_preenchimento(self, parent):
        # Substitui Frame por CTkFrame
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self.frames["Preenchimento"] = f
        f.grid(row=0, column=0, sticky="nsew")

        # center_frame agora é CTkFrame
        center_frame = ctk.CTkScrollableFrame(f, fg_color="transparent") # Usar ScrollableFrame para telas menores
        center_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.vint = f.register(lambda v: v.isdigit() or v == "")
        self.vmoney = f.register(lambda v: all(ch in "0123456789,." for ch in v) and v.count(',') <= 1) 
        self.campos = {}
        self.tel_var = tk.StringVar() 
        self.botoes_preenchimento = []

        def aplicar_e_mostrar_mascara(event):
            raw_text = self.tel_var.get()
            nums_only = "".join(ch for ch in raw_text if ch.isdigit())
            if len(nums_only) >= 10: 
                masked_text = aplicar_mascara_tel(raw_text)
                self.tel_var.set(masked_text)
            else:
                self.tel_var.set(nums_only) 
        
        def on_tipo_garantia_change(event):
            # Acessa o CTkComboBox pelo nome do campo
            combo_dias = self.campos["dias_garantia"]
            if self.campos["tipo_garantia"].get() == "Com Garantia":
                combo_dias.configure(state="readonly")
                if not self.dias_garantia_var.get():
                     self.dias_garantia_var.set("90 Dias")
            else:
                combo_dias.configure(state="disabled")
                self.dias_garantia_var.set("")

        def on_metodo_pagamento_change(event):
            metodo = self.campos["metodo_pagamento"].get()
            combo_parcelas = self.campos["parcelas"]
            label_parcelas = self.campos["parcelas_label"]
            
            if metodo == "PARCELADO NO CREDIÁRIO":
                combo_parcelas.grid(row=8, column=3, sticky="ew", padx=15, pady=(5, 10)) # Ajuste de Grid manual
                label_parcelas.grid(row=8, column=2, sticky="w", padx=15, pady=(10, 0))
            else:
                combo_parcelas.grid_forget()
                label_parcelas.grid_forget()
                self.parcelas_var.set("1x")
        
        def alternar_tipo_documento(event=None):
            self.limpar()
            self.gerar_numero_documento()
            tipo = self.tipo_documento_var.get()
            
            is_os = (tipo == "OS")
            
            self.campos["modelo_label"].configure(text="Modelo*" if is_os else "Produto*")
            self.campos["acessorios_label"].configure(text="Acessórios" if is_os else "Detalhes da Venda")
            
            situacao_combo = self.campos["situacao"]
            if is_os:
                situacao_combo.set("EM ABERTO") 
                situacao_combo.configure(values=["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA", "NÃO PAGO"])
            else:
                situacao_combo.set("CONCLUÍDA")
                situacao_combo.configure(values=["CONCLUÍDA", "CANCELADA"]) # Opções limitadas para VENDA

            metodo_combo = self.campos["metodo_pagamento"]
            if is_os:
                metodo_combo.configure(values=["CARTÃO", "DINHEIRO", "PIX"])
            else:
                metodo_combo.configure(values=["CARTÃO", "DINHEIRO", "PIX", "PARCELADO NO CREDIÁRIO"])

            os_fields_2col = ["imei", "senha"]
            
            campos_info = [
                ("Cliente*", "cliente"), ("Modelo*", "modelo"),
                ("Telefone*", "telefone"), ("Data de Entrada*", "data_entrada"), # Campo de data adicionado
                ("IMEI", "imei"),
                ("Senha/Padrão", "senha"), ("Acessórios", "acessorios"),
                ("Tipo de Garantia*", "tipo_garantia"), ("Método de Pagamento*", "metodo_pagamento"),
                ("Valor (R$)*", "valor"), ("Situacao*", "situacao")
            ]
            
            # Reposiciona ou esconde os campos de IMEI e Senha
            for key in os_fields_2col:
                    
                label_widget = self.campos[f"{key}_label"]
                entry_widget = self.campos[key]
                    
                info = next((item for i, item in enumerate(campos_info) if item[1] == key), None)
                if info:
                    index = campos_info.index(info)
                    row = index // 2
                    col = (index % 2) * 2
                        
                    if is_os:
                        label_widget.grid(row=row, column=col, sticky="w", padx=10, pady=(5, 0))
                        entry_widget.grid(row=row, column=col + 1, sticky="ew", padx=10, pady=(0, 5))
                    else:
                        label_widget.grid_forget()
                        entry_widget.grid_forget()
                        
            # >>> IMPLEMENTAÇÃO PARA OCULTAR/MOSTRAR CHECKLIST E DETALHE ADICIONAL <<<
            problemas_row_start = len(campos_info) // 2
            problemas_row_end = problemas_row_start + 1 + 7

            if is_os:
                # Mostra o Checklist e o Detalhe Adicional (abaixo da checklist)
                self.checklist_frame.grid(row=problemas_row_start + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(15, 5))
                self.campos["problemas_detalhe_label"].configure(text="Detalhe Adicional (Opcional):")
                self.campos["problemas_detalhe_label"].grid(row=problemas_row_end + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 0))
                self.campos["problemas_detalhe"].grid(row=problemas_row_end + 2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
            else:
                # Oculta o Checklist
                self.checklist_frame.grid_forget()
                
                # Reposiciona o campo Detalhe Adicional (Problemas) logo abaixo dos outros campos
                l_detalhe = self.campos["problemas_detalhe_label"]
                e_detalhe = self.campos["problemas_detalhe"]
                
                # A última linha preenchida antes da checklist era 'dias_garantia' que está na linha 'dias_row'
                dias_row = len(campos_info) // 2 
                
                l_detalhe.configure(text="Notas de Venda (Opcional):")
                l_detalhe.grid(row=dias_row + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 0))
                e_detalhe.grid(row=dias_row + 2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
            # >>> FIM DA IMPLEMENTAÇÃO PARA OCULTAR/MOSTRAR CHECKLIST E DETALHE ADICIONAL <<<


        # Logo (Usa CTkImage para compatibilidade de tema)
        if os.path.exists(LOGO_PADRAO):
            try:
                logo_img = ctk.CTkImage(PILImage.open(LOGO_PADRAO), size=(120, 120))
                logo_label = ctk.CTkLabel(center_frame, image=logo_img, text="")
                logo_label.pack(pady=(0, 20))
                self.logo = logo_img # Manter referência
            except Exception as e:
                print(f"Aviso: Não foi possível carregar a logo: {e}")
                pass


        # Seleção OS/VENDA
        tipo_doc_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        tipo_doc_frame.pack(pady=10)
        ctk.CTkLabel(tipo_doc_frame, text="Tipo de Documento:", font=FONTE_NORMAL).pack(side=tk.LEFT, padx=5)
        # Substitui ttk.Combobox por CTkComboBox
        cb_tipo_doc = ctk.CTkComboBox(tipo_doc_frame, 
                                     width=250, # Aumentar um pouco a largura
                                     values=["OS", "VENDA"], 
                                     command=alternar_tipo_documento,
                                     variable=self.tipo_documento_var,
                                     font=FONTE_NORMAL,
                                     corner_radius=8)
        cb_tipo_doc.set("OS")
        cb_tipo_doc.pack(side=tk.LEFT)

        # Frame dos campos 
        campo_frame = ctk.CTkFrame(center_frame, fg_color=COR_FRAME, corner_radius=10)
        campo_frame.pack(pady=10, padx=20)

        campos_info = [
            ("Cliente*", "cliente"), ("Modelo*", "modelo"),
            ("Telefone*", "telefone"), ("Data de Entrada*", "data_entrada"), # NOVO CAMPO AQUI
            ("IMEI", "imei"),
            ("Senha/Padrão", "senha"), ("Acessórios", "acessorios"),
            ("Tipo de Garantia*", "tipo_garantia"), ("Método de Pagamento*", "metodo_pagamento"),
            ("Valor (R$)*", "valor"), ("Situacao*", "situacao")
        ]

        W_ENTRY = 200 # CTk usa pixels, ajustamos o tamanho
        COMBO_VALORES = {
            "situacao": ["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA", "NÃO PAGO"],
            "tipo_garantia": ["Com Garantia", "Sem Garantia"],
            "metodo_pagamento": ["CARTÃO", "DINHEIRO", "PIX", "PARCELADO NO CREDIÁRIO"],
        }
        
        for i, (label, key) in enumerate(campos_info):
            row = i // 2
            col = (i % 2) * 2

            # Label (CTkLabel)
            l = ctk.CTkLabel(campo_frame, text=label, anchor="w", font=FONTE_NORMAL)
            l.grid(row=row, column=col, sticky="w", padx=15, pady=(10, 0))
            self.campos[f"{key}_label"] = l

            # Entrada (CTkEntry ou CTkComboBox)
            if key in COMBO_VALORES:
                e = ctk.CTkComboBox(campo_frame, 
                                    width=W_ENTRY, 
                                    values=COMBO_VALORES[key], 
                                    state="readonly",
                                    font=FONTE_NORMAL,
                                    corner_radius=8)
                e.set(COMBO_VALORES[key][0]) # Define o valor inicial
                
                if key == "tipo_garantia":
                    e.configure(command=on_tipo_garantia_change)
                elif key == "metodo_pagamento":
                    e.configure(command=on_metodo_pagamento_change)
            
            else:
                e = ctk.CTkEntry(campo_frame, width=W_ENTRY, font=FONTE_NORMAL, corner_radius=8)
                
                if key == "telefone":
                    e.configure(validate="key", validatecommand=(self.vint, "%P"), textvariable=self.tel_var)
                    e.bind("<FocusOut>", aplicar_e_mostrar_mascara)
                elif key == "imei":
                    e.configure(validate="key", validatecommand=(self.vint, "%P"))
                elif key == "valor":
                    e.configure(validate="key", validatecommand=(self.vmoney, "%P"))
                    e.insert(0, "0,00") # Valor inicial
                elif key == "data_entrada": # Configuração do novo campo de data
                    e.configure(textvariable=self.data_entrada_var)
            
            e.grid(row=row, column=col + 1, sticky="ew", padx=15, pady=(5, 10))
            self.campos[key] = e

        # Dias de Garantia
        dias_row = len(campos_info) // 2
        l_dias = ctk.CTkLabel(campo_frame, text="Dias de Garantia*", anchor="w", font=FONTE_NORMAL)
        l_dias.grid(row=dias_row, column=2, sticky="w", padx=15, pady=(10, 0))
        self.campos["dias_garantia_label"] = l_dias
        
        e_dias = ctk.CTkComboBox(campo_frame, 
                                 width=W_ENTRY, 
                                 state="readonly", 
                                 values=["30 Dias", "90 Dias"], 
                                 variable=self.dias_garantia_var,
                                 font=FONTE_NORMAL,
                                 corner_radius=8)
        e_dias.set("90 Dias")
        e_dias.grid(row=dias_row, column=3, sticky="ew", padx=15, pady=(5, 10))
        self.campos["dias_garantia"] = e_dias
        on_tipo_garantia_change(None) 

        # Parcelas (Oculto por padrão)
        l_parcelas = ctk.CTkLabel(campo_frame, text="Qtd. Parcelas", anchor="w", font=FONTE_NORMAL)
        self.campos["parcelas_label"] = l_parcelas
        
        e_parcelas = ctk.CTkComboBox(campo_frame,
                                     width=W_ENTRY,
                                     state="readonly",
                                     values=[f"{i}x" for i in range(1, 13)],
                                     variable=self.parcelas_var,
                                     font=FONTE_NORMAL,
                                     corner_radius=8)
        self.campos["parcelas"] = e_parcelas
        # Grid será definido no evento on_metodo_pagamento_change

        # --- SEÇÃO CHECKLIST & DETALHE ---
        
        problemas_row_start = len(campos_info) // 2
        
        self.checklist_frame = ctk.CTkFrame(campo_frame, fg_color="transparent") 
        # A grid para o checklist_frame será definida por alternar_tipo_documento
        ctk.CTkLabel(self.checklist_frame, text="CHECKLIST (PROBLEMAS/STATUS)", font=FONTE_BOLD).pack(anchor="w", pady=(10, 5))
        
        self.checklist_vars = {}
        checklist_itens = [
            "Tela Display", "Touch Screen", "Teclas", "Sensores de Proximidade", 
            "Bluetooth", "Wi-Fi", "Ligações", "Alto Falante", 
            "Câmera", "Microfone", "Conector Carregador", "Conector Cartão de Memória", 
            "Sim Card", "Outros (Opcional - p/ defeitos internos)"
        ]

        # Frame interno para a checklist (organização em duas colunas)
        chk_inner_frame = ctk.CTkFrame(self.checklist_frame, fg_color="transparent")
        chk_inner_frame.pack(fill="x")
        
        for i, item in enumerate(checklist_itens):
            col = i // 7
            var = tk.StringVar(value="Não")
            # Substitui ttk.Checkbutton por CTkCheckBox
            chk = ctk.CTkCheckBox(chk_inner_frame, 
                                  text=item, 
                                  variable=var, 
                                  onvalue="Sim", 
                                  offvalue="Não",
                                  font=FONTE_NORMAL,
                                  corner_radius=15, # Círculo
                                  border_color=COR_VERDE_PRINCIPAL) # Mantém a cor da borda verde
            chk.grid(row=i%7, column=col, sticky="w", padx=10)
            self.checklist_vars[item] = var

        # --- CAMPO DETALHE ADICIONAL (PROBLEMAS/OUTROS) ---
        
        l_detalhe = ctk.CTkLabel(campo_frame, text="Detalhe Adicional (Opcional):", font=FONTE_NORMAL)
        self.campos["problemas_detalhe_label"] = l_detalhe
        # O posicionamento inicial (grid) será definido por alternar_tipo_documento
        
        # Substitui RoundedEntry por CTkEntry
        e_detalhe = ctk.CTkEntry(campo_frame, width=W_ENTRY * 2 + 30, font=FONTE_NORMAL, corner_radius=8)
        # O posicionamento inicial (grid) será definido por alternar_tipo_documento
        self.campos["problemas_detalhe"] = e_detalhe
        
        # --- FIM SEÇÃO CHECKLIST ---

        fb = ctk.CTkFrame(center_frame, fg_color="transparent")
        fb.pack(pady=20)
        
        # Substitui RoundedButton por CTkButton (automaticamente usa a cor de destaque verde)
        
        b_salvar = ctk.CTkButton(fb, text="Salvar Documento", width=200, height=40, command=self.salvar, 
                                 fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE,
                                 font=FONTE_BOLD, corner_radius=8)
        b_salvar.grid(row=0, column=0, padx=10)
        self.botoes_preenchimento.append(b_salvar)
        
        b_limpar = ctk.CTkButton(fb, text="Limpar", width=200, height=40, command=self.limpar, 
                                 fg_color=COR_FRAME, hover_color="#3F4243",
                                 border_width=1, border_color=COR_BORDA,
                                 font=FONTE_BOLD, corner_radius=8)
        b_limpar.grid(row=0, column=1, padx=10)
        self.botoes_preenchimento.append(b_limpar)
        
        b_lista = ctk.CTkButton(fb, text="Ver Lista de Documentos", width=200, height=40, command=lambda: self.show_frame("Lista"), 
                                fg_color="transparent", hover_color=COR_FRAME,
                                border_width=1, border_color=COR_VERDE_PRINCIPAL, text_color=COR_VERDE_PRINCIPAL,
                                font=FONTE_BOLD, corner_radius=8)
        b_lista.grid(row=0, column=2, padx=10)
        self.botoes_preenchimento.append(b_lista)

        # Chama a função para configurar o layout inicial (OS por padrão)
        alternar_tipo_documento() 


    def criar_tela_lista(self, parent):
        
        # Frame principal da Lista (CTkFrame)
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self.frames["Lista"] = f
        f.grid(row=0, column=0, sticky="nsew")
        
        f.grid_rowconfigure(1, weight=1)
        f.grid_columnconfigure(0, weight=1)
        
        top_frame = ctk.CTkFrame(f, fg_color="transparent")
        top_frame.pack(side="top", fill="x", padx=10, pady=(10, 5))
        
        # Título (CTkLabel)
        ctk.CTkLabel(top_frame, text="Documentos Registrados", font=FONTE_TITULO).pack(side=tk.LEFT)
        
        self.botoes_lista = []
        
        # Botões CTk
        b_novo_doc = ctk.CTkButton(top_frame, text="Novo Documento", width=160, height=35, command=lambda: self.show_frame("Preenchimento"), 
                                   fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE,
                                   font=FONTE_BOLD, corner_radius=8)
        b_novo_doc.pack(side=tk.RIGHT, padx=5)
        self.botoes_lista.append(b_novo_doc)
                     
        b_atualizar_lista = ctk.CTkButton(top_frame, text="Atualizar", width=100, height=35, command=self.carregar_dados_lista, 
                                          fg_color="transparent", hover_color=COR_FRAME,
                                          border_width=1, border_color=COR_BORDA,
                                          font=FONTE_NORMAL, corner_radius=8)
        b_atualizar_lista.pack(side=tk.RIGHT, padx=5)
        self.botoes_lista.append(b_atualizar_lista)

        # Frame de Busca (CTkFrame)
        search_frame = ctk.CTkFrame(f, fg_color=COR_FRAME, corner_radius=8)
        search_frame.pack(side="top", fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(search_frame, text="Buscar:", font=FONTE_NORMAL).pack(side=tk.LEFT, padx=(15, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda name, index, mode: self.buscar_com_reset())
        
        # Entrada de busca (CTkEntry)
        self.search_entry = ctk.CTkEntry(search_frame, 
                                         placeholder_text="Buscar por número, cliente, modelo...",
                                         textvariable=self.search_var,
                                         font=FONTE_NORMAL,
                                         corner_radius=8,
                                         border_width=0,
                                         fg_color="transparent")
        self.search_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=10, pady=10)
        
        # Tabela (ttk.Treeview - mantida)
        tree_frame = ctk.CTkFrame(f, fg_color=COR_FRAME, corner_radius=10)
        tree_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        columns = ("Tipo", "Número", "Cliente", "Modelo/Produto", "Entrada", "Saída", "Garantia", "Situação", "Arquivo")
        self.tabela = ttk.Treeview(tree_frame, columns=columns, show='headings')
        
        # Configuração das colunas (mantida)
        self.tabela.heading("Tipo", text="Tipo")
        self.tabela.column("Tipo", width=50, anchor=tk.CENTER)
        self.tabela.heading("Número", text="Número")
        self.tabela.column("Número", width=80, anchor=tk.CENTER)
        self.tabela.heading("Cliente", text="Cliente")
        self.tabela.column("Cliente", width=150)
        self.tabela.heading("Modelo/Produto", text="Modelo/Produto")
        self.tabela.column("Modelo/Produto", width=150)
        self.tabela.heading("Entrada", text="Entrada")
        self.tabela.column("Entrada", width=80, anchor=tk.CENTER)
        self.tabela.heading("Saída", text="Saída")
        self.tabela.column("Saída", width=80, anchor=tk.CENTER)
        self.tabela.heading("Garantia", text="Garantia")
        self.tabela.column("Garantia", width=80, anchor=tk.CENTER)
        self.tabela.heading("Situação", text="Situação")
        self.tabela.column("Situação", width=100, anchor=tk.CENTER)
        self.tabela.heading("Arquivo", text="Arquivo")
        self.tabela.column("Arquivo", width=50, stretch=tk.NO) 

        # Scrollbar (CTkScrollbar)
        scrollbar = ctk.CTkScrollbar(tree_frame, command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tabela.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Frame de Ações (CTkFrame)
        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # Botões de Ação
        b_ver_pdf = ctk.CTkButton(action_frame, text="Ver PDF", width=120, height=35, command=self.abrir_pdf, 
                                  fg_color=COR_AZUL, hover_color="#0056b3",
                                  font=FONTE_BOLD, corner_radius=8)
        b_ver_pdf.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_ver_pdf)
        
        b_editar = ctk.CTkButton(action_frame, 
                                 text="Editar", 
                                 width=120, height=35,
                                 command=self.editar_documento, 
                                 fg_color="transparent", hover_color=COR_FRAME,
                                 border_width=1, border_color=COR_BORDA,
                                 font=FONTE_BOLD, corner_radius=8)
        b_editar.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_editar)

        b_deletar = ctk.CTkButton(action_frame, text="Deletar", width=120, height=35, command=self.deletar, 
                                  fg_color=COR_VERMELHO, hover_color="#a12731",
                                  font=FONTE_BOLD, corner_radius=8) 
        b_deletar.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_deletar)

        # Frame de Paginação
        pagination_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        pagination_frame.pack(side=tk.RIGHT, padx=5)
        
        self.page_label = ctk.CTkLabel(pagination_frame, text="Página 1 de 1", font=FONTE_NORMAL)
        self.page_label.pack(side=tk.LEFT, padx=10)
        
        b_prev = ctk.CTkButton(pagination_frame, text="< Anterior", width=100, height=35, command=self.pagina_anterior,
                               fg_color=COR_FRAME, hover_color="#3F4243",
                               font=FONTE_NORMAL, corner_radius=8)
        b_prev.pack(side=tk.LEFT, padx=5)
        
        b_next = ctk.CTkButton(pagination_frame, text="Próxima >", width=100, height=35, command=self.pagina_proxima,
                               fg_color=COR_FRAME, hover_color="#3F4243",
                               font=FONTE_NORMAL, corner_radius=8)
        b_next.pack(side=tk.LEFT, padx=5)
        
        self.botoes_lista.append(b_prev)
        self.botoes_lista.append(b_next)
        
        self.carregar_dados_lista()


    def criar_tela_editar(self, parent):
        # Frame para edição, similar ao preenchimento
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self.frames["Editar"] = f
        f.grid(row=0, column=0, sticky="nsew")

        # center_frame
        center_frame = ctk.CTkScrollableFrame(f, fg_color="transparent") # Scrollable
        center_frame.pack(expand=True, fill="both", padx=20, pady=20)
        
        self.vint_edit = f.register(lambda v: v.isdigit() or v == "")
        self.vmoney_edit = f.register(lambda v: all(ch in "0123456789,." for ch in v) and v.count(',') <= 1) 
        self.campos_edit = {}
        self.tel_var_edit = tk.StringVar() 
        self.botoes_editar = []

        def aplicar_e_mostrar_mascara_edit(event):
            raw_text = self.tel_var_edit.get()
            nums_only = "".join(ch for ch in raw_text if ch.isdigit())
            if len(nums_only) >= 10: 
                masked_text = aplicar_mascara_tel(raw_text)
                self.tel_var_edit.set(masked_text)
            else:
                self.tel_var_edit.set(nums_only) 
        
        def on_tipo_garantia_change_edit(event):
            combo_dias = self.campos_edit["dias_garantia"]
            if self.campos_edit["tipo_garantia"].get() == "Com Garantia":
                combo_dias.configure(state="readonly")
            else:
                combo_dias.configure(state="disabled")

        def on_metodo_pagamento_change_edit(event):
            metodo = self.campos_edit["metodo_pagamento"].get()
            combo_parcelas = self.campos_edit["parcelas"]
            label_parcelas = self.campos_edit["parcelas_label"]
            
            if metodo == "PARCELADO NO CREDIÁRIO":
                combo_parcelas.grid(row=8, column=3, sticky="ew", padx=15, pady=(5, 10))
                label_parcelas.grid(row=8, column=2, sticky="w", padx=15, pady=(10, 0))
            else:
                combo_parcelas.grid_forget()
                label_parcelas.grid_forget()
        
        # Título
        ctk.CTkLabel(center_frame, text="Editar Documento", font=FONTE_TITULO).pack(pady=(0, 20))

        # Logo, se existir
        if os.path.exists(LOGO_PADRAO):
            try:
                logo_img_edit = ctk.CTkImage(PILImage.open(LOGO_PADRAO), size=(80, 80))
                logo_label_edit = ctk.CTkLabel(center_frame, image=logo_img_edit, text="")
                logo_label_edit.pack(pady=(0, 10))
                self.logo_edit = logo_img_edit
            except Exception as e:
                print(f"Aviso: Não foi possível carregar a logo: {e}")
                pass

        # Frame dos campos 
        campo_frame = ctk.CTkFrame(center_frame, fg_color=COR_FRAME, corner_radius=10)
        campo_frame.pack(pady=10, padx=20)

        campos_info = [
            ("Cliente*", "cliente"), ("Modelo*", "modelo"),
            ("Telefone*", "telefone"), ("Data de Entrada*", "data_entrada"),
            ("IMEI", "imei"),
            ("Senha/Padrão", "senha"), ("Acessórios", "acessorios"),
            ("Tipo de Garantia*", "tipo_garantia"), ("Método de Pagamento*", "metodo_pagamento"),
            ("Valor (R$)*", "valor"), ("Situacao*", "situacao")
        ]

        W_ENTRY = 200
        COMBO_VALORES = {
            "situacao": ["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA", "NÃO PAGO", "CANCELADA"],
            "tipo_garantia": ["Com Garantia", "Sem Garantia"],
            "metodo_pagamento": ["CARTÃO", "DINHEIRO", "PIX", "PARCELADO NO CREDIÁRIO"],
        }
        
        for i, (label, key) in enumerate(campos_info):
            row = i // 2
            col = (i % 2) * 2

            l = ctk.CTkLabel(campo_frame, text=label, anchor="w", font=FONTE_NORMAL)
            l.grid(row=row, column=col, sticky="w", padx=15, pady=(10, 0))
            self.campos_edit[f"{key}_label"] = l

            if key in COMBO_VALORES:
                e = ctk.CTkComboBox(campo_frame, 
                                    width=W_ENTRY, 
                                    values=COMBO_VALORES[key], 
                                    state="readonly",
                                    font=FONTE_NORMAL,
                                    corner_radius=8)
                if key == "tipo_garantia":
                    e.configure(command=on_tipo_garantia_change_edit)
                elif key == "metodo_pagamento":
                    e.configure(command=on_metodo_pagamento_change_edit)
            else:
                e = ctk.CTkEntry(campo_frame, width=W_ENTRY, font=FONTE_NORMAL, corner_radius=8)
                if key == "telefone":
                    e.configure(validate="key", validatecommand=(self.vint_edit, "%P"), textvariable=self.tel_var_edit)
                    e.bind("<FocusOut>", aplicar_e_mostrar_mascara_edit)
                elif key == "imei":
                    e.configure(validate="key", validatecommand=(self.vint_edit, "%P"))
                elif key == "valor":
                    e.configure(validate="key", validatecommand=(self.vmoney_edit, "%P"))
            
            e.grid(row=row, column=col + 1, sticky="ew", padx=15, pady=(5, 10))
            self.campos_edit[key] = e

        # Dias de Garantia
        dias_row = len(campos_info) // 2
        l_dias = ctk.CTkLabel(campo_frame, text="Dias de Garantia*", anchor="w", font=FONTE_NORMAL)
        l_dias.grid(row=dias_row, column=2, sticky="w", padx=15, pady=(10, 0))
        self.campos_edit["dias_garantia_label"] = l_dias
        
        e_dias = ctk.CTkComboBox(campo_frame, 
                                 width=W_ENTRY, 
                                 state="readonly", 
                                 values=["30 Dias", "90 Dias"],
                                 font=FONTE_NORMAL,
                                 corner_radius=8)
        e_dias.grid(row=dias_row, column=3, sticky="ew", padx=15, pady=(5, 10))
        self.campos_edit["dias_garantia"] = e_dias

        # Parcelas Edit
        l_parcelas_edit = ctk.CTkLabel(campo_frame, text="Qtd. Parcelas", anchor="w", font=FONTE_NORMAL)
        self.campos_edit["parcelas_label"] = l_parcelas_edit
        
        e_parcelas_edit = ctk.CTkComboBox(campo_frame,
                                     width=W_ENTRY,
                                     state="readonly",
                                     values=[f"{i}x" for i in range(1, 13)],
                                     font=FONTE_NORMAL,
                                     corner_radius=8)
        self.campos_edit["parcelas"] = e_parcelas_edit

        # Checklist
        self.checklist_frame_edit = ctk.CTkFrame(campo_frame, fg_color="transparent") 
        self.checklist_frame_edit.grid(row=dias_row + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(15, 5))
        ctk.CTkLabel(self.checklist_frame_edit, text="CHECKLIST (PROBLEMAS/STATUS)", font=FONTE_BOLD).pack(anchor="w", pady=(10, 5))
        
        self.checklist_vars_edit = {}
        checklist_itens = [
            "Tela Display", "Touch Screen", "Teclas", "Sensores de Proximidade", 
            "Bluetooth", "Wi-Fi", "Ligações", "Alto Falante", 
            "Câmera", "Microfone", "Conector Carregador", "Conector Cartão de Memória", 
            "Sim Card", "Outros (Opcional - p/ defeitos internos)"
        ]

        chk_inner_frame = ctk.CTkFrame(self.checklist_frame_edit, fg_color="transparent")
        chk_inner_frame.pack(fill="x")
        
        for i, item in enumerate(checklist_itens):
            col = i // 7
            var = tk.StringVar(value="Não")
            chk = ctk.CTkCheckBox(chk_inner_frame, 
                                  text=item, 
                                  variable=var, 
                                  onvalue="Sim", 
                                  offvalue="Não",
                                  font=FONTE_NORMAL,
                                  corner_radius=15,
                                  border_color=COR_VERDE_PRINCIPAL)
            chk.grid(row=i%7, column=col, sticky="w", padx=10)
            self.checklist_vars_edit[item] = var

        # Campo Detalhe Adicional
        l_detalhe = ctk.CTkLabel(campo_frame, text="Detalhe Adicional (Opcional):", font=FONTE_NORMAL)
        self.campos_edit["problemas_detalhe_label"] = l_detalhe
        l_detalhe.grid(row=dias_row + 2, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 0))
        
        e_detalhe = ctk.CTkEntry(campo_frame, width=W_ENTRY * 2 + 30, font=FONTE_NORMAL, corner_radius=8)
        e_detalhe.grid(row=dias_row + 3, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
        self.campos_edit["problemas_detalhe"] = e_detalhe

        # Botões
        fb = ctk.CTkFrame(center_frame, fg_color="transparent")
        fb.pack(pady=20)
        
        b_salvar_edit = ctk.CTkButton(fb, text="Salvar Alterações", width=200, height=40, command=self.salvar_edicao, 
                                      fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE,
                                      font=FONTE_BOLD, corner_radius=8)
        b_salvar_edit.grid(row=0, column=0, padx=10)
        self.botoes_editar.append(b_salvar_edit)
        
        b_cancelar_edit = ctk.CTkButton(fb, text="Cancelar", width=200, height=40, command=lambda: self.show_frame("Lista"), 
                                        fg_color=COR_VERMELHO, hover_color="#a12731",
                                        font=FONTE_BOLD, corner_radius=8)
        b_cancelar_edit.grid(row=0, column=1, padx=10)
        self.botoes_editar.append(b_cancelar_edit)


    def limpar(self):
        # Limpar CTkEntry
        self.campos["cliente"].delete(0, tk.END)
        self.campos["telefone"].delete(0, tk.END)
        self.campos["modelo"].delete(0, tk.END)
        self.campos["imei"].delete(0, tk.END)
        self.campos["senha"].delete(0, tk.END)
        self.campos["acessorios"].delete(0, tk.END)
        self.campos["valor"].delete(0, tk.END)
        self.campos["valor"].insert(0, "0,00")
        self.campos["problemas_detalhe"].delete(0, tk.END) 
        
        # NOVO: Limpar e resetar a data de entrada
        self.campos["data_entrada"].delete(0, tk.END)
        self.campos["data_entrada"].insert(0, datetime.now().strftime("%d/%m/%Y"))

        # Limpar CTkComboBox
        self.campos["situacao"].set("EM ABERTO")
        self.campos["tipo_garantia"].set("Com Garantia")
        self.campos["metodo_pagamento"].set("CARTÃO")
        self.campos["dias_garantia"].set("90 Dias") 
        self.dias_garantia_var.set("90 Dias") 
        self.parcelas_var.set("1x")
        self.campos["parcelas"].grid_forget()
        self.campos["parcelas_label"].grid_forget()

        # Limpar checklist (CTkCheckBox)
        for var in self.checklist_vars.values():
            var.set("Não")

        self.gerar_numero_documento()
        self.campos["dias_garantia"].configure(state="readonly") 

    
    def salvar(self):
        # 1. Coleta e validação de dados
        cliente = self.campos["cliente"].get().strip()
        telefone = self.campos["telefone"].get().strip()
        modelo = self.campos["modelo"].get().strip()
        valor_str = self.campos["valor"].get().strip()
        
        if not all([cliente, telefone, modelo, valor_str]):
            messagebox.showwarning("Aviso", "Os campos 'Cliente', 'Telefone', 'Modelo/Produto' e 'Valor (R$)' são obrigatórios.")
            return

        try:
            total_float = parse_monetario_to_float(valor_str)
            valor_texto = formatar_monetario(total_float)
        except ValueError:
            messagebox.showerror("Erro de Valor", "Formato de valor (R$) inválido.")
            return

        # COLETANDO DATA DE ENTRADA (USANDO O VALOR DO CAMPO EDITÁVEL)
        entrada = self.campos["data_entrada"].get().strip()
        if not entrada:
            entrada = datetime.now().strftime("%d/%m/%Y") # Fallback, embora o campo já venha preenchido.

        # 2. Coleta de dados restantes
        numero = self.numero_documento 
        imei = self.campos["imei"].get().strip()
        senha = self.campos["senha"].get().strip()
        acessorios = self.campos["acessorios"].get().strip()
        problemas = self.campos["problemas_detalhe"].get().strip()
        situacao = self.campos["situacao"].get()
        tipo_garantia = self.campos["tipo_garantia"].get()
        metodo_pagamento = self.campos["metodo_pagamento"].get()
        tipo_documento = self.tipo_documento_var.get()

        saida = ""
        if situacao == "CONCLUÍDA":
            saida = datetime.now().strftime("%d/%m/%Y")

        dias_garantia_texto = self.dias_garantia_var.get().replace(" Dias", "")
        try:
            dias_garantia_num = int(dias_garantia_texto) if dias_garantia_texto.isdigit() else 0
        except:
            dias_garantia_num = 0

        # >>> AJUSTE NA LÓGICA DE GARANTIA: SÓ CALCULA SE FOR CONCLUÍDA <<<
        garantia = "S/Garantia"
        if situacao == "CONCLUÍDA" and tipo_garantia == "Com Garantia" and dias_garantia_num > 0:
            # Garante que a garantia é calculada a partir da data de entrada
            try:
                data_base = datetime.strptime(entrada, "%d/%m/%Y")
                data_garantia = data_base + timedelta(days=dias_garantia_num)
                garantia = data_garantia.strftime("%d/%m/%Y")
            except ValueError:
                # Se a data de entrada for inválida (raro, mas possível), usa a data atual
                data_garantia = datetime.now() + timedelta(days=dias_garantia_num)
                garantia = data_garantia.strftime("%d/%m/%Y")
        # >>> FIM DO AJUSTE <<<

        checklist_data = [f"{item}:{var.get()}" for item, var in self.checklist_vars.items()]
        checklist_str = ";".join(checklist_data)

        # Lógica de Parcelas
        detalhes_parcelas_json = ""
        num_parcelas = 1
        if metodo_pagamento == "PARCELADO NO CREDIÁRIO":
            try:
                num_parcelas = int(self.parcelas_var.get().replace("x", ""))
                lista_parcelas = []
                valor_parcela = total_float / num_parcelas
                
                data_base = datetime.strptime(entrada, "%d/%m/%Y")
                
                for i in range(1, num_parcelas + 1):
                    data_venc = data_base + timedelta(days=30 * i)
                    lista_parcelas.append({
                        "numero": i,
                        "vencimento": data_venc.strftime("%d/%m/%Y"),
                        "valor": formatar_monetario(valor_parcela),
                        "status": "N/PG"
                    })
                detalhes_parcelas_json = json.dumps(lista_parcelas)
            except:
                num_parcelas = 1

        # 3. Estruturação dos dados
        dados_db = {
            "numero": numero,
            "cliente": cliente,
            "telefone": telefone,
            "modelo": modelo,
            "imei": imei,
            "senha": senha,
            "acessorios": acessorios,
            "problemas": problemas,
            "situacao": situacao,
            "valor": valor_texto,
            "entrada": entrada,
            "saida": saida,
            "garantia": garantia, # Valor de garantia ajustado
            "tipo_garantia": tipo_garantia,
            "metodo_pagamento": metodo_pagamento,
            "checklist": checklist_str,
            "dias_garantia": dias_garantia_num,
            "tipo_documento": tipo_documento,
            "parcelas": num_parcelas,
            "detalhes_parcelas": detalhes_parcelas_json
        }
        
        # 4. Geração do PDF
        caminho_pdf = gerar_documento(dados_db, valor_texto, total_float, tipo_garantia, metodo_pagamento, checklist_str, tipo_documento, dias_garantia_num, detalhes_parcelas_json)
        
        if caminho_pdf:
            # 5. Inserção no Banco de Dados
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                
                cols = ", ".join(dados_db.keys())
                placeholders = ", ".join("?" * len(dados_db))
                values = tuple(dados_db.values()) + (caminho_pdf,)
                
                c.execute(f"INSERT INTO os ({cols}, arquivo) VALUES ({placeholders}, ?)", values)
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Sucesso", f"{tipo_documento} {numero} salva com sucesso e PDF gerado:\n{caminho_pdf}")
                
                abrir_arquivo(caminho_pdf)
                
                self.limpar()

            except sqlite3.Error as e:
                messagebox.showerror("Erro no DB", f"Erro ao salvar no banco de dados: {str(e)}")
            except Exception as e:
                messagebox.showerror("Erro Inesperado", f"Erro: {str(e)}")
        else:
            messagebox.showerror("Erro", f"Não foi possível salvar o documento.")

    def carregar_dados_lista(self, search="", page=1):
        """Carrega os dados do banco para a Treeview, aplicando filtro de busca e paginação."""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        for item in self.tabela.get_children():
            self.tabela.delete(item)

        # Contar total de registros para paginação
        count_query = "SELECT COUNT(*) FROM os"
        count_params = []
        if search:
            search_pattern = f"%{search}%"
            count_query += " WHERE numero LIKE ? OR cliente LIKE ? OR modelo LIKE ? OR imei LIKE ? OR problemas LIKE ?"
            count_params = [search_pattern] * 5
        
        c.execute(count_query, count_params)
        self.total_records = c.fetchone()[0]
        
        # Calcular offset
        offset = (page - 1) * self.page_size
        
        query = "SELECT * FROM os"
        params = []
        
        if search:
            search_pattern = f"%{search}%"
            query += " WHERE numero LIKE ? OR cliente LIKE ? OR modelo LIKE ? OR imei LIKE ? OR problemas LIKE ?"
            params = [search_pattern] * 5 

        query += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([self.page_size, offset])
        
        try:
            c.execute(query, params)
            rows = c.fetchall()
            conn.close()

            col_names = [description[0] for description in c.description]
            
            def get_val(row, name):
                try:
                    return row[col_names.index(name)]
                except ValueError:
                    return "" 

            for row in rows:
                tipo = get_val(row, "tipo_documento")
                numero = get_val(row, "numero")
                cliente = get_val(row, "cliente")
                modelo = get_val(row, "modelo")
                entrada = get_val(row, "entrada")
                saida = get_val(row, "saida") or "N/A" # Se for None, exibe N/A
                garantia = get_val(row, "garantia")
                situacao = get_val(row, "situacao")
                arquivo = get_val(row, "arquivo") 

                self.tabela.insert("", tk.END, values=(tipo, numero, cliente, modelo, entrada, saida, garantia, situacao, arquivo))

            # Atualizar controles de paginação
            self.atualizar_controle_paginacao()

        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Erro ao carregar dados do banco: {str(e)}")
            
    def atualizar_controle_paginacao(self):
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if total_pages == 0:
            total_pages = 1
        self.page_label.configure(text=f"Página {self.current_page} de {total_pages}")
    
    def pagina_anterior(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.carregar_dados_lista(search=self.search_var.get(), page=self.current_page)
    
    def pagina_proxima(self):
        total_pages = (self.total_records + self.page_size - 1) // self.page_size
        if self.current_page < total_pages:
            self.current_page += 1
            self.carregar_dados_lista(search=self.search_var.get(), page=self.current_page)
    
    def buscar_com_reset(self):
        self.current_page = 1
        self.carregar_dados_lista(search=self.search_var.get(), page=self.current_page)
            
    def editar_documento(self):
        item = self.tabela.focus()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um documento na lista para editar!")
            return

        values = self.tabela.item(item)['values']
        tipo_documento = values[0]
        numero = values[1]

        metodo_combo = self.campos_edit["metodo_pagamento"]
        if tipo_documento == "OS":
            metodo_combo.configure(values=["CARTÃO", "DINHEIRO", "PIX"])
        else:
            metodo_combo.configure(values=["CARTÃO", "DINHEIRO", "PIX", "PARCELADO NO CREDIÁRIO"])
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM os WHERE numero=? AND tipo_documento=?", (numero, tipo_documento))
        row = c.fetchone()
        conn.close()
        
        if not row:
            messagebox.showerror("Erro", "Registro não encontrado no banco de dados.")
            return

        col_names = [description[0] for description in c.description]
        dados = dict(zip(col_names, row))
        
        # Preencher campos
        self.campos_edit["cliente"].delete(0, tk.END)
        self.campos_edit["cliente"].insert(0, dados.get("cliente", ""))
        
        self.campos_edit["modelo"].delete(0, tk.END)
        self.campos_edit["modelo"].insert(0, dados.get("modelo", ""))
        
        self.tel_var_edit.set(dados.get("telefone", ""))
        
        self.campos_edit["data_entrada"].delete(0, tk.END)
        self.campos_edit["data_entrada"].insert(0, dados.get("entrada", ""))
        
        self.campos_edit["imei"].delete(0, tk.END)
        self.campos_edit["imei"].insert(0, dados.get("imei", ""))
        
        self.campos_edit["senha"].delete(0, tk.END)
        self.campos_edit["senha"].insert(0, dados.get("senha", ""))
        
        self.campos_edit["acessorios"].delete(0, tk.END)
        self.campos_edit["acessorios"].insert(0, dados.get("acessorios", ""))
        
        self.campos_edit["tipo_garantia"].set(dados.get("tipo_garantia", "Com Garantia"))
        
        self.campos_edit["metodo_pagamento"].set(dados.get("metodo_pagamento", "CARTÃO"))
        
        self.campos_edit["valor"].delete(0, tk.END)
        self.campos_edit["valor"].insert(0, dados.get("valor", "0,00"))
        
        self.campos_edit["situacao"].set(dados.get("situacao", "EM ABERTO"))
        
        dias = f"{dados.get('dias_garantia', 90)} Dias"
        self.campos_edit["dias_garantia"].set(dias)
        
        # Parcelas
        num_parcelas = dados.get("parcelas", 1)
        self.campos_edit["parcelas"].set(f"{num_parcelas}x")
        if dados.get("metodo_pagamento") == "PARCELADO NO CREDIÁRIO":
            self.campos_edit["parcelas"].grid(row=8, column=3, sticky="ew", padx=15, pady=(5, 10))
            self.campos_edit["parcelas_label"].grid(row=8, column=2, sticky="w", padx=15, pady=(10, 0))
        else:
            self.campos_edit["parcelas"].grid_forget()
            self.campos_edit["parcelas_label"].grid_forget()

        # Checklist
        checklist_str = dados.get("checklist", "")
        itens_check = [item.split(':')[0] for item in checklist_str.split(';') if item.strip()]
        for item in self.checklist_vars_edit:
            if item in itens_check:
                self.checklist_vars_edit[item].set("Sim")
            else:
                self.checklist_vars_edit[item].set("Não")
        
        # Detalhe
        self.campos_edit["problemas_detalhe"].delete(0, tk.END)
        self.campos_edit["problemas_detalhe"].insert(0, dados.get("problemas", ""))
        
        # Armazenar dados originais para edição
        self.dados_originais = dados
        
        # Mostrar tela de edição
        self.show_frame("Editar")

    def salvar_edicao(self):
        # Validação
        cliente = self.campos_edit["cliente"].get().strip()
        telefone = self.campos_edit["telefone"].get().strip()
        modelo = self.campos_edit["modelo"].get().strip()
        valor_str = self.campos_edit["valor"].get().strip()
        
        if not all([cliente, telefone, modelo, valor_str]):
            messagebox.showwarning("Aviso", "Os campos 'Cliente', 'Telefone', 'Modelo/Produto' e 'Valor (R$)' são obrigatórios.")
            return

        try:
            total_float = parse_monetario_to_float(valor_str)
            valor_texto = formatar_monetario(total_float)
        except ValueError:
            messagebox.showerror("Erro de Valor", "Formato de valor (R$) inválido.")
            return

        # Coletar dados
        entrada = self.campos_edit["data_entrada"].get().strip()
        imei = self.campos_edit["imei"].get().strip()
        senha = self.campos_edit["senha"].get().strip()
        acessorios = self.campos_edit["acessorios"].get().strip()
        problemas = self.campos_edit["problemas_detalhe"].get().strip()
        situacao = self.campos_edit["situacao"].get()
        tipo_garantia = self.campos_edit["tipo_garantia"].get()
        metodo_pagamento = self.campos_edit["metodo_pagamento"].get()
        tipo_documento = self.dados_originais["tipo_documento"]
        numero = self.dados_originais["numero"]

        saida = ""
        if situacao == "CONCLUÍDA":
            saida = datetime.now().strftime("%d/%m/%Y")

        dias_garantia_texto = self.campos_edit["dias_garantia"].get().replace(" Dias", "")
        try:
            dias_garantia_num = int(dias_garantia_texto) if dias_garantia_texto.isdigit() else 0
        except:
            dias_garantia_num = 0

        garantia = "S/Garantia"
        if situacao == "CONCLUÍDA" and tipo_garantia == "Com Garantia" and dias_garantia_num > 0:
            try:
                data_base = datetime.strptime(entrada, "%d/%m/%Y")
                data_garantia = data_base + timedelta(days=dias_garantia_num)
                garantia = data_garantia.strftime("%d/%m/%Y")
            except ValueError:
                data_garantia = datetime.now() + timedelta(days=dias_garantia_num)
                garantia = data_garantia.strftime("%d/%m/%Y")

        checklist_data = [f"{item}:{var.get()}" for item, var in self.checklist_vars_edit.items()]
        checklist_str = ";".join(checklist_data)

        # Lógica de Parcelas (Recalcular se mudar o método ou valor)
        detalhes_parcelas_json = self.dados_originais.get("detalhes_parcelas", "")
        num_parcelas = self.dados_originais.get("parcelas", 1)
        
        if metodo_pagamento == "PARCELADO NO CREDIÁRIO":
             # Se mudou para crediário ou alterou parcelas, recalcula
             nova_qtd = int(self.campos_edit["parcelas"].get().replace("x", ""))
             if nova_qtd != num_parcelas or not detalhes_parcelas_json or metodo_pagamento != self.dados_originais.get("metodo_pagamento"):
                num_parcelas = nova_qtd
                lista_parcelas = []
                valor_parcela = total_float / num_parcelas
                try:
                    data_base = datetime.strptime(entrada, "%d/%m/%Y")
                except:
                    data_base = datetime.now()
                
                for i in range(1, num_parcelas + 1):
                    data_venc = data_base + timedelta(days=30 * i)
                    lista_parcelas.append({"numero": i, "vencimento": data_venc.strftime("%d/%m/%Y"), "valor": formatar_monetario(valor_parcela), "status": "N/PG"})
                detalhes_parcelas_json = json.dumps(lista_parcelas)
        else:
            detalhes_parcelas_json = ""
            num_parcelas = 1

        # Estrutura dados
        dados_atualizados = {
            "cliente": cliente,
            "telefone": telefone,
            "modelo": modelo,
            "imei": imei,
            "senha": senha,
            "acessorios": acessorios,
            "problemas": problemas,
            "situacao": situacao,
            "valor": valor_texto,
            "entrada": entrada,
            "saida": saida,
            "garantia": garantia,
            "tipo_garantia": tipo_garantia,
            "metodo_pagamento": metodo_pagamento,
            "checklist": checklist_str,
            "dias_garantia": dias_garantia_num,
            "parcelas": num_parcelas,
            "detalhes_parcelas": detalhes_parcelas_json
        }
        
        # Gerar novo PDF
        dados_para_pdf = dados_atualizados.copy()
        dados_para_pdf["numero"] = numero
        caminho_pdf = gerar_documento(dados_para_pdf, valor_texto, total_float, tipo_garantia, metodo_pagamento, checklist_str, tipo_documento, dias_garantia_num, detalhes_parcelas_json)
        
        if not caminho_pdf:
            messagebox.showerror("Erro", "Não foi possível regerar o documento.")
            return

        # Adicionar arquivo aos dados
        dados_atualizados["arquivo"] = caminho_pdf

        # Atualizar banco
        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()
            c.execute("""
                UPDATE os SET cliente=?, telefone=?, modelo=?, imei=?, senha=?, acessorios=?, problemas=?, 
                situacao=?, valor=?, entrada=?, saida=?, garantia=?, tipo_garantia=?, metodo_pagamento=?, 
                checklist=?, dias_garantia=?, parcelas=?, detalhes_parcelas=?, arquivo=? 
                WHERE numero=? AND tipo_documento=?
            """, tuple(dados_atualizados.values()) + (numero, tipo_documento))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Sucesso", f"{tipo_documento} {numero} atualizado com sucesso!")
            
            # Voltar para lista e recarregar
            self.show_frame("Lista")
            self.buscar_com_reset()
            
        except sqlite3.Error as e:
            messagebox.showerror("Erro no DB", f"Erro ao atualizar no banco de dados: {str(e)}")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", f"Erro: {str(e)}")

    def deletar(self):
        """Deleta o registro selecionado e seu arquivo PDF associado."""
        item = self.tabela.focus()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um documento para deletar!")
            return

        values = self.tabela.item(item)['values']
        tipo_documento = values[0]
        numero = values[1]
        caminho_pdf = values[8] 

        if messagebox.askyesno("Confirmação", f"Tem certeza que deseja deletar o documento {numero} ({tipo_documento})?"):
            try:
                conn = sqlite3.connect(DB_NAME)
                c = conn.cursor()
                c.execute("DELETE FROM os WHERE numero=? AND tipo_documento=?", (numero, tipo_documento))
                conn.commit()
                conn.close()

                if caminho_pdf and os.path.exists(caminho_pdf):
                    os.remove(caminho_pdf)
                
                messagebox.showinfo("Sucesso", f"Documento {numero} deletado e arquivo PDF removido.")
                self.buscar_com_reset()

            except sqlite3.Error as e:
                messagebox.showerror("Erro", f"Erro ao deletar no banco de dados: {str(e)}")
            except OSError as e:
                messagebox.showwarning("Aviso", f"Registro deletado do DB, mas o arquivo PDF não pôde ser removido.\nPode estar aberto em outro programa. Erro: {str(e)}")


    def atualizar_status_documento(self):
        """Atualiza o status (situação) de um registro e regera o PDF."""
        item = self.tabela.focus()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um documento na lista para atualizar o status!")
            return

        novo_status = self.novo_status_var.get()
        values = self.tabela.item(item)['values']
        tipo_documento = values[0]
        numero = values[1]
        
        if novo_status == values[7]: # values[7] é a Situação/Status atual
            messagebox.showinfo("Aviso", f"O status já é '{novo_status}'. Nenhuma alteração necessária.")
            return

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM os WHERE numero=? AND tipo_documento=?", (numero, tipo_documento))
        row = c.fetchone()
        
        if not row:
            conn.close()
            messagebox.showerror("Erro", "Registro não encontrado no banco de dados.")
            return

        col_names = [description[0] for description in c.description]
        dados_db = dict(zip(col_names, row))
        
        # Atualiza o status e a data de saída (se necessário)
        dados_db["situacao"] = novo_status 
        
        data_saida = ""
        # Preenche a data de saída APENAS se o novo status for CONCLUÍDA
        if novo_status == "CONCLUÍDA":
             data_saida = datetime.now().strftime("%d/%m/%Y")
        
        dados_db["saida"] = data_saida
        
        # >>> NOVO: Recalcula a garantia com base no novo status <<<
        
        tipo_garantia = dados_db["tipo_garantia"]
        dias_garantia_num = dados_db["dias_garantia"]
        entrada = dados_db["entrada"] # Usa a data original de entrada
        
        novo_garantia = "S/Garantia" # Valor padrão
        
        if novo_status == "CONCLUÍDA" and tipo_garantia == "Com Garantia" and dias_garantia_num > 0:
            try:
                # Usa a data de entrada original para calcular a garantia
                data_base = datetime.strptime(entrada, "%d/%m/%Y")
                data_garantia = data_base + timedelta(days=dias_garantia_num)
                novo_garantia = data_garantia.strftime("%d/%m/%Y")
            except ValueError:
                # Fallback, usa a data atual (improvável, mas seguro)
                data_garantia = datetime.now() + timedelta(days=dias_garantia_num)
                novo_garantia = data_garantia.strftime("%d/%m/%Y")
                
        dados_db["garantia"] = novo_garantia # Atualiza o campo garantia
        
        # >>> FIM DA NOVA LÓGICA <<<
        
        # Garante que temos o valor monetário formatado para a regeração do PDF
        valor_texto = dados_db["valor"]
        try:
            total_float = parse_monetario_to_float(valor_texto)
        except ValueError:
             total_float = 0.0 # Fallback
        
        # Corrigido o dicionário de dados para regeneração (baseado no código original)
        dados_regeneracao = {
            "numero": dados_db["numero"],
            "cliente": dados_db["cliente"],
            "telefone": dados_db["telefone"],
            "modelo": dados_db["modelo"],
            "imei": dados_db["imei"],
            "senha": dados_db["senha"],
            "acessorios": dados_db["acessorios"],
            "problemas": dados_db["problemas"],
            "situacao": dados_db["situacao"], # NOVO STATUS
            "entrada": dados_db["entrada"],
            "saida": dados_db["saida"],     # NOVA SAÍDA
            "garantia": dados_db["garantia"] # NOVA GARANTIA
        }
        
        # 1. Regerar o PDF
        novo_pdf = gerar_documento(
            dados_regeneracao,
            valor_texto,
            total_float,
            dados_db["tipo_garantia"],
            dados_db["metodo_pagamento"],
            dados_db["checklist"],
            tipo_documento,
            dados_db["dias_garantia"],
            dados_db.get("detalhes_parcelas")
        )

        if not novo_pdf:
            conn.close()
            messagebox.showerror("Erro", "Não foi possível regerar o PDF com o novo status.")
            return

        # 2. Atualizar o DB - INCLUSÃO DO CAMPO 'GARANTIA' NO UPDATE
        c.execute("""
            UPDATE os SET situacao=?, saida=?, garantia=?, arquivo=? 
            WHERE numero=? AND tipo_documento=?
        """, (dados_db["situacao"], dados_db["saida"], dados_db["garantia"], novo_pdf, numero, tipo_documento))

        conn.commit()
        conn.close()
        
        # 3. Atualizar a Treeview
        dados = {k: dados_regeneracao.get(k, "") for k in dados_regeneracao} 
        self.tabela.item(item, values=(
            tipo_documento, numero, dados["cliente"], dados["modelo"], dados["entrada"],
            dados["saida"] or "N/A", dados["garantia"], dados["situacao"], novo_pdf
        ))

        messagebox.showinfo("OK", f"Status do {tipo_documento} {numero} atualizado para '{novo_status}' e documento regenerado!")


    def atualizar_valor_os(self):
        """Atualiza o valor de um registro, força o status para CONCLUÍDA e regera o PDF."""
        item = self.tabela.focus()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um documento na lista para atualizar!")
            return

        novo_valor_str = self.entry_novo_valor.get().strip()
        if not novo_valor_str:
            messagebox.showwarning("Aviso", "Insira um novo valor no campo abaixo.")
            return

        try:
            novo_total_float = parse_monetario_to_float(novo_valor_str)
            novo_valor_texto = formatar_monetario(novo_total_float)
        except ValueError:
            messagebox.showerror("Erro de Valor", "Formato de novo valor (R$) inválido.")
            return

        values = self.tabela.item(item)['values']
        tipo_documento = values[0]
        numero = values[1]
        
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute("SELECT * FROM os WHERE numero=? AND tipo_documento=?", (numero, tipo_documento))
        row = c.fetchone()
        
        if not row:
            conn.close()
            messagebox.showerror("Erro", "Registro não encontrado no banco de dados.")
            return

        col_names = [description[0] for description in c.description]
        dados_db = dict(zip(col_names, row))
        
        dados_db["valor"] = novo_valor_texto
        
        status_anterior = dados_db["situacao"]
        
        # Se for atualizar o valor, assumimos que o serviço foi concluído (se não estiver cancelado)
        if dados_db["situacao"] != "CANCELADA":
            dados_db["situacao"] = "CONCLUÍDA" 
            if not dados_db["saida"] or dados_db["saida"] == "N/A":
                 dados_db["saida"] = datetime.now().strftime("%d/%m/%Y")

        # >>> NOVO: Recalcula a garantia se o status foi alterado/mantido como CONCLUÍDA <<<
        if dados_db["situacao"] == "CONCLUÍDA" and dados_db["tipo_garantia"] == "Com Garantia":
            tipo_garantia = dados_db["tipo_garantia"]
            dias_garantia_num = dados_db["dias_garantia"]
            entrada = dados_db["entrada"]
            
            novo_garantia = "S/Garantia" 
            
            if dias_garantia_num > 0:
                try:
                    data_base = datetime.strptime(entrada, "%d/%m/%Y")
                    data_garantia = data_base + timedelta(days=dias_garantia_num)
                    novo_garantia = data_garantia.strftime("%d/%m/%Y")
                except ValueError:
                    data_garantia = datetime.now() + timedelta(days=dias_garantia_num)
                    novo_garantia = data_garantia.strftime("%d/%m/%Y")
            
            dados_db["garantia"] = novo_garantia
        # Se o status for CANCELADA, a garantia deve ser mantida como S/Garantia, o que já está implícito
        # pois o valor inicial do banco é 'S/Garantia' e só é calculado aqui se for 'CONCLUÍDA'.
        # >>> FIM DA NOVA LÓGICA <<<

        # Corrigido o dicionário de dados para regeneração
        dados_regeneracao = {
            "numero": dados_db["numero"],
            "cliente": dados_db["cliente"],
            "telefone": dados_db["telefone"],
            "modelo": dados_db["modelo"],
            "imei": dados_db["imei"],
            "senha": dados_db["senha"],
            "acessorios": dados_db["acessorios"],
            "problemas": dados_db["problemas"],
            "situacao": dados_db["situacao"],
            "entrada": dados_db["entrada"],
            "saida": dados_db["saida"],
            "garantia": dados_db["garantia"] # Garantia ajustada
        }
        
        novo_pdf = gerar_documento(
            dados_regeneracao,
            novo_valor_texto,
            novo_total_float,
            dados_db["tipo_garantia"],
            dados_db["metodo_pagamento"],
            dados_db["checklist"],
            tipo_documento,
            dados_db["dias_garantia"],
            dados_db.get("detalhes_parcelas")
        )

        if not novo_pdf:
            conn.close()
            messagebox.showerror("Erro", "Não foi possível regerar o PDF.")
            return

        # 2. Atualizar o DB - INCLUSÃO DO CAMPO 'GARANTIA' NO UPDATE
        c.execute("""
            UPDATE os SET valor=?, situacao=?, saida=?, garantia=?, arquivo=? 
            WHERE numero=? AND tipo_documento=?
        """, (novo_valor_texto, dados_db["situacao"], dados_db["saida"], dados_db["garantia"], novo_pdf, numero, tipo_documento))

        conn.commit()
        conn.close()
        
        self.entry_novo_valor.delete(0, tk.END) 
        
        dados = {k: dados_regeneracao.get(k, "") for k in dados_regeneracao} 
        self.tabela.item(item, values=(
            tipo_documento, numero, dados["cliente"], dados["modelo"], dados["entrada"],
            dados["saida"] or "N/A", dados["garantia"], dados["situacao"], novo_pdf
        ))

        messagebox.showinfo("OK", f"Valor do {tipo_documento} atualizado e documento regenerado!")


    def abrir_pdf(self):
        """Abre o PDF selecionado de forma compatível com diferentes sistemas operacionais."""
        item = self.tabela.focus()
        if not item:
            messagebox.showwarning("Aviso", "Selecione um documento na lista!")
            return
        
        try:
            caminho_pdf = self.tabela.item(item)["values"][8]
            if not caminho_pdf or not os.path.exists(caminho_pdf):
                messagebox.showerror("Erro", f"Arquivo PDF não encontrado:\n{caminho_pdf}")
                return
            abrir_arquivo(caminho_pdf)
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao abrir o PDF:\n{str(e)}")


if __name__ == "__main__":
    criar_banco()
    # Substitui Tk() por ctk.CTk()
    root = ctk.CTk()
    SistemaOS(root)
    root.mainloop()