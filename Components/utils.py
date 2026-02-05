import os
import sys
from tkinter import messagebox


def abrir_arquivo(caminho):
    """Abre um arquivo de forma compatível com Windows, Linux e Mac."""
    try:
        if sys.platform == "win32":
            os.startfile(caminho)
        elif sys.platform == "darwin":  # macOS
            os.system(f"open '{caminho}'")
        else:  # Linux e outros
            os.system(f"xdg-open '{caminho}'")
    except Exception:
        try:
            import subprocess

            subprocess.Popen([caminho], shell=True)
        except Exception as e2:
            try:
                messagebox.showerror(
                    "Erro",
                    f"Não foi possível abrir o arquivo:\n{caminho}\n\nErro: {str(e2)}",
                )
            except Exception:
                print(f"Erro ao abrir arquivo {caminho}: {str(e2)}")


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

