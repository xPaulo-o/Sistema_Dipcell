# SISTEMA DE OS DIPCELL (COM CHECKLIST, ATUALIZAÇÃO, VALOR E FUNÇÃO VENDAS)

import os
import sys 
import sqlite3
from datetime import datetime, timedelta
import tkinter as tk # Manter tkinter para constantes (tk.END) e Treeview
from tkinter import ttk, messagebox

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
COR_VERDE_PRINCIPAL = '#2E8B57' 
COR_VERMELHO = "#DC3545" 
COR_AZUL = "#007BFF" 
COR_HOVER_VERDE = "#226C41" # Variação mais escura para o hover

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
            "tipo_documento": "TEXT" 
        }

        for col, tipo in obrig.items():
            if col not in cols:
                try:
                    if col == "dias_garantia":
                        default_val = "90"
                    elif col == "tipo_documento":
                        default_val = "'OS'"
                    else:
                        default_val = "'Com Garantia'"
                        
                    c.execute(f"ALTER TABLE os ADD COLUMN {col} {tipo} DEFAULT {default_val}")
                    conn.commit()
                except sqlite3.Error as e:
                    print(f"Aviso: Não foi possível adicionar coluna {col}: {e}")
                    pass

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

def gerar_documento(dados, valor_texto, total_float, tipo_garantia, metodo_pagamento, checklist_str, tipo_documento, dias_garantia_num):
    # Código da função gerar_documento (mantido inalterado)
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
        
        # O CustomTkinter gerencia a cor de fundo globalmente
        
        # Configuração do estilo da Treeview (necessária, pois CTk não a substitui)
        style = ttk.Style()
        style.theme_use('clam') 
        # Cores para a Treeview em modo escuro
        style.configure("Treeview", 
                        background="#2c2c2c", 
                        foreground="white", 
                        fieldbackground="#2c2c2c", 
                        rowheight=25, 
                        font=('Arial', 10))
        # O tema "green" do CTk cuida do highlight, mas reforçamos o fundo
        style.map('Treeview', background=[('selected', COR_VERDE_PRINCIPAL)]) 
        style.configure("Treeview.Heading", 
                        font=('Arial', 11, 'bold'), 
                        background="#3c3c3c", 
                        foreground="white")
        # ----------------------------------------------------

        # Container principal agora é um CTkFrame, usando fg_color="transparent" para se misturar ao root
        self.container = ctk.CTkFrame(master, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew") 

        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        self.tipo_documento_var = tk.StringVar(value="OS") 
        self.dias_garantia_var = tk.StringVar(value="90 Dias") 
        # NOVO: Variável para a Data de Entrada, inicializada com a data atual
        self.data_entrada_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        
        self.criar_tela_preenchimento(self.container)
        self.criar_tela_lista(self.container)

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
            self.carregar_dados_lista() 

    def criar_tela_preenchimento(self, parent):
        # Substitui Frame por CTkFrame
        f = ctk.CTkFrame(parent, fg_color="transparent")
        self.frames["Preenchimento"] = f
        f.grid(row=0, column=0, sticky="nsew")

        # center_frame agora é CTkFrame
        center_frame = ctk.CTkFrame(f, fg_color="transparent")
        center_frame.place(relx=0.5, rely=0.5, anchor=tk.CENTER) 
        
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
                situacao_combo.configure(values=["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA"])
            else:
                situacao_combo.set("CONCLUÍDA")
                situacao_combo.configure(values=["CONCLUÍDA", "CANCELADA"]) # Opções limitadas para VENDA

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


        # Logo (Usa tk.Label pois a imagem é PIL.ImageTk)
        if os.path.exists(LOGO_PADRAO):
            try:
                l = ImageTk.PhotoImage(PILImage.open(LOGO_PADRAO).resize((120, 120)))
                
                # --- CORREÇÃO ROBUSTA DA COR DE FUNDO PARA RESOLVER O ERRO DE ÍNDICE ---
                app_mode = ctk.get_appearance_mode().lower() # 'dark' ou 'light'
                bg_color_data = ctk.ThemeManager.theme["CTk"]["fg_color"]
                current_bg_color = None

                # Tenta obter a cor de fundo, tratando lista/tupla ou dicionário
                if isinstance(bg_color_data, dict):
                    # Ex: {"dark": "#242424", "light": "#F0F0F0"}
                    current_bg_color = bg_color_data.get(app_mode)
                elif isinstance(bg_color_data, (list, tuple)) and len(bg_color_data) == 2:
                    # Ex: ["#F0F0F0", "#242424"] (Índice 0: Light, Índice 1: Dark)
                    index = 0 if app_mode == "light" else 1
                    current_bg_color = bg_color_data[index]
                
                # Se a cor obtida for uma tupla de cores (ex: ['#343638', '#343638']), extrai a cor base
                if isinstance(current_bg_color, (list, tuple)) and len(current_bg_color) >= 1:
                    index = 0 if app_mode == "light" else 1
                    current_bg_color = current_bg_color[index]
                    
                # Fallback seguro caso a cor ainda seja None ou não-string
                if not isinstance(current_bg_color, str) or not current_bg_color:
                    current_bg_color = "#242424" if app_mode == "dark" else "#F0F0F0"
                
                # Usa a cor obtida com o argumento 'bg' do tk.Label
                tk.Label(center_frame, image=l, bg=current_bg_color, relief="flat").pack(pady=(0, 10))
                self.logo = l
                # ----------------------------------------------------------------------------------
            except Exception as e:
                print(f"Aviso: Não foi possível carregar a logo ou aplicar a cor de fundo: {e}")
                pass


        # Seleção OS/VENDA
        tipo_doc_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
        tipo_doc_frame.pack(pady=5)
        ctk.CTkLabel(tipo_doc_frame, text="Tipo de Documento:").pack(side=tk.LEFT, padx=5)
        # Substitui ttk.Combobox por CTkComboBox
        cb_tipo_doc = ctk.CTkComboBox(tipo_doc_frame, 
                                     width=200, 
                                     values=["OS", "VENDA"], 
                                     command=alternar_tipo_documento,
                                     variable=self.tipo_documento_var)
        cb_tipo_doc.set("OS")
        cb_tipo_doc.pack(side=tk.LEFT)

        # Frame dos campos 
        campo_frame = ctk.CTkFrame(center_frame, fg_color="transparent")
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
            "situacao": ["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA"],
            "tipo_garantia": ["Com Garantia", "Sem Garantia"],
            "metodo_pagamento": ["CARTÃO", "DINHEIRO", "PIX"],
        }
        
        for i, (label, key) in enumerate(campos_info):
            row = i // 2
            col = (i % 2) * 2

            # Label (CTkLabel)
            l = ctk.CTkLabel(campo_frame, text=label, anchor="w")
            l.grid(row=row, column=col, sticky="w", padx=10, pady=(5, 0))
            self.campos[f"{key}_label"] = l

            # Entrada (CTkEntry ou CTkComboBox)
            if key in COMBO_VALORES:
                e = ctk.CTkComboBox(campo_frame, 
                                    width=W_ENTRY, 
                                    values=COMBO_VALORES[key], 
                                    state="readonly")
                e.set(COMBO_VALORES[key][0]) # Define o valor inicial
                
                if key == "tipo_garantia":
                    e.configure(command=on_tipo_garantia_change)
            
            else:
                e = ctk.CTkEntry(campo_frame, width=W_ENTRY)
                
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
            
            e.grid(row=row, column=col + 1, sticky="ew", padx=10, pady=(0, 5))
            self.campos[key] = e

        # Dias de Garantia
        dias_row = len(campos_info) // 2
        l_dias = ctk.CTkLabel(campo_frame, text="Dias de Garantia*", anchor="w")
        l_dias.grid(row=dias_row, column=2, sticky="w", padx=10, pady=(5, 0))
        self.campos["dias_garantia_label"] = l_dias
        
        e_dias = ctk.CTkComboBox(campo_frame, 
                                 width=W_ENTRY, 
                                 state="readonly", 
                                 values=["30 Dias", "90 Dias"], 
                                 variable=self.dias_garantia_var)
        e_dias.set("90 Dias")
        e_dias.grid(row=dias_row, column=3, sticky="ew", padx=10, pady=(0, 5))
        self.campos["dias_garantia"] = e_dias
        on_tipo_garantia_change(None) 

        # --- SEÇÃO CHECKLIST & DETALHE ---
        
        problemas_row_start = len(campos_info) // 2
        
        self.checklist_frame = ctk.CTkFrame(campo_frame, fg_color="transparent") 
        # A grid para o checklist_frame será definida por alternar_tipo_documento
        ctk.CTkLabel(self.checklist_frame, text="CHECKLIST (PROBLEMAS/STATUS)", font=('Arial', 10, 'bold')).pack(anchor="w")
        
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
                                  border_color=COR_VERDE_PRINCIPAL) # Mantém a cor da borda verde
            chk.grid(row=i%7, column=col, sticky="w", padx=10)
            self.checklist_vars[item] = var

        # --- CAMPO DETALHE ADICIONAL (PROBLEMAS/OUTROS) ---
        
        l_detalhe = ctk.CTkLabel(campo_frame, text="Detalhe Adicional (Opcional):")
        self.campos["problemas_detalhe_label"] = l_detalhe
        # O posicionamento inicial (grid) será definido por alternar_tipo_documento
        
        # Substitui RoundedEntry por CTkEntry
        e_detalhe = ctk.CTkEntry(campo_frame, width=W_ENTRY * 2 + 30)
        # O posicionamento inicial (grid) será definido por alternar_tipo_documento
        self.campos["problemas_detalhe"] = e_detalhe
        
        # --- FIM SEÇÃO CHECKLIST ---

        fb = ctk.CTkFrame(center_frame, fg_color="transparent")
        fb.pack(pady=10)
        
        # Substitui RoundedButton por CTkButton (automaticamente usa a cor de destaque verde)
        
        b_salvar = ctk.CTkButton(fb, text="Salvar Documento", width=180, command=self.salvar, 
                                 fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_salvar.grid(row=0, column=0, padx=6)
        self.botoes_preenchimento.append(b_salvar)
        
        b_limpar = ctk.CTkButton(fb, text="Limpar", width=180, command=self.limpar, 
                                 fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_limpar.grid(row=0, column=1, padx=6)
        self.botoes_preenchimento.append(b_limpar)
        
        b_lista = ctk.CTkButton(fb, text="Lista de Docs", width=180, command=lambda: self.show_frame("Lista"), 
                                fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_lista.grid(row=0, column=2, padx=6)
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
        top_frame.pack(side="top", fill="x", padx=10, pady=10)
        
        # Título (CTkLabel)
        ctk.CTkLabel(top_frame, text="Documentos Registrados", font=('Arial', 16, 'bold')).pack(side=tk.LEFT)
        
        self.botoes_lista = []
        
        # Botões CTk (VERDE)
        b_novo_doc = ctk.CTkButton(top_frame, text="Novo Documento", width=150, command=lambda: self.show_frame("Preenchimento"), 
                                   fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_novo_doc.pack(side=tk.RIGHT, padx=5)
        self.botoes_lista.append(b_novo_doc)
                     
        b_atualizar_lista = ctk.CTkButton(top_frame, text="Atualizar Lista", width=120, command=self.carregar_dados_lista, 
                                          fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_atualizar_lista.pack(side=tk.RIGHT, padx=5)
        self.botoes_lista.append(b_atualizar_lista)

        # Frame de Busca (CTkFrame)
        search_frame = ctk.CTkFrame(f, fg_color="transparent")
        search_frame.pack(side="top", fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(search_frame, text="Buscar:").pack(side=tk.LEFT, padx=5)
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda name, index, mode: self.carregar_dados_lista(search=self.search_var.get()))
        
        # Entrada de busca (CTkEntry)
        self.search_entry = ctk.CTkEntry(search_frame, width=200, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=5)
        
        # Tabela (ttk.Treeview - mantida)
        tree_frame = ctk.CTkFrame(f, fg_color="transparent")
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

        # Scrollbar (ttk.Scrollbar - mantida)
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tabela.pack(fill="both", expand=True)
        
        # Frame de Ações (CTkFrame)
        action_frame = ctk.CTkFrame(f, fg_color="transparent")
        action_frame.pack(side="bottom", fill="x", padx=10, pady=5)
        
        # Botões de Ação (AGORA TODOS SÃO VERDES)
        b_ver_pdf = ctk.CTkButton(action_frame, text="Ver PDF", width=150, command=self.abrir_pdf, 
                                  fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_ver_pdf.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_ver_pdf)
        
        b_deletar = ctk.CTkButton(action_frame, text="Deletar", width=150, command=self.deletar, 
                                  fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE) 
        b_deletar.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_deletar)

        # --------------------------------------------------------------------------------------------------
        # NOVO: FRAME DE ATUALIZAÇÃO DE STATUS
        # --------------------------------------------------------------------------------------------------
        status_update_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        status_update_frame.pack(side=tk.LEFT, padx=5)
        
        ctk.CTkLabel(status_update_frame, text="Novo Status:").pack(side=tk.LEFT, padx=5)
        
        # Variável para o novo status
        self.novo_status_var = tk.StringVar(value="EM ANDAMENTO")
        
        # ComboBox de Novo Status (CTkComboBox)
        self.combo_novo_status = ctk.CTkComboBox(status_update_frame, 
                                                 width=150, 
                                                 values=["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA", "CANCELADA"],
                                                 variable=self.novo_status_var,
                                                 state="readonly")
        self.combo_novo_status.pack(side=tk.LEFT, padx=5)
        
        # Botão Atualizar Status (VERDE)
        b_atualizar_status = ctk.CTkButton(status_update_frame, 
                                           text="Atualizar Status", 
                                           width=150, 
                                           command=self.atualizar_status_documento, 
                                           fg_color=COR_VERDE_PRINCIPAL, 
                                           hover_color=COR_HOVER_VERDE)
        b_atualizar_status.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_atualizar_status)
        # --------------------------------------------------------------------------------------------------

        # Frame de Atualização de Valor (CTkFrame)
        update_frame = ctk.CTkFrame(action_frame, fg_color="transparent")
        update_frame.pack(side=tk.RIGHT, padx=5)
        
        ctk.CTkLabel(update_frame, text="Novo Valor (R$):").pack(side=tk.LEFT, padx=5)
        # Entrada de Novo Valor (CTkEntry)
        self.entry_novo_valor = ctk.CTkEntry(update_frame, width=150)
        self.entry_novo_valor.pack(side=tk.LEFT, padx=5)
        
        # Botão Atualizar Valor/Regerar PDF (VERDE)
        b_atualizar_valor = ctk.CTkButton(update_frame, text="Atualizar Valor/Regerar PDF", width=180, command=self.atualizar_valor_os, 
                                          fg_color=COR_VERDE_PRINCIPAL, hover_color=COR_HOVER_VERDE)
        b_atualizar_valor.pack(side=tk.LEFT, padx=5)
        self.botoes_lista.append(b_atualizar_valor)
        
        self.carregar_dados_lista()


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
            "tipo_documento": tipo_documento
        }
        
        # 4. Geração do PDF
        caminho_pdf = gerar_documento(dados_db, valor_texto, total_float, tipo_garantia, metodo_pagamento, checklist_str, tipo_documento, dias_garantia_num)
        
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

    def carregar_dados_lista(self, search=""):
        """Carrega os dados do banco para a Treeview, aplicando filtro de busca."""
        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        for item in self.tabela.get_children():
            self.tabela.delete(item)

        query = "SELECT * FROM os"
        params = []
        
        if search:
            search_pattern = f"%{search}%"
            query += " WHERE numero LIKE ? OR cliente LIKE ? OR modelo LIKE ? OR imei LIKE ? OR problemas LIKE ?"
            params = [search_pattern] * 5 

        query += " ORDER BY id DESC"
        
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

        except sqlite3.Error as e:
            messagebox.showerror("Erro de Leitura", f"Erro ao carregar dados do banco: {str(e)}")
            
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
                self.carregar_dados_lista(search=self.search_var.get())

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
            dados_db["dias_garantia"]
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
            dados_db["dias_garantia"]
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