# SISTEMA DE OS DIPCELL (COM CHECKLIST, ATUALIZAÇÃO, VALOR E FUNÇÃO VENDAS)

import os
import sys 
import sqlite3
from datetime import datetime, timedelta
from tkinter import *
from tkinter import ttk, messagebox

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
# FUNÇÕES AUXILIARES PARA COMPATIBILIDADE E ROBUSTEZ
# ==========================================================

def resource_path(relative_path):
    """Obtém o caminho absoluto para o recurso, funciona para desenvolvimento e para PyInstaller."""
    try:
        # Caminho temporário criado pelo PyInstaller
        base_path = sys._MEIPASS
    except Exception:
        # Caminho padrão quando rodando como script
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def get_app_directory():
    """Retorna o diretório onde o executável está rodando (ou o diretório do script)."""
    if getattr(sys, 'frozen', False):
        # Executável compilado (PyInstaller)
        return os.path.dirname(sys.executable)
    else:
        # Script Python normal
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
        # Fallback: tenta abrir com o comando padrão do sistema
        try:
            import subprocess
            subprocess.Popen([caminho], shell=True)
        except Exception as e2:
            # Se messagebox não estiver disponível, apenas imprime o erro
            try:
                from tkinter import messagebox
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
# BANCO DE DADOS + MIGRAÇÃO (INCLUI CAMPO CHECKLIST + DIAS_GARANTIA + TIPO_DOCUMENTO)
# ==========================================================

def criar_banco():
    """Cria o banco de dados com tratamento robusto de erros."""
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
                    # Define um valor padrão razoável para a migração
                    if col == "dias_garantia":
                        default_val = "90"
                    elif col == "tipo_documento":
                        default_val = "'OS'"
                    else:
                        default_val = "'Com Garantia'"
                        
                    c.execute(f"ALTER TABLE os ADD COLUMN {col} {tipo} DEFAULT {default_val}")
                    conn.commit()
                except sqlite3.Error as e:
                    # Log do erro mas continua (coluna pode já existir)
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
# FUNÇÕES AUXILIARES
# ==========================================================

def parse_monetario_to_float(txt):
    if not txt:
        return 0.0
    # Adiciona tratamento para a vírgula como separador decimal
    txt = txt.replace(",", ".")
    return float(txt.replace(".", "", txt.count(".") - 1) or 0) # Trata . como separador de milhar

def formatar_monetario(v):
    # Formata para moeda brasileira R$ 1.000,00
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
# GERAR PDF (INCLUI CHECKLIST E TIPO DOCUMENTO)
# ==========================================================

def gerar_documento(dados, valor_texto, total_float, tipo_garantia, metodo_pagamento, checklist_str, tipo_documento, dias_garantia_num):
    """Gera o documento PDF com tratamento robusto de erros."""
    try:
        # Cria a pasta se não existir, com tratamento de erro
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

    # NOVO: Nome do arquivo dinâmico
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

    # NOVO: Título dinâmico
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

    # Função de bloco padrão
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

    # Função para o bloco da Checklist (SÓ PARA OS)
    def bloco_checklist(titulo, checklist_str):
        story.append(Paragraph(
            f"<b>{titulo}</b>",
            ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14)
        ))
        
        rows = []
        # Converte a string "Item:Sim;Item2:Não" para uma lista de tuplas
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


    # Dados
    bloco("Dados do Cliente", [
        (f"Número {tipo_documento}", dados["numero"]), 
        ("Cliente", dados["cliente"]),
        ("Telefone", dados["telefone"]),
        ("Data", dados["entrada"])
    ])

    # NOVO: Bloco de Aparelho/Produto condicional
    if tipo_documento == "OS":
        bloco("Aparelho", [
            ("Modelo", dados["modelo"]),
            ("IMEI", dados["imei"]),
            ("Acessórios", dados["acessorios"]),
            ("Senha/Padrão", dados["senha"])
        ])
        
        # Chamada para o bloco da Checklist
        bloco_checklist("Lista de Checagem do Aparelho", checklist_str)
        
        problema_titulo = "Problemas / Detalhe"
    
    else: # VENDA
        # No caso de venda, o "modelo" é o nome do produto e "problemas" é a descrição
        bloco("Produto Vendido", [
            ("Produto", dados["modelo"]), # Aqui é o nome do produto
            ("Detalhes", dados["acessorios"]) # Aqui é a descrição/detalhes da venda
        ])
        
        problema_titulo = "Detalhe (Venda)"


    # Bloco de serviço ou venda
    bloco(titulo_doc, [ 
        (problema_titulo, dados["problemas"] if tipo_documento == "OS" else "Ver Produto Vendido"), 
        ("Situação" if tipo_documento == "OS" else "Status", dados["situacao"]),
        ("Valor (R$)", valor_texto),
        ("Total (R$)", formatar_monetario(total_float)),
        ("Método Pgto.", metodo_pagamento), 
        ("Saída", dados["saida"]),
        ("Garantia até", dados["garantia"]),
        ("Tipo de Garantia", tipo_garantia) 
    ])

    # ---------------------------------------------------------
    # TERMO DE GARANTIA (LÓGICA CORRIGIDA E REVISADA)
    # ---------------------------------------------------------
    
    AVISO_PAGAMENTO = "NÃO SERÁ ENTREGUE O APARELHO/PRODUTO SEM ANTES ACERTAR O PAGAMENTO. "
    dias_garantia_texto = f"{dias_garantia_num} dias" if dias_garantia_num > 0 else "legal"
    termo_texto = ""
    
    if tipo_documento == "OS":
        # TERMOS PARA ORDEM DE SERVIÇO (mantidos como anteriormente)
        if tipo_garantia == "Com Garantia":
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO}</b> A garantia cobre exclusivamente o **serviço** realizado pelo período de **{dias_garantia_texto}** informado nesta OS. "
                "Não cobre danos causados por mau uso, queda, oxidação, danos líquidos, tela quebrada ou violação do lacre. "
                "O aparelho deve ser retirado em até 90 dias após a conclusão do serviço.</font>"
            )
        else: # Sem Garantia
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO} SERVIÇO NÃO COBERTO POR GARANTIA!</b> O cliente está ciente de que o serviço realizado "
                "não possui cobertura de garantia devido à natureza do reparo/peça ou condição do aparelho. "
                "O aparelho deve ser retirado em até 90 dias após a conclusão do serviço.</font>"
            )
            
    else: # VENDA
        # TERMOS PARA VENDA DE PRODUTO (conforme sua solicitação)
        if tipo_garantia == "Com Garantia":
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO}</b> A garantia de **{dias_garantia_texto}** cobre somente se o produto apresentar "
                "problemas de fábrica e estiver com a caixa do mesmo. "
                "A garantia **NÃO COBRE** danos por mau uso, queda, oxidação, danos líquidos ou remoção de selos de garantia.</font>"
            )
        else: # Sem Garantia
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO} PRODUTO VENDIDO SEM GARANTIA!</b> O cliente está ciente de que este produto "
                "não possui cobertura de garantia.</font>"
            )


    termo = Paragraph(termo_texto, normal)

    story.append(Spacer(1, 3)) 
    story.append(termo)
    story.append(Spacer(1, 3)) 

    # ---------------------------------------------------------
    # Assinaturas
    # ---------------------------------------------------------

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


    # Borda + marca d’água
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
# INTERFACE TKINTER - LÓGICA DINÂMICA E CORREÇÃO DO KEYERROR
# ==========================================================

