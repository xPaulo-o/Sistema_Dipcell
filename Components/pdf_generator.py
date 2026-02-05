import json
import os
from tkinter import messagebox

from reportlab.lib import colors
from reportlab.lib.colors import grey
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .config import LOGO_PADRAO, PASTA_OS
from .utils import formatar_monetario


def gerar_documento(
    dados,
    valor_texto,
    total_float,
    tipo_garantia,
    metodo_pagamento,
    checklist_str,
    tipo_documento,
    dias_garantia_num,
    parcelas_info=None,
):
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
                messagebox.showerror(
                    "Erro",
                    f"Não foi possível criar a pasta de documentos:\n{PASTA_OS}\n\n"
                    f"Erro: {str(e)}\n\n"
                    f"Verifique as permissões do diretório.",
                )
                return None
    except Exception as e:
        messagebox.showerror("Erro", f"Erro ao verificar/criar pasta: {str(e)}")
        return None

    pdf_path = os.path.join(PASTA_OS, f"{tipo_documento}_{dados['numero'].split('-')[1]}.pdf")

    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
    )

    styles = getSampleStyleSheet()
    normal = styles["Normal"]

    titulo_doc = "Ordem de Serviço" if tipo_documento == "OS" else "Comprovante de Venda"

    titulo = Paragraph(
        f"<b>DIPCELL<br/>{titulo_doc}</b>",
        ParagraphStyle("t", parent=styles["Heading1"], alignment=1, fontSize=22),
    )

    if os.path.exists(LOGO_PADRAO):
        img = Image(LOGO_PADRAO, width=120, height=120)
    else:
        img = Paragraph("", normal)

    header = Table([[img, titulo]], colWidths=[160, 330])
    header.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "MIDDLE")]))

    story = [header, Spacer(1, 10)]

    def bloco(titulo, lista):
        story.append(
            Paragraph(
                f"<b>{titulo}</b>",
                ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14),
            )
        )

        rows = [[Paragraph(f"<b>{k}</b>"), Paragraph(str(v))] for k, v in lista]

        tbl = Table(rows, colWidths=[160, 330])
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, 0), 0.6, colors.grey),
                    ("GRID", (0, 1), (-1, -1), 0.6, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ]
            )
        )

        story.append(tbl)
        story.append(Spacer(1, 4))

    def bloco_checklist(titulo, checklist_str):
        story.append(
            Paragraph(
                f"<b>{titulo}</b>",
                ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14),
            )
        )

        rows = []
        itens = [item.split(":") for item in checklist_str.split(";") if item.strip()]

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
                        ParagraphStyle("s", parent=normal, alignment=0, leading=8),
                    )
                else:
                    paragrafo = Paragraph("", normal)

                row_data.append(paragrafo)

            rows.append(row_data)

        col_widths = [5.66 * cm] * NUM_COLUNAS

        tbl = Table(rows, colWidths=col_widths)
        tbl.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0.5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0.5),
                ]
            )
        )

        story.append(tbl)
        story.append(Spacer(1, 4))

    def bloco_parcelas(detalhes_parcelas_json):
        try:
            lista_parcelas = json.loads(detalhes_parcelas_json)
        except Exception:
            return

        story.append(
            Paragraph(
                f"<b>Parcelamento (Crediário)</b>",
                ParagraphStyle("t2", parent=styles["Heading2"], fontSize=14),
            )
        )

        # Cabeçalho da tabela
        rows = [["Parcela", "Vencimento", "Valor", "Situação"]]

        for p in lista_parcelas:
            # Cria um espaço visual para marcar PG ou N/PG
            status_visual = "  (  ) PG    (  ) N/PG  "
            rows.append(
                [f"{p['numero']}x", p["vencimento"], f"R$ {p['valor']}", status_visual]
            )

        tbl = Table(rows, colWidths=[60, 100, 100, 230])
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.6, colors.grey),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ]
            )
        )
        story.append(tbl)
        story.append(Spacer(1, 4))

    bloco(
        "Dados do Cliente",
        [
            (f"Número {tipo_documento}", dados["numero"]),
            ("Cliente", dados["cliente"]),
            ("Telefone", dados["telefone"]),
            ("Data", dados["entrada"]),
        ],
    )

    if tipo_documento == "OS":
        bloco(
            "Aparelho",
            [
                ("Modelo", dados["modelo"]),
                ("IMEI", dados["imei"]),
                ("Acessórios", dados["acessorios"]),
                ("Senha/Padrão", dados["senha"]),
            ],
        )

        bloco_checklist("Lista de Checagem do Aparelho", checklist_str)

        problema_titulo = "Problemas / Detalhe"

    else:
        bloco(
            "Produto Vendido",
            [
                ("Produto", dados["modelo"]),
                ("Detalhes", dados["acessorios"]),
            ],
        )

        problema_titulo = "Detalhe (Venda)"

    bloco(
        titulo_doc,
        [
            (
                problema_titulo,
                dados["problemas"] if tipo_documento == "OS" else "Ver Produto Vendido",
            ),
            ("Situação" if tipo_documento == "OS" else "Status", dados["situacao"]),
            ("Valor (R$)", valor_texto),
            ("Total (R$)", formatar_monetario(total_float)),
            ("Método Pgto.", metodo_pagamento),
            ("Saída", dados["saida"] if dados["saida"] else "N/A"),  # Alterado para N/A se vazio
            ("Garantia até", dados["garantia"]),
            ("Tipo de Garantia", tipo_garantia),
        ],
    )

    if metodo_pagamento == "PARCELADO NO CREDIÁRIO" and parcelas_info:
        bloco_parcelas(parcelas_info)

    AVISO_PAGAMENTO = "NÃO SERÁ ENTREGUE O APARELHO/PRODUTO SEM ANTES ACERTAR O PAGAMENTO. "
    dias_garantia_texto = f"{dias_garantia_num} dias" if dias_garantia_num > 0 else "legal"
    termo_texto = ""

    if tipo_documento == "OS":
        if (
            dados["situacao"] == "CONCLUÍDA" and tipo_garantia == "Com Garantia"
        ):  # Condição alterada
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO}</b> A garantia cobre exclusivamente o **serviço** realizado pelo período de **{dias_garantia_texto}** informado nesta OS. "
                "Não cobre danos causados por mau uso, queda, oxidação, danos líquidos, tela quebrada ou violação do lacre. "
                "O aparelho deve ser retirado em até 90 dias após a conclusão do serviço.</font>"
            )
        else:
            termo_texto = (  # Se não for Concluída ou for Sem Garantia
                f"<font size='8'><b>{AVISO_PAGAMENTO} SERVIÇO SEM GARANTIA!</b> Esta OS está como <b>{dados['situacao']}</b>. O cliente está ciente de que o serviço realizado "
                "não possui cobertura de garantia devido à situação, natureza do reparo/peça ou condição do aparelho. "
                "O aparelho deve ser retirado em até 90 dias após a conclusão do serviço.</font>"
            )

    else:
        if (
            dados["situacao"] == "CONCLUÍDA" and tipo_garantia == "Com Garantia"
        ):  # Condição alterada
            termo_texto = (
                f"<font size='8'><b>{AVISO_PAGAMENTO}</b> A garantia de **{dias_garantia_texto}** cobre somente se o produto apresentar "
                "problemas de fábrica e estiver com a caixa do mesmo. "
                "A garantia **NÃO COBRE** danos por mau uso, queda, oxidação, danos líquidos ou remoção de selos de garantia.</font>"
            )
        else:
            termo_texto = (  # Se não for Concluída ou for Sem Garantia
                f"<font size='8'><b>{AVISO_PAGAMENTO} PRODUTO VENDIDO SEM GARANTIA!</b> O cliente está ciente de que este produto "
                "não possui cobertura de garantia (Status: {dados['situacao']}).</font>"
            )

    termo = Paragraph(termo_texto, normal)

    story.append(Spacer(1, 3))
    story.append(termo)
    story.append(Spacer(1, 3))

    assinatura_tbl = Table(
        [["__________________________________", "__________________________________"], ["Assinatura do Cliente", "Assinatura da Loja"]],
        colWidths=[245, 245],
    )

    assinatura_tbl.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )

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
        canvas.drawCentredString(W / 2, 35, "DIPCELL — Sistema de OS/Vendas")
        canvas.restoreState()

    try:
        doc.build(story, onFirstPage=desenhar_borda, onLaterPages=desenhar_borda)
        return pdf_path
    except Exception as e:
        messagebox.showerror(
            "Erro ao Gerar PDF",
            f"Erro ao gerar o documento PDF:\n{str(e)}\n\n"
            f"Verifique se você tem permissões de escrita no diretório:\n{PASTA_OS}",
        )
        return None
