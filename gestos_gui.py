import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import json
import os
import subprocess

CONFIG_FILE = "gestos.json"

DEDOS = {
    8:  "Índice",
    12: "Medio",
    16: "Anular",
    20: "Meñique",
}

DEDOS_OPCIONES = [f"{v} ({k})" for k, v in DEDOS.items()]
DEDOS_INVERSO  = {f"{v} ({k})": k for k, v in DEDOS.items()}

TIPOS = ["hotkey", "comando"]

COLORES = {
    "bg":       "#0f0f0f",
    "panel":    "#1a1a1a",
    "card":     "#242424",
    "accent":   "#00ff88",
    "accent2":  "#0088ff",
    "danger":   "#ff4455",
    "warning":  "#ffaa00",
    "text":     "#e8e8e8",
    "subtext":  "#888888",
    "border":   "#333333",
    "hover":    "#2e2e2e",
    "inactive": "#555555",
}

def cargar_config():
    if not os.path.exists(CONFIG_FILE):
        messagebox.showerror("Error", f"No se encontró {CONFIG_FILE}")
        return None
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def guardar_config(data):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

class GestosApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestos — Configurador")
        self.geometry("820x620")
        self.resizable(True, True)
        self.configure(bg=COLORES["bg"])
        self.minsize(700, 500)

        self.config_data = cargar_config()
        if not self.config_data:
            self.destroy()
            return

        self._build_ui()
        self._render_gestos()

    # ────────────────────────────────────────────────
    # UI principal
    # ────────────────────────────────────────────────
    def _build_ui(self):
        # ── Header ──
        header = tk.Frame(self, bg=COLORES["bg"], pady=14, padx=24)
        header.pack(fill="x")

        tk.Label(
            header, text="✋  GESTOS", font=("Courier New", 20, "bold"),
            bg=COLORES["bg"], fg=COLORES["accent"]
        ).pack(side="left")

        tk.Label(
            header, text="Mano izquierda · Configurador",
            font=("Courier New", 10), bg=COLORES["bg"], fg=COLORES["subtext"]
        ).pack(side="left", padx=14, pady=4)

        btn_frame = tk.Frame(header, bg=COLORES["bg"])
        btn_frame.pack(side="right")

        self._btn(btn_frame, "+ Nuevo gesto", self._nuevo_gesto,
                  COLORES["accent"], COLORES["bg"]).pack(side="right", padx=4)
        self._btn(btn_frame, "💾 Guardar", self._guardar,
                  COLORES["bg"], COLORES["accent2"], border=True).pack(side="right", padx=4)

        # Separador
        tk.Frame(self, bg=COLORES["border"], height=1).pack(fill="x")

        # ── Umbral ──
        umbral_bar = tk.Frame(self, bg=COLORES["panel"], pady=8, padx=24)
        umbral_bar.pack(fill="x")

        tk.Label(umbral_bar, text="Umbral de detección:",
                 font=("Courier New", 10), bg=COLORES["panel"],
                 fg=COLORES["subtext"]).pack(side="left")

        self.umbral_var = tk.DoubleVar(value=self.config_data.get("umbral", 0.05))
        tk.Scale(
            umbral_bar, from_=0.02, to=0.12, resolution=0.005,
            orient="horizontal", variable=self.umbral_var,
            bg=COLORES["panel"], fg=COLORES["accent"],
            troughcolor=COLORES["border"], highlightthickness=0,
            activebackground=COLORES["accent"], length=200, showvalue=True
        ).pack(side="left", padx=10)

        tk.Label(umbral_bar,
                 text="(menor = más preciso, mayor = más fácil de activar)",
                 font=("Courier New", 9), bg=COLORES["panel"],
                 fg=COLORES["subtext"]).pack(side="left")

        tk.Frame(self, bg=COLORES["border"], height=1).pack(fill="x")

        # ── Scrollable cards ──
        container = tk.Frame(self, bg=COLORES["bg"])
        container.pack(fill="both", expand=True, padx=0, pady=0)

        canvas = tk.Canvas(container, bg=COLORES["bg"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg=COLORES["bg"])

        self.scroll_frame.bind("<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        canvas.create_window((0, 0), window=self.scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        canvas.bind_all("<MouseWheel>",
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        self.canvas = canvas

        # ── Status bar ──
        tk.Frame(self, bg=COLORES["border"], height=1).pack(fill="x")
        self.status_var = tk.StringVar(value="Listo.")
        tk.Label(
            self, textvariable=self.status_var,
            font=("Courier New", 9), bg=COLORES["panel"],
            fg=COLORES["subtext"], anchor="w", padx=16, pady=5
        ).pack(fill="x")

    # ────────────────────────────────────────────────
    # Render de tarjetas
    # ────────────────────────────────────────────────
    def _render_gestos(self):
        for w in self.scroll_frame.winfo_children():
            w.destroy()

        gestos = self.config_data.get("gestos", [])
        if not gestos:
            tk.Label(
                self.scroll_frame, text="No hay gestos configurados.\nPresiona '+ Nuevo gesto' para agregar uno.",
                font=("Courier New", 12), bg=COLORES["bg"],
                fg=COLORES["subtext"], justify="center"
            ).pack(pady=60)
            return

        for i, gesto in enumerate(gestos):
            self._card(self.scroll_frame, gesto, i)

    def _card(self, parent, gesto, idx):
        activo = gesto.get("activo", True)
        border_color = COLORES["accent"] if activo else COLORES["inactive"]

        outer = tk.Frame(parent, bg=border_color, pady=1, padx=1)
        outer.pack(fill="x", padx=20, pady=6)

        card = tk.Frame(outer, bg=COLORES["card"], pady=12, padx=16)
        card.pack(fill="x")

        # ── Fila 1: nombre + dedo + toggle + eliminar ──
        row1 = tk.Frame(card, bg=COLORES["card"])
        row1.pack(fill="x")

        # Número
        dedo_num = gesto.get("dedo", 8)
        dedo_label = DEDOS.get(dedo_num, str(dedo_num))
        tk.Label(row1, text=f"#{idx+1}", font=("Courier New", 10, "bold"),
                 bg=COLORES["card"], fg=COLORES["subtext"], width=3).pack(side="left")

        # Nombre (editable)
        nombre_var = tk.StringVar(value=gesto.get("nombre", ""))
        nombre_entry = tk.Entry(
            row1, textvariable=nombre_var,
            font=("Courier New", 12, "bold"),
            bg=COLORES["card"], fg=COLORES["text"],
            insertbackground=COLORES["accent"],
            relief="flat", bd=0, width=22
        )
        nombre_entry.pack(side="left", padx=4)
        nombre_entry.bind("<FocusOut>",
            lambda e, i=idx, v=nombre_var: self._update_campo(i, "nombre", v.get()))

        # Dedo pill
        tk.Label(row1, text=f"✋ {dedo_label}",
                 font=("Courier New", 9), bg=COLORES["border"],
                 fg=COLORES["accent2"], padx=8, pady=2).pack(side="left", padx=8)

        # Botones derecha
        right = tk.Frame(row1, bg=COLORES["card"])
        right.pack(side="right")

        toggle_text = "● ON" if activo else "○ OFF"
        toggle_fg   = COLORES["accent"] if activo else COLORES["inactive"]
        self._btn(right, toggle_text, lambda i=idx: self._toggle(i),
                  COLORES["card"], toggle_fg, border=True).pack(side="right", padx=4)

        self._btn(right, "✕", lambda i=idx: self._eliminar(i),
                  COLORES["card"], COLORES["danger"], border=True).pack(side="right", padx=2)

        self._btn(right, "⬆" if idx > 0 else " ",
                  (lambda i=idx: self._mover(i, -1)) if idx > 0 else lambda: None,
                  COLORES["card"], COLORES["subtext"], border=True).pack(side="right", padx=2)

        gestos = self.config_data.get("gestos", [])
        self._btn(right, "⬇" if idx < len(gestos)-1 else " ",
                  (lambda i=idx: self._mover(i, 1)) if idx < len(gestos)-1 else lambda: None,
                  COLORES["card"], COLORES["subtext"], border=True).pack(side="right", padx=2)

        # ── Fila 2: descripcion ──
        desc_var = tk.StringVar(value=gesto.get("descripcion", ""))
        desc_entry = tk.Entry(
            card, textvariable=desc_var,
            font=("Courier New", 9), bg=COLORES["card"],
            fg=COLORES["subtext"], insertbackground=COLORES["accent"],
            relief="flat", bd=0, width=50
        )
        desc_entry.pack(anchor="w", padx=3, pady=(2, 8))
        desc_entry.bind("<FocusOut>",
            lambda e, i=idx, v=desc_var: self._update_campo(i, "descripcion", v.get()))

        tk.Frame(card, bg=COLORES["border"], height=1).pack(fill="x", pady=4)

        # ── Fila 3: dedo + tipo + acción ──
        row3 = tk.Frame(card, bg=COLORES["card"])
        row3.pack(fill="x", pady=4)

        # Selector de dedo
        tk.Label(row3, text="Dedo:", font=("Courier New", 9),
                 bg=COLORES["card"], fg=COLORES["subtext"]).pack(side="left")

        dedo_str = f"{DEDOS.get(dedo_num, '?')} ({dedo_num})"
        dedo_combo = ttk.Combobox(row3, values=DEDOS_OPCIONES,
                                  width=14, font=("Courier New", 9))
        dedo_combo.set(dedo_str if dedo_str in DEDOS_OPCIONES else DEDOS_OPCIONES[0])
        dedo_combo.pack(side="left", padx=6)
        dedo_combo.bind("<<ComboboxSelected>>",
            lambda e, i=idx, c=dedo_combo: self._update_dedo(i, c.get()))

        # Selector de tipo
        tk.Label(row3, text="Tipo:", font=("Courier New", 9),
                 bg=COLORES["card"], fg=COLORES["subtext"]).pack(side="left", padx=(16,0))

        tipo_combo = ttk.Combobox(row3, values=TIPOS, width=10,
                                  font=("Courier New", 9))
        tipo_combo.set(gesto.get("tipo", "hotkey"))
        tipo_combo.pack(side="left", padx=6)
        tipo_combo.bind("<<ComboboxSelected>>",
            lambda e, i=idx, c=tipo_combo: self._update_campo(i, "tipo", c.get()))

        # Acción
        tk.Label(row3, text="Acción:", font=("Courier New", 9),
                 bg=COLORES["card"], fg=COLORES["subtext"]).pack(side="left", padx=(16,0))

        accion = gesto.get("accion", "")
        accion_str = "+".join(accion) if isinstance(accion, list) else accion
        accion_var = tk.StringVar(value=accion_str)

        accion_hint = "(teclas separadas por +)" if gesto.get("tipo") == "hotkey" else "(ruta o comando)"
        accion_entry = tk.Entry(
            row3, textvariable=accion_var,
            font=("Courier New", 9), bg=COLORES["border"],
            fg=COLORES["text"], insertbackground=COLORES["accent"],
            relief="flat", bd=0, width=28
        )
        accion_entry.pack(side="left", padx=6, ipady=3)
        accion_entry.bind("<FocusOut>",
            lambda e, i=idx, v=accion_var: self._update_accion(i, v.get()))

        tk.Label(row3, text=accion_hint, font=("Courier New", 8),
                 bg=COLORES["card"], fg=COLORES["subtext"]).pack(side="left")

        # Botón probar
        self._btn(row3, "▶ Probar", lambda i=idx: self._probar(i),
                  COLORES["warning"], COLORES["bg"]).pack(side="right", padx=4)

    # ────────────────────────────────────────────────
    # Acciones
    # ────────────────────────────────────────────────
    def _update_campo(self, idx, campo, valor):
        self.config_data["gestos"][idx][campo] = valor
        self.status_var.set(f"Modificado: gesto #{idx+1} · {campo}")

    def _update_dedo(self, idx, valor_str):
        num = DEDOS_INVERSO.get(valor_str, 8)
        self.config_data["gestos"][idx]["dedo"] = num
        self.status_var.set(f"Dedo actualizado: gesto #{idx+1} → {valor_str}")

    def _update_accion(self, idx, valor_str):
        tipo = self.config_data["gestos"][idx].get("tipo", "hotkey")
        if tipo == "hotkey":
            partes = [p.strip() for p in valor_str.split("+") if p.strip()]
            self.config_data["gestos"][idx]["accion"] = partes
        else:
            self.config_data["gestos"][idx]["accion"] = valor_str
        self.status_var.set(f"Acción actualizada: gesto #{idx+1}")

    def _toggle(self, idx):
        g = self.config_data["gestos"][idx]
        g["activo"] = not g.get("activo", True)
        self._render_gestos()
        estado = "activado" if g["activo"] else "desactivado"
        self.status_var.set(f"Gesto #{idx+1} {estado}")

    def _eliminar(self, idx):
        nombre = self.config_data["gestos"][idx].get("nombre", f"#{idx+1}")
        if messagebox.askyesno("Eliminar gesto", f"¿Eliminar '{nombre}'?"):
            self.config_data["gestos"].pop(idx)
            self._render_gestos()
            self.status_var.set(f"Gesto '{nombre}' eliminado")

    def _mover(self, idx, direccion):
        gestos = self.config_data["gestos"]
        nuevo = idx + direccion
        if 0 <= nuevo < len(gestos):
            gestos[idx], gestos[nuevo] = gestos[nuevo], gestos[idx]
            self._render_gestos()

    def _nuevo_gesto(self):
        nuevo = {
            "id": f"gesto_{len(self.config_data['gestos'])+1}",
            "nombre": "Nuevo gesto",
            "descripcion": "Descripción del gesto",
            "dedo": 8,
            "tipo": "hotkey",
            "accion": ["ctrl", "c"],
            "activo": True,
        }
        self.config_data["gestos"].append(nuevo)
        self._render_gestos()
        # Scroll al final
        self.after(100, lambda: self.canvas.yview_moveto(1.0))
        self.status_var.set("Nuevo gesto agregado — edita los campos y guarda")

    def _probar(self, idx):
        import pyautogui, time
        g = self.config_data["gestos"][idx]
        tipo   = g.get("tipo", "hotkey")
        accion = g.get("accion", [])
        nombre = g.get("nombre", f"#{idx+1}")
        try:
            if tipo == "hotkey":
                if isinstance(accion, list) and accion:
                    time.sleep(0.5)
                    pyautogui.hotkey(*accion)
                    self.status_var.set(f"Probado: {nombre} → {'+'.join(accion)}")
                else:
                    messagebox.showwarning("Sin acción", "Define teclas antes de probar.")
            elif tipo == "comando":
                if accion:
                    subprocess.Popen(accion, shell=True)
                    self.status_var.set(f"Probado: {nombre} → {accion}")
                else:
                    messagebox.showwarning("Sin acción", "Define un comando antes de probar.")
        except Exception as e:
            messagebox.showerror("Error al probar", str(e))

    def _guardar(self):
        self.config_data["umbral"] = round(self.umbral_var.get(), 4)
        guardar_config(self.config_data)
        self.status_var.set("✓ Configuración guardada en gestos.json")
        messagebox.showinfo("Guardado", "gestos.json actualizado correctamente.")

    # ────────────────────────────────────────────────
    # Helper botón
    # ────────────────────────────────────────────────
    def _btn(self, parent, text, command, bg, fg, border=False):
        relief = "groove" if border else "flat"
        b = tk.Button(
            parent, text=text, command=command,
            font=("Courier New", 9, "bold"),
            bg=bg, fg=fg, activebackground=COLORES["hover"],
            activeforeground=fg, relief=relief,
            bd=1 if border else 0,
            cursor="hand2", padx=8, pady=3
        )
        return b


if __name__ == "__main__":
    app = GestosApp()
    app.mainloop()
