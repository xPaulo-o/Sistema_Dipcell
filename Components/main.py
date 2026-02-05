import customtkinter as ctk
from config import init_customtkinter
from database import criar_banco
from gui import SistemaOS

if __name__ == "__main__":
    criar_banco()
    ctk_module = init_customtkinter()
    
    app = ctk_module.CTk()
    SistemaOS(app)
    app.mainloop()