class SistemaOS:

    def __init__(self, master):
        master.title("DIPCELL - Sistema de OS/Vendas")
        master.configure(bg="#1e1e1e")
        
        # ... (Configuração de tema e estilos omitida para brevidade, mas deve ser mantida) ...
        style = ttk.Style()
        style.theme_use('clam') 
        COR_VERDE_ESCURO = '#2E8B57' 
        COR_VERDE_ATIVO = '#226C41'
        style.configure('Custom.TButton', font=('Arial', 10, 'bold'), background=COR_VERDE_ESCURO, foreground='white', borderwidth=0, relief='flat', padding=10) 
        style.map('Custom.TButton', background=[('active', COR_VERDE_ATIVO), ('pressed', COR_VERDE_ATIVO)], foreground=[('active', 'white'), ('pressed', 'white')])
        style.configure('TFrame', background='#1e1e1e')
        style.configure('TLabel', background='#1e1e1e', foreground='white')
        style.configure("Treeview", background="#2c2c2c", foreground="white", fieldbackground="#2c2c2c", rowheight=25, font=('Arial', 10))
        style.map('Treeview', background=[('selected', COR_VERDE_ATIVO)]) 
        style.configure("Treeview.Heading", font=('Arial', 11, 'bold'), background="#3c3c3c", foreground="white")
        style.configure("TCheckbutton", background="#1e1e1e", foreground='white', indicatorcolor='white', font=('Arial', 10))
        style.map("TCheckbutton", background=[('active', '#1e1e1e')], foreground=[('active', 'white')])
        # ----------------------------------------------------

        self.container = Frame(master, bg="#1e1e1e")
        self.container.grid(row=0, column=0, sticky="nsew") 

        master.grid_rowconfigure(0, weight=1)
        master.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        
        # Inicializa variáveis de controle
        self.tipo_documento_var = StringVar(value="OS") 
        self.dias_garantia_var = StringVar(value="90 Dias") # VARIÁVEL REINTEGRADA
        
        self.criar_tela_preenchimento(self.container)
        self.criar_tela_lista(self.container)

        self.show_frame("Preenchimento")
        self.gerar_numero_documento() 
        
    # Funções de numeração separadas
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
        f = Frame(parent, bg="#1e1e1e")
        self.frames["Preenchimento"] = f
        f.grid(row=0, column=0, sticky="nsew")

        center_frame = Frame(f, bg="#1e1e1e")
        center_frame.place(relx=0.5, rely=0.5, anchor=CENTER) 
        
        self.vint = f.register(lambda v: v.isdigit() or v == "")
        self.vmoney = f.register(lambda v: all(ch in "0123456789,." for ch in v) and v.count(',') <= 1) 
        self.campos = {}
        self.tel_var = StringVar() 

        def aplicar_e_mostrar_mascara(event):
            raw_text = self.tel_var.get()
            nums_only = "".join(ch for ch in raw_text if ch.isdigit())
            if len(nums_only) >= 10: 
                masked_text = aplicar_mascara_tel(raw_text)
                self.tel_var.set(masked_text)
            else:
                self.tel_var.set(nums_only) 
        
        # NOVO: Função para controlar o Combobox Dias de Garantia (REINTEGRADA)
        def on_tipo_garantia_change(event):
            """Habilita/Desabilita o seletor de dias de garantia."""
            if self.campos["tipo_garantia"].get() == "Com Garantia":
                self.campos["dias_garantia"].config(state="readonly")
                if not self.dias_garantia_var.get():
                     self.dias_garantia_var.set("90 Dias") # Default
            else:
                self.campos["dias_garantia"].config(state="disabled")
                self.dias_garantia_var.set("")
        # -----------------------------------------------------------
        
        # NOVO: Função para alternar entre OS e VENDA
        def alternar_tipo_documento(event=None):
            self.limpar()
            self.gerar_numero_documento()
            tipo = self.tipo_documento_var.get()
            
            is_os = (tipo == "OS")
            
            # 1. Ajustar os rótulos dinâmicos
            self.campos["modelo_label"].config(text="Modelo*" if is_os else "Produto*")
            self.campos["acessorios_label"].config(text="Acessórios" if is_os else "Detalhes da Venda")
            
            # Resetamos a situação para o padrão da OS/Venda
            if is_os:
                self.campos["situacao"].current(0) # EM ABERTO
            else:
                self.campos["situacao"].current(2) # CONCLUÍDA

            # 2. Widgets de OS (2 Colunas: IMEI, Senha, Acessórios)
            os_fields_2col = ["imei", "senha", "acessorios"]
            
            # Informações dos campos para reposicionamento
            campos_info = [
                ("Cliente*", "cliente"), ("Modelo*", "modelo"),
                ("Telefone*", "telefone"), ("IMEI", "imei"),
                ("Senha/Padrão", "senha"), ("Acessórios", "acessorios"),
                ("Tipo de Garantia*", "tipo_garantia"), ("Método de Pagamento*", "metodo_pagamento"),
                ("Valor (R$)*", "valor"), ("Situacao*", "situacao")
            ]
            
            # Reposiciona ou esconde os campos de IMEI e Senha (visíveis apenas na OS)
            for key in os_fields_2col:
                
                label_widget = self.campos[f"{key}_label"]
                entry_widget = self.campos[key]
                
                if key == "acessorios":
                    continue # Acessórios apenas muda o rótulo
                    
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

            # 3. Widgets de OS (Largura Total: Checklist e Detalhe Adicional)
            problemas_row_start = len(campos_info) // 2 # Linha onde o campo dias_garantia está
            problemas_row_end = problemas_row_start + 1 + 7 # Linha onde o detalhe adicional começa
                    
            if is_os:
                self.checklist_frame.grid(row=problemas_row_start + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(15, 5))
                self.campos["problemas_detalhe_label"].grid(row=problemas_row_end + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 0))
                self.campos["problemas_detalhe"].grid(row=problemas_row_end + 2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
            else:
                self.checklist_frame.grid_forget()
                self.campos["problemas_detalhe_label"].grid_forget()
                self.campos["problemas_detalhe"].grid_forget()


        # Logo
        if os.path.exists(LOGO_PADRAO):
            l = ImageTk.PhotoImage(PILImage.open(LOGO_PADRAO).resize((120, 120))) 
            Label(center_frame, image=l, bg="#1e1e1e").pack(pady=(0, 10)) 
            self.logo = l
            
        # NOVO: Seleção OS/VENDA
        tipo_doc_frame = Frame(center_frame, bg="#1e1e1e")
        tipo_doc_frame.pack(pady=5)
        Label(tipo_doc_frame, text="Tipo de Documento:", fg="white", bg="#1e1e1e").pack(side=LEFT, padx=5)
        
        cb_tipo_doc = ttk.Combobox(tipo_doc_frame, width=20, state="readonly",
                                 values=["OS", "VENDA"], textvariable=self.tipo_documento_var)
        cb_tipo_doc.current(0)
        cb_tipo_doc.bind("<<ComboboxSelected>>", alternar_tipo_documento)
        cb_tipo_doc.pack(side=LEFT)
        
        
        # Frame dos campos (Organização em GRIDS/2 COLUNAS)
        campo_frame = Frame(center_frame, bg="#1e1e1e") 
        campo_frame.pack(pady=10, padx=20) 

        campos_info = [
            ("Cliente*", "cliente"), ("Modelo*", "modelo"),
            ("Telefone*", "telefone"), ("IMEI", "imei"),
            ("Senha/Padrão", "senha"), ("Acessórios", "acessorios"),
            ("Tipo de Garantia*", "tipo_garantia"), ("Método de Pagamento*", "metodo_pagamento"),
            ("Valor (R$)*", "valor"), ("Situacao*", "situacao")
        ]

        W_ENTRY = 28 
        W_COMBO = 28 

        for i, (label, key) in enumerate(campos_info):
            row = i // 2
            col = (i % 2) * 2
            
            # Label
            l = Label(campo_frame, text=label, fg="white", bg="#1e1e1e", anchor="w", name=f"{key}_label")
            l.grid(row=row, column=col, sticky="w", padx=10, pady=(5, 0))
            self.campos[f"{key}_label"] = l 

            # Entrada
            if key == "telefone":
                e = Entry(campo_frame, width=W_ENTRY, validate="key", validatecommand=(self.vint, "%P"), textvariable=self.tel_var, name=key)
                e.bind("<FocusOut>", aplicar_e_mostrar_mascara) 
            elif key in ("imei",):
                e = Entry(campo_frame, width=W_ENTRY, validate="key", validatecommand=(self.vint, "%P"), name=key)
            elif key == "valor":
                e = Entry(campo_frame, width=W_ENTRY, validate="key", validatecommand=(self.vmoney, "%P"), name=key)
            elif key == "situacao":
                e = ttk.Combobox(campo_frame, width=W_COMBO-2, state="readonly", name=key,
                                 values=["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA"])
                e.current(0)
            elif key == "tipo_garantia":
                e = ttk.Combobox(campo_frame, width=W_COMBO-2, state="readonly", name=key,
                                 values=["Com Garantia", "Sem Garantia"])
                e.current(0)
                e.bind("<<ComboboxSelected>>", on_tipo_garantia_change) # Bind REINTEGRADO
            elif key == "metodo_pagamento":
                e = ttk.Combobox(campo_frame, width=W_COMBO-2, state="readonly", name=key,
                                 values=["CARTÃO", "DINHEIRO", "PIX"])
                e.current(0) 
            else:
                e = Entry(campo_frame, width=W_ENTRY, name=key)

            e.grid(row=row, column=col + 1, sticky="ew", padx=10, pady=(0, 5))
            self.campos[key] = e
            
        # NOVO CAMPO: Dias de Garantia (REINTEGRADO)
        # Deve ficar logo abaixo de Situação
        dias_row = len(campos_info) // 2 
        
        l_dias = Label(campo_frame, text="Dias de Garantia*", fg="white", bg="#1e1e1e", anchor="w", name="dias_garantia_label")
        l_dias.grid(row=dias_row, column=2, sticky="w", padx=10, pady=(5, 0)) # Coluna 2 (lado direito)
        self.campos["dias_garantia_label"] = l_dias # Salva o Label
        
        e_dias = ttk.Combobox(campo_frame, width=W_COMBO-2, state="readonly", name="dias_garantia",
                              values=["30 Dias", "90 Dias"], textvariable=self.dias_garantia_var)
        e_dias.current(1) # Default 90
        e_dias.grid(row=dias_row, column=3, sticky="ew", padx=10, pady=(0, 5)) # Coluna 3
        self.campos["dias_garantia"] = e_dias
        on_tipo_garantia_change(None) # Define o estado inicial

        # ---------------------------------------------------------
        # --- SEÇÃO CHECKLIST & DETALHE ---
        # ---------------------------------------------------------
        
        problemas_row_start = len(campos_info) // 2 
        
        self.checklist_frame = Frame(campo_frame, bg="#1e1e1e")
        # Colocado na linha debaixo para não conflitar com Dias de Garantia
        self.checklist_frame.grid(row=problemas_row_start + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(15, 5)) 
        
        Label(self.checklist_frame, text="CHECKLIST (PROBLEMAS/STATUS)", fg="white", bg="#1e1e1e", font=('Arial', 10, 'bold')).pack(anchor="w")

        self.checklist_vars = {}
        checklist_itens = [
            "Tela Display", "Touch Screen", "Teclas", "Sensores de Proximidade",
            "Bluetooth", "Wi-Fi", "Ligações", "Alto Falante",
            "Câmera", "Microfone", "Conector Carregador", "Conector Cartão de Memória",
            "Sim Card", "Outros (Opcional - p/ defeitos internos)"
        ]
        
        # Frame interno para a checklist (organização em duas colunas)
        chk_inner_frame = Frame(self.checklist_frame, bg="#1e1e1e")
        chk_inner_frame.pack(fill="x")
        
        for i, item in enumerate(checklist_itens):
            col = i // 7 
            
            var = StringVar(value="Não")
            
            chk = ttk.Checkbutton(chk_inner_frame, text=item, variable=var, 
                              onvalue="Sim", offvalue="Não", style="TCheckbutton")
                              
            chk.grid(row=i%7, column=col, sticky="w", padx=10)
            self.checklist_vars[item] = var
        
        # --- CAMPO DETALHE ADICIONAL (PROBLEMAS/OUTROS) ---
        
        problemas_row_end = problemas_row_start + 1 + 7 
        
        l_detalhe = Label(campo_frame, text="Detalhe Adicional (Opcional):", fg="white", bg="#1e1e1e", name="problemas_detalhe_label")
        # CORREÇÃO CRÍTICA DO KEYERROR: Adicionar o rótulo ao dicionário
        self.campos["problemas_detalhe_label"] = l_detalhe 
        l_detalhe.grid(row=problemas_row_end + 1, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 0))

        e_detalhe = Entry(campo_frame, width=W_ENTRY * 2 + 10, name="problemas_detalhe") 
        e_detalhe.grid(row=problemas_row_end + 2, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))
        self.campos["problemas_detalhe"] = e_detalhe
        
        # --- FIM SEÇÃO CHECKLIST ---

        fb = Frame(center_frame, bg="#1e1e1e")
        fb.pack(pady=10)

        # Botões com estilo verde Custom.TButton
        ttk.Button(fb, text="Salvar Documento", width=20, command=self.salvar, style='Custom.TButton').grid(row=0, column=0, padx=6)
        ttk.Button(fb, text="Limpar", width=20, command=self.limpar, style='Custom.TButton').grid(row=0, column=1, padx=6)
        ttk.Button(fb, text="Lista de Docs", width=20, command=lambda: self.show_frame("Lista"), style='Custom.TButton').grid(row=0, column=2, padx=6)
        
        # Garante que a tela inicia com os campos de OS visíveis (chamando a função)
        alternar_tipo_documento() 


    def criar_tela_lista(self, parent):
        win = Frame(parent, bg="#1e1e1e")
        self.frames["Lista"] = win
        win.grid(row=0, column=0, sticky="nsew")

        win.grid_rowconfigure(3, weight=1) 
        win.grid_columnconfigure(0, weight=1)

        # Botão Voltar
        ttk.Button(win, text="<< Voltar ao Cadastro", command=lambda: self.show_frame("Preenchimento")).grid(row=0, column=0, sticky="w", padx=20, pady=10)
        
        Label(win, text="LISTA DE DOCUMENTOS (OS/VENDAS)", fg="white", bg="#1e1e1e", font=("Arial", 16, "bold")).grid(row=1, column=0, pady=10)

        # Frame de Busca
        busca_frame = Frame(win, bg="#1e1e1e")
        busca_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10))
        busca_frame.grid_columnconfigure(1, weight=1)
        
        Label(busca_frame, text="Buscar por Número:", fg="white", bg="#1e1e1e", font=('Arial', 10)).grid(row=0, column=0, padx=(0, 10), sticky="w")
        
        self.entry_busca = Entry(busca_frame, width=30, font=('Arial', 10))
        self.entry_busca.grid(row=0, column=1, padx=5, sticky="ew")
        self.entry_busca.bind("<KeyRelease>", self.filtrar_por_numero)
        
        ttk.Button(busca_frame, text="Limpar", command=self.limpar_filtro, style='Custom.TButton', width=12).grid(row=0, column=2, padx=5)

        cols = ("Tipo","Numero","Cliente","Modelo/Produto","Entrada","Saida","Garantia","Situacao","Arquivo")

        tabela_frame = Frame(win)
        tabela_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)

        tabela_frame.grid_rowconfigure(0, weight=1)
        tabela_frame.grid_columnconfigure(0, weight=1)

        vsb = ttk.Scrollbar(tabela_frame, orient="vertical")
        hsb = ttk.Scrollbar(tabela_frame, orient="horizontal")

        self.tabela = ttk.Treeview(tabela_frame, columns=cols, show="headings", height=20, 
                                   yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        
        vsb.config(command=self.tabela.yview)
        hsb.config(command=self.tabela.xview)
        
        vsb.pack(side="right", fill="y")
        self.tabela.pack(side="left", fill="both", expand=True)
        hsb.pack(side="bottom", fill="x")

        for c in cols:
            self.tabela.heading(c, text=c)

        control_frame = Frame(win, bg="#1e1e1e")
        control_frame.grid(row=4, column=0, pady=10)
        
        # LINHA 0: ATUALIZAÇÃO DE SITUAÇÃO
        Label(control_frame, text="Alterar Situação:", fg="white", bg="#1e1e1e").grid(row=0, column=0, padx=10, pady=5)
        self.cb_situacao = ttk.Combobox(control_frame, values=["EM ABERTO", "EM ANDAMENTO", "CONCLUÍDA"],
                          state="readonly", width=30)
        self.cb_situacao.grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(control_frame, text="Atualizar Situação", command=self.atualizar_situacao, style='Custom.TButton').grid(row=0, column=2, padx=10, pady=5)
        
        # LINHA 1: ATUALIZAÇÃO DE PAGAMENTO
        Label(control_frame, text="Alterar Pagamento:", fg="white", bg="#1e1e1e").grid(row=1, column=0, padx=10, pady=5)
        self.cb_pagamento = ttk.Combobox(control_frame, values=["CARTÃO", "DINHEIRO", "PIX"],
                          state="readonly", width=30)
        self.cb_pagamento.grid(row=1, column=1, padx=10, pady=5)
        self.cb_pagamento.current(0)
        ttk.Button(control_frame, text="Atualizar Pagamento", command=self.atualizar_pagamento, style='Custom.TButton').grid(row=1, column=2, padx=10, pady=5)

        # LINHA 2: ATUALIZAÇÃO DE VALOR
        Label(control_frame, text="Novo Valor (R$):", fg="white", bg="#1e1e1e").grid(row=2, column=0, padx=10, pady=5)
        
        vcmd_money = win.register(lambda v: all(ch in "0123456789,." for ch in v) and v.count(',') <= 1) 
        self.entry_novo_valor = Entry(control_frame, width=33, validate="key", validatecommand=(vcmd_money, "%P")) 
        self.entry_novo_valor.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        ttk.Button(control_frame, text="Atualizar Valor", command=self.atualizar_valor, style='Custom.TButton').grid(row=2, column=2, padx=10, pady=5)

        # Botão Abrir OS (PDF) - MAIOR
        ttk.Button(control_frame, text="Abrir Documento (PDF)", command=self.abrir_pdf, style='Custom.TButton', width=20).grid(
            row=0, column=3, padx=10, rowspan=3, sticky="nsew"
        )

    def carregar_dados_lista(self, filtro_numero=None):
        self.tabela.delete(*self.tabela.get_children()) 

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        
        if filtro_numero and filtro_numero.strip():
            # Busca por número (case-insensitive e parcial)
            c.execute("""
                SELECT tipo_documento, numero, cliente, modelo, entrada, saida, garantia, situacao, arquivo 
                FROM os 
                WHERE numero LIKE ? 
                ORDER BY id DESC
            """, (f"%{filtro_numero.strip()}%",))
        else:
            c.execute("SELECT tipo_documento, numero, cliente, modelo, entrada, saida, garantia, situacao, arquivo FROM os ORDER BY id DESC") 
        
        for row in c.fetchall():
            self.tabela.insert("", END, values=row)
        conn.close()

    def filtrar_por_numero(self, event=None):
        """Filtra a tabela pelo número digitado"""
        texto_busca = self.entry_busca.get()
        self.carregar_dados_lista(filtro_numero=texto_busca)

    def limpar_filtro(self):
        """Limpa o campo de busca e recarrega todos os dados"""
        self.entry_busca.delete(0, END)
        self.carregar_dados_lista()


    def salvar(self):
        tipo_documento = self.tipo_documento_var.get()
        
        dados = {
            "numero": self.numero_documento, 
            "entrada": datetime.now().strftime("%d/%m/%Y"),
            "saida": "--",
            "garantia": "--",
            "tipo_documento": tipo_documento, 
            "dias_garantia": 0 # Inicializa
        }

        # 1. VALIDAÇÃO E EXTRAÇÃO DOS CAMPOS
        campos_obrigatorios = {
            "cliente": "Cliente", "telefone": "Telefone", "modelo": "Modelo/Produto", 
            "situacao": "Situação", "tipo_garantia": "Tipo de Garantia", 
            "metodo_pagamento": "Método de Pagamento", "valor": "Valor (R$)"
        }
        
        for key, nome in campos_obrigatorios.items():
            if key == "telefone":
                txt = self.tel_var.get().strip()
                nums_only = "".join(ch for ch in txt if ch.isdigit())
                if len(nums_only) < 10:
                     messagebox.showerror("Erro", "Campo 'Telefone' inválido ou incompleto (Mínimo 10 dígitos).")
                     return
                dados[key] = txt 
                continue

            txt = self.campos[key].get().strip()
            
            if txt == "":
                messagebox.showerror("Erro", f"Campo '{nome}' obrigatório.")
                return
            
            if key == "valor":
                try:
                    valor_float = parse_monetario_to_float(txt)
                    dados[key] = formatar_monetario(valor_float)
                except ValueError:
                    messagebox.showerror("Erro", "Formato de Valor inválido.")
                    return
            else:
                dados[key] = txt
                
        # TRATAMENTO DO CAMPO DIAS DE GARANTIA (REINTEGRADO)
        if dados["tipo_garantia"] == "Com Garantia":
             dias_garantia_txt = self.dias_garantia_var.get().strip()
             if not dias_garantia_txt or "Dias" not in dias_garantia_txt:
                 messagebox.showerror("Erro", "Selecione a quantidade de dias de garantia (30 ou 90).")
                 return
             dados["dias_garantia"] = int(dias_garantia_txt.split(' ')[0]) # Salva o número

        # 2. TRATAMENTO DOS CAMPOS ESPECÍFICOS (OS/VENDA)
        if tipo_documento == "OS":
            detalhe_problemas = self.campos["problemas_detalhe"].get().strip()
            dados["problemas"] = detalhe_problemas if detalhe_problemas else "Conforme Checklist"
            
            checklist_data = [f"{item}:{var.get()}" for item, var in self.checklist_vars.items()]
            dados["checklist"] = ";".join(checklist_data)
            
            dados["acessorios"] = self.campos["acessorios"].get().strip() or "N/A"
            dados["imei"] = self.campos["imei"].get().strip() or "N/A"
            dados["senha"] = self.campos["senha"].get().strip() or "N/A"

        else: # VENDA
            # VENDA: Problemas é o detalhe da venda, checklist/imei/senha são vazios.
            dados["imei"] = "N/A"
            dados["senha"] = "N/A"
            dados["problemas"] = "Venda de Produto" 
            dados["checklist"] = "" 
            
            # O campo 'acessorios' (da OS) é usado para 'Detalhes da Venda'
            dados["acessorios"] = self.campos["acessorios"].get().strip() or "Sem detalhes adicionais"
            
            # Situação de Venda deve ser CONCLUÍDA
            dados["situacao"] = "CONCLUÍDA"

        # 3. CÁLCULO DE SAÍDA E GARANTIA
        if dados["situacao"] == "CONCLUÍDA":
            dados["saida"] = datetime.now().strftime("%d/%m/%Y")
            
            if dados["tipo_garantia"] == "Com Garantia":
                dias = dados["dias_garantia"]
                dados["garantia"] = (datetime.now() + timedelta(days=dias)).strftime("%d/%m/%Y")
            else:
                # Sem Garantia: OS = --, VENDA = 30 dias (legal, se aplicável, mas aqui tratamos como "Sem Garantia")
                if tipo_documento == "OS":
                    dados["garantia"] = "--"
                else: 
                    # Para Vendas Sem Garantia, o termo informa que não há cobertura. Mantém "--" na data.
                    dados["garantia"] = "--" 
        # --------------------------------------------------------------------

        # 4. GERAÇÃO DO PDF E SALVAMENTO
        total = valor_float 

        pdf_path = gerar_documento(
            dados, dados["valor"], total, dados["tipo_garantia"], dados["metodo_pagamento"], dados["checklist"], tipo_documento, dados["dias_garantia"]
        )
        
        # Verifica se o PDF foi gerado com sucesso
        if not pdf_path:
            messagebox.showerror("Erro", "Não foi possível gerar o PDF. Operação cancelada.")
            return
        
        dados["arquivo"] = pdf_path

        try:
            conn = sqlite3.connect(DB_NAME)
            c = conn.cursor()

            # O comando SQL AGORA TEM 19 CAMPOS (incluindo dias_garantia e tipo_documento)
            c.execute("""
                INSERT INTO os (
                    numero, cliente, telefone, modelo, imei, senha, acessorios,
                    problemas, situacao, valor, entrada, saida, garantia, arquivo, 
                    tipo_garantia, metodo_pagamento, checklist, dias_garantia, tipo_documento
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados["numero"], dados["cliente"], dados["telefone"], dados["modelo"],
                dados["imei"], dados["senha"], dados["acessorios"], dados["problemas"], 
                dados["situacao"], dados["valor"], dados["entrada"],
                dados["saida"], dados["garantia"], dados["arquivo"], 
                dados["tipo_garantia"], dados["metodo_pagamento"], dados["checklist"],
                dados["dias_garantia"], dados["tipo_documento"]
            ))

            conn.commit()
            conn.close()

            messagebox.showinfo("OK", f"{tipo_documento} salva com sucesso!")
            self.limpar()
            self.gerar_numero_documento()
        except sqlite3.Error as e:
            messagebox.showerror("Erro ao Salvar", 
                f"Erro ao salvar no banco de dados:\n{str(e)}\n\n"
                f"O PDF foi gerado, mas os dados não foram salvos.")
        except Exception as e:
            messagebox.showerror("Erro Inesperado", 
                f"Erro inesperado ao salvar:\n{str(e)}") 

    def limpar(self):
        # 1. Salvar o valor atual do tipo de documento antes de limpar TUDO
        tipo_doc_salvo = self.tipo_documento_var.get()

        for key, e in self.campos.items():
            if hasattr(e, 'delete'):
                e.delete(0, END)
            if key in ("situacao", "tipo_garantia", "metodo_pagamento") and hasattr(e, 'current'):
                e.current(0)
            
        self.tel_var.set("")
        
        # 2. Restaurar o valor do tipo de documento
        self.tipo_documento_var.set(tipo_doc_salvo) 
        self.dias_garantia_var.set("90 Dias")
        
        # Aplicar o estado inicial da garantia
        if "tipo_garantia" in self.campos and "dias_garantia" in self.campos:
            self.campos["tipo_garantia"].current(0)
            self.campos["dias_garantia"].config(state="readonly")
        
        for var in self.checklist_vars.values():
            var.set("Não")


    def atualizar_situacao(self):
        item = self.tabela.focus()
        if not item:
            messagebox.showerror("Erro", "Selecione um Documento!")
            return

        nova = self.cb_situacao.get()
        if not nova:
            messagebox.showerror("Erro", "Selecione a nova situação!")
            return
            
        valores = self.tabela.item(item)["values"]
        tipo_documento = valores[0] 
        numero = valores[1] 

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # Seleciona todos os campos necessários para regenerar o PDF
        c.execute("""
            SELECT cliente, telefone, modelo, imei, senha, acessorios, problemas, valor, 
                   entrada, tipo_garantia, metodo_pagamento, checklist, dias_garantia
            FROM os WHERE numero=? AND tipo_documento=?
        """, (numero, tipo_documento))
        row = c.fetchone()
        
        # Garante que row existe
        if not row:
            conn.close()
            messagebox.showerror("Erro", "Documento não encontrado no banco de dados.")
            return

        tipo_garantia_db = row[9] 
        metodo_pagamento_db = row[10] 
        checklist_db = row[11] 
        dias_garantia_db = row[12] # Campo reintegrado

        if nova == "CONCLUÍDA":
            saida = datetime.now().strftime("%d/%m/%Y")
            
            if tipo_garantia_db == "Com Garantia":
                dias = dias_garantia_db
                garantia = (datetime.now() + timedelta(days=dias)).strftime("%d/%m/%Y")
            else:
                # Sem Garantia: OS = --, VENDA = --
                garantia = "--"
        else:
            saida = valores[5]
            garantia = valores[6]

        # 1. Atualiza a situação, saída e garantia no DB
        c.execute("UPDATE os SET situacao=?, saida=?, garantia=? WHERE numero=? AND tipo_documento=?",
                  (nova, saida, garantia, numero, tipo_documento))

        valor_texto = row[7]
        total = parse_monetario_to_float(valor_texto)

        dados = {
            "numero": numero, "cliente": row[0], "telefone": row[1], "modelo": row[2], 
            "imei": row[3], "senha": row[4], "acessorios": row[5], "problemas": row[6],
            "situacao": nova, "valor": row[7], "entrada": row[8], "saida": saida, 
            "garantia": garantia
        }

        # 2. Regenera o PDF
        novo_pdf = gerar_documento(dados, valor_texto, total, tipo_garantia_db, metodo_pagamento_db, checklist_db, tipo_documento, dias_garantia_db)
        
        # 3. Atualiza o caminho do PDF no DB
        c.execute("UPDATE os SET arquivo=? WHERE numero=? AND tipo_documento=?", (novo_pdf, numero, tipo_documento))

        conn.commit()
        conn.close()

        self.tabela.item(item, values=(
            tipo_documento, numero, valores[2], valores[3], valores[4],
            saida, garantia, nova, novo_pdf
        ))

        messagebox.showinfo("OK", f"Situação do {tipo_documento} atualizada e documento regenerado!")


    def atualizar_pagamento(self):
        """Função para atualizar apenas o método de pagamento e regenerar o PDF."""
        item = self.tabela.focus()
        if not item:
            messagebox.showerror("Erro", "Selecione um Documento!")
            return

        novo_pagamento = self.cb_pagamento.get()
        if not novo_pagamento:
            messagebox.showerror("Erro", "Selecione o novo método de pagamento!")
            return
            
        valores = self.tabela.item(item)["values"]
        tipo_documento = valores[0]
        numero = valores[1]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 1. Atualiza o Método de Pagamento no DB
        c.execute("UPDATE os SET metodo_pagamento=? WHERE numero=? AND tipo_documento=?", (novo_pagamento, numero, tipo_documento))
        
        # 2. Busca os dados completos 
        c.execute("""
            SELECT cliente, telefone, modelo, imei, senha, acessorios, problemas, 
                   valor, entrada, saida, garantia, situacao, tipo_garantia, checklist, dias_garantia
            FROM os WHERE numero=? AND tipo_documento=?
        """, (numero, tipo_documento))
        row = c.fetchone()
        
        dados = {
            "numero": numero, "cliente": row[0], "telefone": row[1], "modelo": row[2], 
            "imei": row[3], "senha": row[4], "acessorios": row[5], "problemas": row[6], 
            "valor": row[7], "entrada": row[8], "saida": row[9], "garantia": row[10], 
            "situacao": row[11],
        }
        
        valor_texto = dados["valor"]
        total = parse_monetario_to_float(valor_texto)

        # 3. Regenera o PDF
        tipo_garantia_db = row[12]
        checklist_db = row[13] 
        dias_garantia_db = row[14]
        
        novo_pdf = gerar_documento(dados, valor_texto, total, tipo_garantia_db, novo_pagamento, checklist_db, tipo_documento, dias_garantia_db) 

        # 4. Atualiza o caminho do PDF no DB
        c.execute("UPDATE os SET arquivo=? WHERE numero=? AND tipo_documento=?", (novo_pdf, numero, tipo_documento))

        conn.commit()
        conn.close()
        
        self.tabela.item(item, values=(
            tipo_documento, numero, dados["cliente"], dados["modelo"], dados["entrada"],
            dados["saida"], dados["garantia"], dados["situacao"], novo_pdf
        ))

        messagebox.showinfo("OK", f"Método de pagamento do {tipo_documento} atualizado e documento regenerado!")

    def atualizar_valor(self):
        """Função para atualizar o valor do serviço e regenerar o PDF."""
        item = self.tabela.focus()
        if not item:
            messagebox.showerror("Erro", "Selecione um Documento!")
            return

        novo_valor_raw = self.entry_novo_valor.get().strip()
        if not novo_valor_raw:
            messagebox.showerror("Erro", "Insira o novo valor!")
            return

        try:
            if novo_valor_raw.count(',') > 1:
                raise ValueError
                
            novo_valor_float = parse_monetario_to_float(novo_valor_raw)
            novo_valor_texto = formatar_monetario(novo_valor_float)
        except ValueError:
            messagebox.showerror("Erro", "Valor inválido. Use vírgula para centavos (ex: 150,50).")
            return

        valores = self.tabela.item(item)["values"]
        tipo_documento = valores[0]
        numero = valores[1]

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()

        # 1. Atualiza o Valor no DB
        c.execute("UPDATE os SET valor=? WHERE numero=? AND tipo_documento=?", (novo_valor_texto, numero, tipo_documento))
        
        # 2. Busca os dados completos para regenerar o PDF 
        c.execute("""
            SELECT cliente, telefone, modelo, imei, senha, acessorios, problemas, 
                   entrada, saida, garantia, situacao, tipo_garantia, metodo_pagamento, checklist, dias_garantia
            FROM os WHERE numero=? AND tipo_documento=?
        """, (numero, tipo_documento))
        row = c.fetchone()
        
        dados = {
            "numero": numero, "cliente": row[0], "telefone": row[1], "modelo": row[2], 
            "imei": row[3], "senha": row[4], "acessorios": row[5], "problemas": row[6], 
            "valor": novo_valor_texto, "entrada": row[7], "saida": row[8], 
            "garantia": row[9], "situacao": row[10],
        }
        
        total = novo_valor_float

        # 3. Regenera o PDF
        tipo_garantia_db = row[11]
        metodo_pagamento_db = row[12]
        checklist_db = row[13] 
        dias_garantia_db = row[14]
        
        novo_pdf = gerar_documento(dados, novo_valor_texto, total, tipo_garantia_db, metodo_pagamento_db, checklist_db, tipo_documento, dias_garantia_db) 

        # 4. Atualiza o caminho do PDF no DB
        c.execute("UPDATE os SET arquivo=? WHERE numero=? AND tipo_documento=?", (novo_pdf, numero, tipo_documento))

        conn.commit()
        conn.close()
        
        self.entry_novo_valor.delete(0, END)
        
        self.tabela.item(item, values=(
            tipo_documento, numero, dados["cliente"], dados["modelo"], dados["entrada"],
            dados["saida"], dados["garantia"], dados["situacao"], novo_pdf
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


# ==========================================================
# INICIAR SISTEMA
# ==========================================================

criar_banco()
root = Tk()
SistemaOS(root)
root.mainloop()