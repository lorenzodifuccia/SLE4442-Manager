"""
xp_style.py
Stylesheet QSS che replica il tema "Luna" (blu) di Windows XP per app PyQt5.
Include la barra del titolo personalizzata e blocca il Dark Mode del sistema.
"""

from PyQt5 import QtGui

XP_QSS = """
/* ---------- Reset Globale Anti-Dark Mode ---------- */
/* Forza lo sfondo beige e il testo nero su TUTTI i widget, isolando l'app dal sistema */
QWidget {
    background-color: #ECE9D8;
    color: #000000;
    font-family: "Tahoma", "Segoe UI", sans-serif;
    font-size: 8pt;
}

/* ---------- Finestra Frameless ---------- */
/* Il QMainWindow deve rimanere trasparente per permettere i bordi arrotondati del wrapper */
QMainWindow {
    background: transparent;
}

#MainWindowWrapper {
    background-color: #ECE9D8;
    border: 3px solid #0054E3;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
}

/* ---------- Barra del Titolo ---------- */
#CustomTitleBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, 
        stop:0 #0058E6, stop:0.1 #3A93FF, stop:0.8 #288EFE, stop:1 #1240AB);
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}

#TitleLabel {
    background: transparent;
    color: black;
    font-weight: bold;
    font-family: "Trebuchet MS", "Tahoma", sans-serif;
    font-size: 10pt;
    padding-left: 4px;
}

/* ---------- Pulsanti Barra del Titolo ---------- */
#MinMaxButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #4698FE, stop:1 #0654D2);
    color: white;
    border: 1px solid white;
    border-radius: 3px;
    font-weight: bold;
    font-size: 10pt;
    margin-top: 2px;
    margin-bottom: 2px;
}

#MinMaxButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #60A5FE, stop:1 #1C65DB);
}

#CloseButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E04343, stop:1 #B91B1B);
    color: white;
    border: 1px solid white;
    border-radius: 3px;
    font-weight: bold;
    font-size: 9pt;
    margin-top: 2px;
    margin-bottom: 2px;
    margin-right: 2px;
}

#CloseButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #E76666, stop:1 #CC2D2D);
}

/* ---------- Menu bar ---------- */
QMenuBar {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #3B78C3, stop:1 #2A5DA8);
    color: white;
    border-bottom: 1px solid #1A3D6E;
    padding: 2px;
}

QMenuBar::item {
    background: transparent;
    padding: 4px 10px;
    color: white;
}

QMenuBar::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFD966, stop:1 #FFB700);
    color: black;
    border: 1px solid #C08000;
    border-radius: 2px;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
}

QMenu::item {
    background-color: transparent;
    padding: 4px 24px 4px 24px;
}

QMenu::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFE49C, stop:1 #FFB700);
    border: 1px solid #C08000;
}

QMenu::separator {
    height: 1px;
    background: #D4D0C8;
    margin: 4px 2px;
}

/* ---------- Etichette (Trasparenza) ---------- */
QLabel {
    background: transparent;
}

/* ---------- Pulsanti Generici ---------- */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.5 #ECE9D8, stop:1 #D6D2C2);
    border: 1px solid #919B9C;
    border-radius: 3px;
    padding: 4px 14px;
    min-height: 20px;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #FFFFFF, stop:0.5 #FFF3CE, stop:1 #FFDB7A);
    border: 1px solid #CC9933;
}

QPushButton:pressed {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
        stop:0 #E8D28A, stop:1 #FCE29B);
    border: 1px solid #C08000;
}

QPushButton:disabled {
    background: #ECE9D8;
    color: #A0A0A0;
    border: 1px solid #C0C0C0;
}

/* ---------- Campi di testo e Aree Dati ---------- */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #FFFFFF;
    border: 1px solid #7F9DB9;
    border-top: 1px solid #4A6B8A;
    border-left: 1px solid #4A6B8A;
    padding: 2px;
    selection-background-color: #316AC5;
    selection-color: white;
}

QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border: 1px solid #3B78C3;
}

/* ---------- ScrollArea (Risolve il problema della griglia scura) ---------- */
QScrollArea {
    background-color: #ECE9D8;
    border: none;
}
QScrollArea > QWidget > QWidget {
    background-color: #ECE9D8;
}

/* ---------- Scrollbar ---------- */
QScrollBar:vertical {
    background: #ECE9D8;
    width: 16px;
    border: 1px solid #ACA899;
}

QScrollBar::handle:vertical {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #D6D2C2, stop:0.5 #F5F3EA, stop:1 #D6D2C2);
    border: 1px solid #ACA899;
    min-height: 20px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background: #ECE9D8;
    border: 1px solid #ACA899;
    height: 16px;
}

/* ---------- Dialoghi / MessageBox ---------- */
QDialog, QMessageBox {
    background-color: #ECE9D8;
}
"""

def apply_xp_style(app):
    """Applica il tema Windows XP (Luna) bloccando i temi scuri moderni."""
    # Imposta lo stile base nativo su 'windows' per disattivare
    # il motore di rendering moderno che eredita la dark mode
    app.setStyle("windows")
    app.setFont(QtGui.QFont("Tahoma", 8))
    app.setStyleSheet(XP_QSS)