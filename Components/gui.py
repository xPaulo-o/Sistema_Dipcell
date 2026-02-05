import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
from datetime import datetime, timedelta
import json
import os
from PIL import Image as PILImage, ImageTk

from .config import (
    COR_FUNDO, COR_FRAME, COR_TEXTO, COR_VERDE_PRINCIPAL, COR_VERMELHO,
    COR_AZUL, COR_HOVER_VERDE, COR_BORDA, FONTE_TITULO, FONTE_NORMAL,
    FONTE_BOLD, LOGO_PADRAO, resource_path
)
from .utils import (
    parse_monetario_to_float, formatar_monetario, aplicar_mascara_tel, abrir_arquivo
)
from .database import (
    get_next_document_number, insert_document, list_documents,
    fetch_document, update_document, delete_document
)
from .pdf_generator import gerar_documento

class SistemaOS:

    def __init__(self, master):
        # Master agora é um ctk.CTk()
        master.title("DIPCELL - Sistema de OS/Vendas")
        master.geometry("1200x800") # Definir um tamanho inicial maior
        master.configure(fg_color=COR_FUNDO) # Aplicar cor de fundo principal
        
        # Configuração de Ícone (Compatível com PyInstaller)
        try:
            # Tenta carregar logo.ico para a janela/barra de tarefas
            icon_path = resource_path(os.path.join("public", "logo.ico"))
            if os.path.exists(icon_path):
                master.iconbitmap(icon_path)
            # Se não tiver ico, ou além disso, define o ícone da janela via imagem (Linux/Fallback)
            elif os.path.exists(LOGO_PADRAO):
                master.iconphoto(False, ImageTk.PhotoImage(PILImage.open(LOGO_PADRAO)))
        except Exception as e:
            print(f"Aviso: Não foi possível definir o ícone: {e}")
        
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
        
    def gerar_numero_documento(self):
        try:
            self.numero_documento = get_next_document_number(self.tipo_documento_var.get())
        except Exception as e:
            print(f"Erro ao gerar número: {e}")
            self.numero_documento = "ERRO"

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
                logo_img = ctk.CTkImage(light_image=PILImage.open(LOGO_PADRAO), size=(200, 200))
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
                logo_img_edit = ctk.CTkImage(light_image=PILImage.open(LOGO_PADRAO), size=(100, 100))
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
                insert_document(dados_db, caminho_pdf)
                
                messagebox.showinfo("Sucesso", f"{tipo_documento} {numero} salva com sucesso e PDF gerado:\n{caminho_pdf}")
                
                abrir_arquivo(caminho_pdf)
                
                self.limpar()

            except Exception as e:
                messagebox.showerror("Erro no DB", f"Erro ao salvar no banco de dados: {str(e)}")
        else:
            messagebox.showerror("Erro", f"Não foi possível salvar o documento.")

    def carregar_dados_lista(self, search="", page=1):
        """Carrega os dados do banco para a Treeview, aplicando filtro de busca e paginação."""
        
        for item in self.tabela.get_children():
            self.tabela.delete(item)

        # Calcular offset
        offset = (page - 1) * self.page_size
        
        try:
            rows, total = list_documents(search, self.page_size, offset)
            self.total_records = total

            for row in rows:
                tipo = row.get("tipo_documento", "")
                numero = row.get("numero", "")
                cliente = row.get("cliente", "")
                modelo = row.get("modelo", "")
                entrada = row.get("entrada", "")
                saida = row.get("saida") or "N/A" # Se for None, exibe N/A
                garantia = row.get("garantia", "")
                situacao = row.get("situacao", "")
                arquivo = row.get("arquivo", "")

                self.tabela.insert("", tk.END, values=(tipo, numero, cliente, modelo, entrada, saida, garantia, situacao, arquivo))

            # Atualizar controles de paginação
            self.atualizar_controle_paginacao()

        except Exception as e:
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
        
        dados = fetch_document(numero, tipo_documento)
        
        if not dados:
            messagebox.showerror("Erro", "Registro não encontrado no banco de dados.")
            return

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
            update_document(numero, tipo_documento, dados_atualizados)
            
            messagebox.showinfo("Sucesso", f"{tipo_documento} {numero} atualizado com sucesso!")
            
            # Voltar para lista e recarregar
            self.show_frame("Lista")
            self.buscar_com_reset()
            
        except Exception as e:
            messagebox.showerror("Erro no DB", f"Erro ao atualizar no banco de dados: {str(e)}")

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
                delete_document(numero, tipo_documento)

                if caminho_pdf and os.path.exists(caminho_pdf):
                    os.remove(caminho_pdf)
                
                messagebox.showinfo("Sucesso", f"Documento {numero} deletado e arquivo PDF removido.")
                self.buscar_com_reset()

            except Exception as e:
                messagebox.showerror("Erro", f"Erro ao deletar no banco de dados: {str(e)}")

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