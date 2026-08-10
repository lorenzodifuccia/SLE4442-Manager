from card.sle4442 import *
from datetime import datetime
import hashlib
import os

try:
    from PyQt5 import QtWidgets, QtGui, QtCore
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.wayland*=false"
    HAS_QT = True
except Exception:
    HAS_QT = False

if HAS_QT:
    class ByteCell(QtWidgets.QLineEdit):
        """A single editable/clickable byte cell in the memory grid."""
        clicked = QtCore.pyqtSignal(int)

        UNCHANGED_STYLE = ""
        MODIFIED_STYLE = "background-color: #FFF3A0; color: #000000; font-weight: bold;"

        def __init__(self, addr, parent=None):
            super().__init__(parent)
            self.addr = addr
            self.setMaxLength(2)
            self.setAlignment(QtCore.Qt.AlignCenter)
            self.setFont(QtGui.QFont("Courier", 10))
            self.setFixedWidth(30)
            self.setValidator(QtGui.QRegExpValidator(QtCore.QRegExp("[0-9A-Fa-f]{0,2}")))
            self.setReadOnly(True)
            self.setStyleSheet(self.UNCHANGED_STYLE)
            self.setToolTip(f"Address 0x{addr:02X}")

        def mousePressEvent(self, event):
            self.clicked.emit(self.addr)
            super().mousePressEvent(event)


    class CustomTitleBar(QtWidgets.QWidget):
        """Barra del titolo personalizzata stile Windows XP."""

        def __init__(self, parent):
            super().__init__(parent)
            self.parent = parent
            self.setObjectName("CustomTitleBar")
            self.setFixedHeight(30)

            # Forza l'applicazione del background
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

            layout = QtWidgets.QHBoxLayout(self)
            layout.setContentsMargins(5, 0, 0, 0)
            layout.setSpacing(2)

            self.title_label = QtWidgets.QLabel("SLE4442 Manager")
            self.title_label.setObjectName("TitleLabel")

            self.btn_minimize = QtWidgets.QPushButton("-")
            self.btn_minimize.setFixedSize(22, 22)
            self.btn_minimize.setObjectName("MinMaxButton")
            self.btn_minimize.clicked.connect(self.parent.showMinimized)

            self.btn_maximize = QtWidgets.QPushButton("□")
            self.btn_maximize.setFixedSize(22, 22)
            self.btn_maximize.setObjectName("MinMaxButton")
            self.btn_maximize.clicked.connect(self.toggle_maximize)

            self.btn_close = QtWidgets.QPushButton("X")
            self.btn_close.setFixedSize(22, 22)
            self.btn_close.setObjectName("CloseButton")
            self.btn_close.clicked.connect(self.parent.close)

            layout.addWidget(self.title_label)
            layout.addStretch()
            layout.addWidget(self.btn_minimize)
            layout.addWidget(self.btn_maximize)
            layout.addWidget(self.btn_close)

            self._drag_pos = None

        def toggle_maximize(self):
            if self.parent.isMaximized():
                self.parent.showNormal()
                self.btn_maximize.setText("□")
            else:
                self.parent.showMaximized()
                self.btn_maximize.setText("❐")

        def mousePressEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self._drag_pos = event.globalPos() - self.parent.frameGeometry().topLeft()
                event.accept()

        def mouseMoveEvent(self, event):
            if event.buttons() == QtCore.Qt.LeftButton and self._drag_pos is not None:
                if self.parent.isMaximized():
                    self.parent.showNormal()
                    self.btn_maximize.setText("□")
                    self._drag_pos = QtCore.QPoint(self.width() // 2, event.pos().y())
                self.parent.move(event.globalPos() - self._drag_pos)
                event.accept()

        def mouseDoubleClickEvent(self, event):
            if event.button() == QtCore.Qt.LeftButton:
                self.toggle_maximize()
                event.accept()


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SLE4442 Manager")
        self.resize(1000, 700)

        # --- FORZA LO STILE FUSION COME DEFAULT (Bottoni arrotondati) ---
        self._default_style_name = "Fusion"

        # --- Configurazione Finestra Frameless per stile XP ---
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint | QtCore.Qt.WindowMinimizeButtonHint)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)

        # Il widget wrapper contiene l'intera app
        self.wrapper = QtWidgets.QWidget()
        self.wrapper.setObjectName("MainWindowWrapper")
        self.setCentralWidget(self.wrapper)

        # Layout principale del wrapper
        wrapper_layout = QtWidgets.QVBoxLayout(self.wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        # 1. Barra del Titolo Personalizzata XP
        self.title_bar = CustomTitleBar(self)
        wrapper_layout.addWidget(self.title_bar)

        # 2. Barra dei Menu inserita manualmente sotto il titolo
        self.custom_menubar = QtWidgets.QMenuBar()
        wrapper_layout.addWidget(self.custom_menubar)

        # 3. Contenitore dell'Applicazione
        w = QtWidgets.QWidget()
        wrapper_layout.addWidget(w, 1)
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 10, 10, 10)

        self.intf = SLE4442Interface(log_callback=self.log)
        self.intf.establish()
        self.current_reader = None
        self.loaded_data = None

        self.original_data = None
        self.modified = set()
        self.card_unlocked = False
        self.grid_mode = None
        self.byte_cells = []

        self.create_menus()

        # Top controls
        top = QtWidgets.QHBoxLayout()

        self.read_btn = QtWidgets.QPushButton("Read All")
        self.unlock_btn = QtWidgets.QPushButton("Unlock (PSC)")
        self.export_btn = QtWidgets.QPushButton("Export to .hex")

        self.import_btn = QtWidgets.QPushButton("Import .hex")
        self.write_btn = QtWidgets.QPushButton("Write to Card")
        self.write_btn.setEnabled(False)

        self.save_btn = QtWidgets.QPushButton("Save")
        self.save_btn.setEnabled(False)

        top.addWidget(self.read_btn)
        top.addWidget(self.unlock_btn)
        top.addWidget(self.export_btn)
        separator = QtWidgets.QLabel(" | ")
        top.addWidget(separator)
        top.addWidget(self.import_btn)
        top.addWidget(self.write_btn)
        separator2 = QtWidgets.QLabel(" | ")
        top.addWidget(separator2)
        top.addWidget(self.save_btn)
        top.addStretch()
        v.addLayout(top)

        # --- Intestazione Memoria e Selezione Colonne (Sempre visibile) ---
        header_lay = QtWidgets.QHBoxLayout()
        mem_label = QtWidgets.QLabel("Main Memory (256 bytes) — click a byte to edit it (unlock required):")

        self.col_combo = QtWidgets.QComboBox()
        self.col_combo.addItems(["8 columns", "16 columns", "32 columns"])
        self.col_combo.setCurrentIndex(1)  # Default 16 colonne
        self.col_combo.currentIndexChanged.connect(self.rebuild_grid)

        header_lay.addWidget(mem_label)
        header_lay.addStretch()
        header_lay.addWidget(QtWidgets.QLabel("Columns:"))
        header_lay.addWidget(self.col_combo)
        v.addLayout(header_lay)

        # --- Griglia Esadecimale gestita con StackedWidget ---
        self.mem_stack = QtWidgets.QStackedWidget()

        # Pagina 0: Placeholder (Nessun dato caricato)
        self.placeholder_lbl = QtWidgets.QLabel("No data loaded.\nClick 'Read All' or 'Import .hex' to view memory.")
        self.placeholder_lbl.setAlignment(QtCore.Qt.AlignCenter)
        # Stile neutro che va bene sia per XP che per Dark Mode
        self.placeholder_lbl.setStyleSheet("color: #777; font-size: 14px;")
        self.mem_stack.addWidget(self.placeholder_lbl)

        # Pagina 1: La griglia vera e propria
        self.hex_scroll = QtWidgets.QScrollArea()
        self.hex_scroll.setWidgetResizable(True)
        self.hex_grid_widget, self.byte_cells = self.build_hex_grid(16)
        self.hex_scroll.setWidget(self.hex_grid_widget)
        self.mem_stack.addWidget(self.hex_scroll)

        # Aggiungiamo lo stack al layout principale, partendo dalla pagina vuota (0)
        v.addWidget(self.mem_stack, 2)
        self.mem_stack.setCurrentIndex(0)

        # Log view
        log_label = QtWidgets.QLabel("Log:")
        v.addWidget(log_label)
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setFont(QtGui.QFont("Courier", 9))
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumHeight(150)
        v.addWidget(self.log_view, 1)

        # Bottom status with SizeGrip for resizing
        bottom = QtWidgets.QHBoxLayout()
        self.status_label = QtWidgets.QLabel("Disconnected")
        bottom.addWidget(self.status_label)
        bottom.addStretch()

        self.size_grip = QtWidgets.QSizeGrip(self)
        bottom.addWidget(self.size_grip, 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight)

        v.addLayout(bottom)

        # Connect signals
        self.read_btn.clicked.connect(self.do_read_all)
        self.import_btn.clicked.connect(self.do_import_hex)
        self.write_btn.clicked.connect(self.do_write_to_card)
        self.export_btn.clicked.connect(self.do_export_hex)
        self.unlock_btn.clicked.connect(self.do_unlock)
        self.save_btn.clicked.connect(self.do_save_bytes)

        # Initialize
        self.log("Application started")
        self.log("⚠️ WARNING: Write operations can permanently modify card data!")

        # Imposta il tema iniziale
        self.current_theme = "xp"
        self.apply_theme("default")

        # Check for readers at startup
        QtCore.QTimer.singleShot(100, self.check_readers_at_startup)

    # ---------------------------------------------------------------
    # Grid & Column Management
    # ---------------------------------------------------------------
    def build_hex_grid(self, cols=16):
        container = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(container)
        grid.setSpacing(2)

        grid.addWidget(QtWidgets.QLabel(""), 0, 0)
        for col in range(cols):
            lbl = QtWidgets.QLabel(f"{col:X}")
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("font-weight: bold;")
            grid.addWidget(lbl, 0, col + 1)

        cells = []
        rows = MAIN_MEM_SIZE // cols
        if MAIN_MEM_SIZE % cols != 0:
            rows += 1

        for row in range(rows):
            addr_lbl = QtWidgets.QLabel(f"{row * cols:02X}")
            addr_lbl.setStyleSheet("font-weight: bold;")
            grid.addWidget(addr_lbl, row + 1, 0)

            for col in range(cols):
                addr = row * cols + col
                if addr >= MAIN_MEM_SIZE:
                    break
                cell = ByteCell(addr)
                cell.clicked.connect(self.on_byte_clicked)
                cell.editingFinished.connect(lambda a=addr: self.on_byte_edited(a))
                grid.addWidget(cell, row + 1, col + 1)
                cells.append(cell)

        grid.setRowStretch(rows + 1, 1)
        grid.setColumnStretch(cols + 1, 1)
        return container, cells

    def rebuild_grid(self):
        cols_text = self.col_combo.currentText()
        cols = int(cols_text.split()[0])

        current_texts = {cell.addr: cell.text() for cell in self.byte_cells}

        self.hex_grid_widget, self.byte_cells = self.build_hex_grid(cols)
        self.hex_scroll.setWidget(self.hex_grid_widget)

        for cell in self.byte_cells:
            addr = cell.addr
            if addr in current_texts:
                cell.blockSignals(True)
                cell.setText(current_texts[addr])
                cell.blockSignals(False)

            if self.grid_mode == "card" and self.card_unlocked:
                cell.setReadOnly(False)
            else:
                cell.setReadOnly(True)

            if addr in self.modified:
                cell.setStyleSheet(ByteCell.MODIFIED_STYLE)
            else:
                cell.setStyleSheet(ByteCell.UNCHANGED_STYLE)

    def load_data_into_grid(self, data, editable_source=True):
        if len(data) != len(self.byte_cells):
            self.log(
                f"⚠️ Expected {len(self.byte_cells)} bytes, got {len(data)} "
                f"from the reader - truncating/padding to fit the grid"
            )
            if len(data) > len(self.byte_cells):
                data = data[:len(self.byte_cells)]
            else:
                data = bytes(data) + b'\x00' * (len(self.byte_cells) - len(data))

        for addr, b in enumerate(data):
            cell = self.byte_cells[addr]
            cell.blockSignals(True)
            cell.setText(f"{b:02X}")
            cell.blockSignals(False)
            cell.setStyleSheet(ByteCell.UNCHANGED_STYLE)
            cell.setReadOnly(True)

        self.modified.clear()
        self.save_btn.setEnabled(False)

        if editable_source:
            self.original_data = bytearray(data)
            self.grid_mode = "card"
            if self.card_unlocked:
                for cell in self.byte_cells:
                    cell.setReadOnly(False)
        else:
            self.original_data = None
            self.grid_mode = "preview"

        # Switch to the grid page now that data is loaded
        self.mem_stack.setCurrentIndex(1)

    def on_byte_clicked(self, addr):
        if self.grid_mode != "card" or self.original_data is None:
            QtWidgets.QMessageBox.information(
                self, "Read-Only Preview",
                "This is a read-only preview.\n\n"
                "Press 'Read All' to load the card's actual memory and "
                "enable byte-by-byte editing."
            )
            return

        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader from the Readers menu first."
            )
            return

        if not self.card_unlocked:
            self.unlock_for_editing(focus_addr=addr)
            return

        cell = self.byte_cells[addr]
        cell.setReadOnly(False)
        cell.selectAll()

    def unlock_for_editing(self, focus_addr=None):
        pin, ok = QtWidgets.QInputDialog.getText(
            self, "Unlock to Edit",
            "Enter 3-byte PSC (6 hex digits) to enable byte-by-byte editing:"
        )

        if not ok:
            return

        pin = pin.strip().replace(" ", "").upper()

        if len(pin) != 6 or not all(c in "0123456789ABCDEF" for c in pin):
            QtWidgets.QMessageBox.warning(
                self, "Invalid PIN",
                "PSC must be exactly 6 hex digits (0-9, A-F).\nExample: FFFFFF"
            )
            return

        try:
            pin_bytes = bytes.fromhex(pin)
            self.log("Attempting unlock for byte editing...")
            res = self.intf.unlock_with_pin_bytes(pin_bytes)

            if res == "unlocked":
                self.card_unlocked = True
                for cell in self.byte_cells:
                    cell.setReadOnly(False)
                self.log("✅ Card unlocked - byte editing enabled")
                self.set_status("Unlocked — click any byte to edit")

                if focus_addr is not None:
                    cell = self.byte_cells[focus_addr]
                    cell.setFocus()
                    cell.selectAll()
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Unlock Failed", f"Result: {res}"
                )
                self.log(f"Unlock for editing failed: {res}")
        except Exception as e:
            self.handle_exception(e, "Unlock")

    def on_byte_edited(self, addr):
        cell = self.byte_cells[addr]
        text = cell.text().upper()

        if len(text) != 2 or not all(c in "0123456789ABCDEF" for c in text):
            if self.original_data is not None:
                cell.blockSignals(True)
                cell.setText(f"{self.original_data[addr]:02X}")
                cell.blockSignals(False)
            return

        cell.blockSignals(True)
        cell.setText(text)
        cell.blockSignals(False)

        new_val = int(text, 16)

        if self.original_data is not None and new_val == self.original_data[addr]:
            self.modified.discard(addr)
            cell.setStyleSheet(ByteCell.UNCHANGED_STYLE)
        else:
            self.modified.add(addr)
            cell.setStyleSheet(ByteCell.MODIFIED_STYLE)

        self.save_btn.setEnabled(len(self.modified) > 0)

    def do_save_bytes(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader from the Readers menu first."
            )
            return

        if not self.modified:
            return

        changes = sorted(self.modified)
        preview_lines = [
            f"0x{addr:02X}: {self.original_data[addr]:02X} → {self.byte_cells[addr].text()}"
            for addr in changes
        ]
        preview = "\n".join(preview_lines[:20])
        if len(preview_lines) > 20:
            preview += f"\n... and {len(preview_lines) - 20} more byte(s)"

        msg = (
            f"⚠️ You are about to write {len(changes)} modified byte(s) to the card:\n\n"
            f"{preview}\n\n"
            "This operation is permanent. Continue?"
        )

        reply = QtWidgets.QMessageBox.warning(
            self, "Confirm Save", msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            self.log("Save cancelled by user")
            return

        try:
            self.log(f"Saving {len(changes)} modified byte(s)...")
            self.set_status("Saving changes...")

            for addr in changes:
                val = int(self.byte_cells[addr].text(), 16)
                self.intf.write(addr, bytes([val]))

            self.log("Verifying changes...")
            verify_data = self.intf.read(0, MAIN_MEM_SIZE)

            failed = [
                addr for addr in changes
                if verify_data[addr] != int(self.byte_cells[addr].text(), 16)
            ]

            self.load_data_into_grid(verify_data, editable_source=True)

            if not failed:
                self.log(f"✅ Saved {len(changes)} byte(s) successfully")
                self.set_status(f"Saved {len(changes)} byte(s)")
                QtWidgets.QMessageBox.information(
                    self, "Saved",
                    f"✅ {len(changes)} byte(s) written and verified successfully."
                )
            else:
                self.log(f"⚠️ {len(failed)} byte(s) failed to write (protected?)")
                self.set_status("Save completed with errors")
                QtWidgets.QMessageBox.warning(
                    self, "Partial Save",
                    f"⚠️ {len(failed)} byte(s) were not written correctly.\n"
                    f"Addresses: {', '.join(f'0x{a:02X}' for a in failed)}\n\n"
                    "They may be write-protected (check Protection Bits)."
                )
        except Exception as e:
            self.handle_exception(e, "Save")

    def check_readers_at_startup(self):
        try:
            readers = self.intf.list_readers()
            if not readers:
                self.show_no_readers_alert()
            else:
                self.refresh_readers_menu()
        except Exception as e:
            self.log(f"Startup check error: {e}")
            self.show_no_readers_alert(error_msg=str(e))

    def show_no_readers_alert(self, error_msg=None):
        msg = "⚠️ No Smart Card Readers Found\n\n"

        if error_msg:
            msg += f"Error: {error_msg}\n\n"
        else:
            msg += "No PC/SC compatible smart card readers detected.\n\n"

        msg += "Please ensure:\n"
        msg += "• Your card reader is properly connected\n"
        msg += "• Reader drivers are installed\n"
        msg += "• PC/SC service is running"

        msg_box = QtWidgets.QMessageBox.warning(
            self, "No Readers Found", msg,
            QtWidgets.QMessageBox.Retry | QtWidgets.QMessageBox.Cancel
        )

        if msg_box == QtWidgets.QMessageBox.Retry:
            self.log("User requested reader re-check")
            try:
                readers = self.intf.list_readers()
                if not readers:
                    self.log("Re-check: Still no readers found")
                    self.show_no_readers_alert()
                else:
                    self.log(f"Re-check: Found {len(readers)} reader(s)")
                    self.refresh_readers_menu()
                    QtWidgets.QMessageBox.information(
                        self, "Readers Found",
                        f"✅ Found {len(readers)} reader(s):\n" + "\n".join(f"- {r}" for r in readers)
                    )
            except Exception as e:
                self.log(f"Re-check error: {e}")
                self.show_no_readers_alert(error_msg=str(e))
        else:
            self.log("User cancelled reader check")
            self.set_status("No readers available")

    def create_menus(self):
        menubar = self.custom_menubar

        self.reader_menu = menubar.addMenu("&Readers")
        self.reader_group = QtWidgets.QActionGroup(self)
        self.reader_group.triggered.connect(self.on_reader_selected)

        card_menu = menubar.addMenu("&Card")

        actions = [
            ("&Read All", self.do_read_all, None),
            None,
            ("&Unlock (PSC)", self.do_unlock, None),
            ("&Change PIN", self.do_change_pin, "Ctrl+P"),
            None,
            ("&Export HEX", self.do_export_hex, "Ctrl+E"),
            ("&Import HEX", self.do_import_hex, "Ctrl+I"),
            ("&Write to Card", self.do_write_to_card, "Ctrl+W"),
            None,
            ("Card &Information", self.show_card_info, None),
            ("&Security Memory", self.show_security_memory, None),
            ("P&rotection Bits", self.show_protection_bits, None),
        ]

        for item in actions:
            if item is None:
                card_menu.addSeparator()
            else:
                name, handler, shortcut = item
                action = QtWidgets.QAction(name, self)
                action.triggered.connect(handler)
                if shortcut:
                    action.setShortcut(shortcut)
                card_menu.addAction(action)

        tools_menu = menubar.addMenu("&Tools")
        raw_apdu_action = QtWidgets.QAction("Send Raw &APDU", self)
        raw_apdu_action.setShortcut("Ctrl+R")
        raw_apdu_action.triggered.connect(self.do_send_raw_apdu)
        tools_menu.addAction(raw_apdu_action)

        settings_menu = menubar.addMenu("&Settings")

        theme_menu = settings_menu.addMenu("&Theme")
        self.theme_group = QtWidgets.QActionGroup(self)
        self.theme_group.setExclusive(True)

        default_theme_action = QtWidgets.QAction("&Default (Original)", self)
        default_theme_action.setCheckable(True)
        default_theme_action.setChecked(True)
        default_theme_action.setData("default")
        self.theme_group.addAction(default_theme_action)
        theme_menu.addAction(default_theme_action)

        xp_theme_action = QtWidgets.QAction("&Windows XP", self)
        xp_theme_action.setCheckable(True)
        xp_theme_action.setData("xp")
        self.theme_group.addAction(xp_theme_action)
        theme_menu.addAction(xp_theme_action)

        self.theme_group.triggered.connect(self.on_theme_selected)

        settings_menu.addSeparator()

        self.apdu_log_action = QtWidgets.QAction("Log &APDUs", self)
        self.apdu_log_action.setCheckable(True)
        self.apdu_log_action.setChecked(False)
        self.apdu_log_action.triggered.connect(self.toggle_apdu_logging)
        settings_menu.addAction(self.apdu_log_action)

        settings_menu.addSeparator()

        clear_log_action = QtWidgets.QAction("&Clear Log", self)
        clear_log_action.triggered.connect(self.clear_log)
        settings_menu.addAction(clear_log_action)

        help_menu = menubar.addMenu("&Help")
        about_action = QtWidgets.QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def toggle_apdu_logging(self):
        self.intf.log_apdus = self.apdu_log_action.isChecked()
        status = "enabled" if self.intf.log_apdus else "disabled"
        self.log(f"APDU logging {status}")

    def _get_apply_xp_style(self):
        try:
            from xp_style import apply_xp_style
            return apply_xp_style
        except ImportError:
            pass
        try:
            from .xp_style import apply_xp_style
            return apply_xp_style
        except ImportError:
            return None

    def _configure_theme(self, theme):
        app = QtWidgets.QApplication.instance()

        if theme == "xp":
            apply_xp_style = self._get_apply_xp_style()
            if apply_xp_style is None:
                QtWidgets.QMessageBox.warning(
                    self, "Theme Unavailable",
                    "Could not load xp_style.py"
                )
                return False

            apply_xp_style(app)
            self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
            self.setWindowFlags(
                QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowSystemMenuHint |
                QtCore.Qt.WindowMinimizeButtonHint
            )
            self.title_bar.show()
            self.size_grip.show()

            self.write_btn.setStyleSheet("")
            self.save_btn.setStyleSheet("")
        else:
            app.setStyleSheet("")
            app.setStyle(QtWidgets.QStyleFactory.create(self._default_style_name))

            self.setAttribute(QtCore.Qt.WA_StyledBackground, False)
            self.setWindowFlags(QtCore.Qt.Window)
            self.title_bar.hide()
            self.size_grip.hide()

            self.write_btn.setStyleSheet(
                "QPushButton:enabled { background-color: #ff9800; color: white; font-weight: bold; }")
            self.save_btn.setStyleSheet(
                "QPushButton:enabled { background-color: #4CAF50; color: white; font-weight: bold; }")

        self.current_theme = theme
        return True

    def apply_theme(self, theme):
        was_visible = self.isVisible()
        ok = self._configure_theme(theme)

        if was_visible:
            self.show()

        if ok:
            label = "Windows XP" if theme == "xp" else "Default (Original)"
            self.log(f"Theme switched to: {label}")
            self.set_status(f"Theme: {label}")

    def on_theme_selected(self, action):
        theme = action.data()
        if theme == self.current_theme:
            return
        self.apply_theme(theme)

    def clear_log(self):
        self.log_view.clear()
        self.log("Log cleared")

    def refresh_readers_menu(self):
        self.reader_menu.clear()

        refresh_action = QtWidgets.QAction("Refresh Readers", self)
        refresh_action.triggered.connect(self.refresh_readers_menu)
        self.reader_menu.addAction(refresh_action)
        self.reader_menu.addSeparator()

        self.reader_group = QtWidgets.QActionGroup(self)
        self.reader_group.triggered.connect(self.on_reader_selected)

        try:
            readers = self.intf.list_readers()
            if not readers:
                no_reader = QtWidgets.QAction("No readers found", self)
                no_reader.setEnabled(False)
                self.reader_menu.addAction(no_reader)
                self.log("No readers found")
            else:
                for reader in readers:
                    action = QtWidgets.QAction(reader, self)
                    action.setCheckable(True)
                    action.setData(reader)
                    self.reader_group.addAction(action)
                    self.reader_menu.addAction(action)
                    if self.current_reader == reader:
                        action.setChecked(True)
                self.log(f"Found {len(readers)} reader(s)")
        except Exception as e:
            self.log(f"Error listing readers: {e}")

    def on_reader_selected(self, action):
        reader_name = action.data()
        try:
            if self.intf.hcard:
                self.intf.disconnect(release_context=False)
            self.intf.connect(reader_name)
            self.current_reader = reader_name
            self.set_status(f"Connected: {reader_name}")
            self.log(f"Connected to reader: {reader_name}")

            self.card_unlocked = False
            for cell in self.byte_cells:
                cell.setReadOnly(True)
        except Exception as e:
            self.set_status("Connection failed")
            self.log(f"Error connecting to {reader_name}: {e}")
            QtWidgets.QMessageBox.critical(self, "Connection Error", str(e))

    def handle_card_error(self, error, operation_name, offer_unlock=False, offer_raw_apdu=False):
        msg = QtWidgets.QMessageBox(self)

        if isinstance(error, WrongPINError):
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setWindowTitle("Wrong PIN")
        elif isinstance(error, INSNotSupportedError):
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setWindowTitle("APDU Not Supported")
        elif isinstance(error, (CommandNotAllowedError, SecurityNotSatisfiedError)):
            msg.setIcon(QtWidgets.QMessageBox.Warning)
            msg.setWindowTitle("Security Error")
        else:
            msg.setIcon(QtWidgets.QMessageBox.Critical)
            msg.setWindowTitle(f"{operation_name} Error")

        msg.setText(f"{operation_name} failed")
        msg.setInformativeText(str(error))

        if offer_raw_apdu and isinstance(error, INSNotSupportedError):
            msg.addButton("Open Raw APDU Tool", QtWidgets.QMessageBox.YesRole)
            msg.addButton(QtWidgets.QMessageBox.Close)

            if msg.exec_() == 0:
                self.do_send_raw_apdu()
        elif offer_unlock:
            unlock_btn = msg.addButton("Unlock Card", QtWidgets.QMessageBox.ActionRole)
            security_btn = msg.addButton("Check Security", QtWidgets.QMessageBox.ActionRole)
            msg.addButton(QtWidgets.QMessageBox.Close)

            msg.setDefaultButton(unlock_btn)
            msg.exec_()

            clicked = msg.clickedButton()
            if clicked == unlock_btn:
                self.do_unlock()
            elif clicked == security_btn:
                self.show_security_memory()
        else:
            msg.exec_()

    def handle_exception(self, e, operation_name):
        self.log(f"{operation_name} error: {e}")
        self.set_status(f"{operation_name} failed")

        if isinstance(e, INSNotSupportedError):
            self.handle_card_error(e, operation_name, offer_raw_apdu=True)
        elif isinstance(e, (CommandNotAllowedError, SecurityNotSatisfiedError, WrongPINError)):
            self.handle_card_error(e, operation_name, offer_unlock=True)
        else:
            QtWidgets.QMessageBox.critical(self, f"{operation_name} Error", str(e))

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{timestamp}] {message}")

    def set_status(self, text):
        self.status_label.setText(text)

    def do_read_all(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader from the Readers menu first."
            )
            self.log("Read failed: not connected")
            return

        try:
            self.log("Reading main memory...")
            data = self.intf.read(0, MAIN_MEM_SIZE)
            self.load_data_into_grid(data, editable_source=True)
            self.log(f"Read {len(data)} bytes successfully")
            self.set_status(f"Read OK — {len(data)} bytes")
        except Exception as e:
            self.handle_exception(e, "Read")

    def do_import_hex(self):
        filename, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Import HEX File", "",
            "HEX Files (*.hex *.txt);;All Files (*.*)"
        )
        if not filename:
            self.log("Import cancelled by user")
            return

        try:
            self.log(f"Importing file: {filename}")
            with open(filename, "r") as f:
                hexstr = f.read().strip().replace(" ", "").replace("\n", "").replace("\r", "")

            if len(hexstr) != MAIN_MEM_SIZE * 2:
                raise ValueError(
                    f"HEX file must contain exactly {MAIN_MEM_SIZE * 2} hex characters "
                    f"({MAIN_MEM_SIZE} bytes), found {len(hexstr)}"
                )

            data = bytes.fromhex(hexstr)
            self.loaded_data = data
            self.load_data_into_grid(data, editable_source=False)
            self.write_btn.setEnabled(True)

            info = (
                f"✅ File imported successfully!\n\n"
                f"File: {filename}\n"
                f"Data loaded: {len(data)} bytes\n\n"
                f"SHA-256: {hashlib.sha256(data).hexdigest()[:32]}...\n\n"
                f"Ready to write to card.\n"
                f"⚠️ Make sure the card is unlocked first!"
            )

            QtWidgets.QMessageBox.information(self, "Import Successful", info)
            self.log(f"Imported {len(data)} bytes from {filename}")
            self.set_status(f"Data loaded - ready to write")
        except Exception as e:
            self.log(f"Import error: {e}")
            QtWidgets.QMessageBox.critical(
                self, "Import Error",
                f"Failed to import file:\n\n{str(e)}"
            )

    def do_write_to_card(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader and connect to a card first."
            )
            self.log("Write failed: not connected")
            return

        if self.loaded_data is None:
            QtWidgets.QMessageBox.warning(
                self, "No Data",
                "Please import a .hex file first."
            )
            self.log("Write failed: no data loaded")
            return

        msg = (
            "⚠️ WARNING: Write Operation\n\n"
            "You are about to write data to the card.\n"
            "This operation will PERMANENTLY modify the card!\n\n"
            f"Data size: {len(self.loaded_data)} bytes\n"
            f"SHA-256: {hashlib.sha256(self.loaded_data).hexdigest()[:32]}...\n\n"
            "Prerequisites:\n"
            "• Card must be unlocked with correct PSC\n"
            "• Protected bytes cannot be written\n"
            "• Operation cannot be undone\n\n"
            "Do you want to continue?"
        )

        reply = QtWidgets.QMessageBox.warning(
            self, "Confirm Write Operation", msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            self.log("Write cancelled by user")
            return

        try:
            self.log("Starting write operation...")
            self.set_status("Writing to card...")

            bytes_written = self.intf.write(0, self.loaded_data)

            self.log("Verifying written data...")
            verify_data = self.intf.read(0, MAIN_MEM_SIZE)

            if verify_data == self.loaded_data:
                info = (
                    f"✅ Write Operation Successful!\n\n"
                    f"Bytes written: {bytes_written}\n"
                    f"Verification: PASSED\n\n"
                    f"All data written and verified successfully."
                )

                QtWidgets.QMessageBox.information(self, "Write Successful", info)
                self.log(f"✅ Write completed: {bytes_written} bytes")
                self.log("✅ Verification PASSED")
                self.set_status(f"Write successful - {bytes_written} bytes")

                self.load_data_into_grid(verify_data, editable_source=True)
            else:
                diff_count = sum(
                    1 for i in range(len(verify_data))
                    if verify_data[i] != self.loaded_data[i]
                )

                info = (
                    f"⚠️ Write Verification Failed!\n\n"
                    f"Bytes written: {bytes_written}\n"
                    f"Differences found: {diff_count} bytes\n\n"
                    f"Possible reasons:\n"
                    f"• Some bytes are write-protected\n"
                    f"• Card was not unlocked\n"
                    f"• Write operation failed\n\n"
                    f"Check protection bits and PSC status."
                )

                QtWidgets.QMessageBox.warning(self, "Verification Failed", info)
                self.log(f"⚠️ Write verification FAILED: {diff_count} bytes differ")
                self.set_status(f"Write completed with errors")

        except Exception as e:
            self.handle_exception(e, "Write")

    def do_export_hex(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader from the Readers menu first."
            )
            self.log("Export failed: not connected")
            return

        try:
            self.log("Reading card data for export...")
            main_memory = self.intf.read(0, MAIN_MEM_SIZE)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            default_filename = f"sle4442_dump_{timestamp}.hex"

            filename, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export Card Data", default_filename,
                "HEX Files (*.hex *.txt);;All Files (*.*)"
            )

            if not filename:
                self.log("Export cancelled by user")
                return

            with open(filename, "w") as f:
                f.write(main_memory.hex().upper())

            self.log(f"Card data exported to: {filename}")
            self.set_status(f"Exported to {filename}")

            info = (
                f"✅ Card data successfully exported!\n\n"
                f"File: {filename}\n"
                f"Format: Raw HEX (512 characters)\n"
                f"Data: {len(main_memory)} bytes\n\n"
                f"SHA-256: {hashlib.sha256(main_memory).hexdigest()[:32]}...\n\n"
                f"The file can be imported and written to another card."
            )

            QtWidgets.QMessageBox.information(self, "Export Successful", info)

        except Exception as e:
            self.handle_exception(e, "Export")

    def do_unlock(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader first."
            )
            self.log("Unlock failed: not connected")
            return

        pin, ok = QtWidgets.QInputDialog.getText(
            self, "Unlock (PSC)",
            "Enter 3-byte PSC (6 hex digits, e.g. FFFFFF - common default):"
        )

        if not ok:
            return

        pin = pin.strip().replace(" ", "").upper()

        if len(pin) != 6 or not all(c in "0123456789ABCDEF" for c in pin):
            QtWidgets.QMessageBox.warning(
                self, "Invalid PIN",
                "PSC must be exactly 6 hex digits (0-9, A-F).\nExample: FFFFFF"
            )
            self.log("Unlock failed: invalid PSC format")
            return

        try:
            pin_bytes = bytes.fromhex(pin)
            self.log(f"Attempting unlock with PSC: {pin}")
            res = self.intf.unlock_with_pin_bytes(pin_bytes)

            if res == "unlocked":
                self.card_unlocked = True
                if self.grid_mode == "card":
                    for cell in self.byte_cells:
                        cell.setReadOnly(False)

            QtWidgets.QMessageBox.information(self, "Unlock Result", f"Result: {res}")
            self.set_status(f"Unlock result: {res}")
            self.log(f"Unlock result: {res}")
        except Exception as e:
            self.handle_exception(e, "Unlock")

    def do_change_pin(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader first."
            )
            self.log("Change PIN failed: not connected")
            return

        reader_info = self.intf.get_reader_info()
        is_omnikey = reader_info['is_omnikey']

        msg = (
            "⚠️ WARNING: Change PIN Operation\n\n"
            "You are about to change the card's PSC (PIN).\n"
            "This operation is PERMANENT and CANNOT be undone!\n\n"
        )

        if is_omnikey:
            msg += (
                "OMNIKEY Reader Detected:\n"
                "• You will need to provide BOTH old and new PSC\n"
                "• Card does NOT need to be unlocked first\n"
                "• Old PSC will be verified before change\n\n"
            )
        else:
            msg += (
                "Standard Reader:\n"
                "• Card MUST be unlocked with current PSC first\n"
                "• Only new PSC is required\n\n"
            )

        msg += (
            "Prerequisites:\n"
            "• New PSC will immediately replace old PSC\n"
            "• Make sure to remember the new PSC!\n\n"
            "⚠️ If you forget the new PSC, the card may become unusable!\n\n"
            "Do you want to continue?"
        )

        reply = QtWidgets.QMessageBox.warning(
            self, "Change PIN Warning", msg,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )

        if reply != QtWidgets.QMessageBox.Yes:
            self.log("Change PIN cancelled by user")
            return

        old_pin_bytes = None

        if is_omnikey:
            old_pin, ok = QtWidgets.QInputDialog.getText(
                self, "Change PIN - Old PSC",
                "Enter CURRENT 3-byte PSC (6 hex digits, e.g. FFFFFF):"
            )

            if not ok:
                return

            old_pin = old_pin.strip().replace(" ", "").upper()

            if len(old_pin) != 6 or not all(c in "0123456789ABCDEF" for c in old_pin):
                QtWidgets.QMessageBox.warning(
                    self, "Invalid PIN",
                    "Current PSC must be exactly 6 hex digits (0-9, A-F).\nExample: FFFFFF"
                )
                self.log("Change PIN failed: invalid old PSC format")
                return

            old_pin_bytes = bytes.fromhex(old_pin)
            self.log(f"Old PSC provided: {old_pin}")
        else:
            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setIcon(QtWidgets.QMessageBox.Warning)
            msg_box.setWindowTitle("Unlock Required")
            msg_box.setText("Card must be unlocked first")
            msg_box.setInformativeText(
                "Standard readers require the card to be unlocked "
                "with the current PSC before changing it.\n\n"
                "Would you like to unlock the card now?"
            )

            unlock_btn = msg_box.addButton("Unlock Card", QtWidgets.QMessageBox.ActionRole)
            continue_btn = msg_box.addButton("Continue (Already Unlocked)", QtWidgets.QMessageBox.AcceptRole)
            cancel_btn = msg_box.addButton(QtWidgets.QMessageBox.Cancel)

            msg_box.exec_()
            clicked = msg_box.clickedButton()

            if clicked == unlock_btn:
                self.do_unlock()
                retry = QtWidgets.QMessageBox.question(
                    self, "Continue?",
                    "Card unlock attempted. Do you want to continue with PIN change?",
                    QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
                )
                if retry != QtWidgets.QMessageBox.Yes:
                    return
            elif clicked == cancel_btn:
                self.log("Change PIN cancelled by user")
                return

        new_pin, ok = QtWidgets.QInputDialog.getText(
            self, "Change PIN - New PSC",
            "Enter NEW 3-byte PSC (6 hex digits, e.g. 123456):"
        )

        if not ok:
            return

        new_pin = new_pin.strip().replace(" ", "").upper()

        if len(new_pin) != 6 or not all(c in "0123456789ABCDEF" for c in new_pin):
            QtWidgets.QMessageBox.warning(
                self, "Invalid PIN",
                "New PSC must be exactly 6 hex digits (0-9, A-F).\nExample: 123456"
            )
            self.log("Change PIN failed: invalid new PSC format")
            return

        confirm_pin, ok = QtWidgets.QInputDialog.getText(
            self, "Confirm New PIN",
            "Re-enter NEW PSC to confirm:"
        )

        if not ok:
            return

        confirm_pin = confirm_pin.strip().replace(" ", "").upper()

        if new_pin != confirm_pin:
            QtWidgets.QMessageBox.critical(
                self, "PIN Mismatch",
                "The PINs you entered do not match!\n\nOperation cancelled for safety."
            )
            self.log("Change PIN cancelled: PIN mismatch")
            return

        try:
            new_pin_bytes = bytes.fromhex(new_pin)

            if is_omnikey:
                self.log(f"Attempting OMNIKEY PIN change: {old_pin} -> {new_pin}")
            else:
                self.log(f"Attempting standard PIN change to: {new_pin}")
                try:
                    sec_before = self.intf.read_security()
                    self.log(f"Current PSC: {sec_before[1:].hex().upper()}")
                except INSNotSupportedError:
                    self.log("Note: Reader doesn't support reading security memory")

            self.intf.change_pin(new_pin_bytes, old_pin_bytes)

            verification_supported = True
            try:
                sec_after = self.intf.read_security()
                self.log(f"New PSC: {sec_after[1:].hex().upper()}")
                verified = (sec_after[1:] == new_pin_bytes)
            except INSNotSupportedError:
                self.log("Note: Cannot verify PIN change - reader doesn't support reading security memory")
                verification_supported = False
                verified = True

            if verified:
                info = (
                    f"✅ PIN Changed Successfully!\n\n"
                    f"⚠️ IMPORTANT: Write down your new PSC!\n"
                    f"New PSC: {new_pin}\n\n"
                )

                if verification_supported:
                    info += f"Verified PSC: {sec_after[1:].hex().upper()}\n\n"
                else:
                    info += f"Note: Reader doesn't support verification by reading security memory.\n"
                    info += f"PIN change command succeeded (90 00 response).\n\n"

                if is_omnikey:
                    info += (
                        f"OMNIKEY reader used - PIN changed with authentication.\n"
                        f"Card may still be unlocked depending on reader behavior."
                    )
                else:
                    info += (
                        f"The card is now locked with the new PSC.\n"
                        f"You will need to unlock it again to write data."
                    )

                QtWidgets.QMessageBox.information(self, "PIN Changed", info)
                self.log("✅ PIN change successful" + (" and verified" if verification_supported else ""))
                self.set_status("PIN changed successfully")
            else:
                QtWidgets.QMessageBox.warning(
                    self, "Verification Failed",
                    "PIN change completed but verification failed.\n"
                    "Please check the security memory."
                )
                self.log("⚠️ PIN change verification failed")

        except Exception as e:
            self.handle_exception(e, "Change PIN")

    def show_card_info(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader first."
            )
            return

        try:
            self.log("Reading card information...")
            sec = self.intf.read_security()
            prot = self.intf.read_protection_bits()
            data = self.intf.read(0, MAIN_MEM_SIZE)
            reader_info = self.intf.get_reader_info()

            info = (
                f"Card Type: SLE4442\n"
                f"Main Memory: {MAIN_MEM_SIZE} bytes\n"
                f"Protection Bits: {PROT_BITS} bits\n\n"
                f"Security Memory: {sec.hex().upper()}\n"
                f"  Error Counter: 0x{sec[0]:02X} ({sec[0]} attempts left)\n"
                f"  PSC Bytes: {sec[1:].hex().upper()}\n\n"
                f"Protection Bits: {prot.hex().upper()}\n\n"
                f"Reader: {reader_info['name']}\n"
                f"Reader Type: {reader_info['type']}\n"
                f"Write APDU: {reader_info['write_apdu']}"
            )

            QtWidgets.QMessageBox.information(self, "Card Information", info)
            self.log("Card information displayed")
        except Exception as e:
            self.handle_exception(e, "Card information")

    def show_security_memory(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader first."
            )
            return

        try:
            self.log("Reading security memory...")
            sec = self.intf.read_security()

            info = (
                f"Security Memory (4 bytes):\n\n"
                f"Hex: {sec.hex().upper()}\n"
                f"Bytes: {list(sec)}\n\n"
                f"Error Counter: 0x{sec[0]:02X} ({sec[0]} attempts left)\n"
                f"  • 7 = unlocked\n"
                f"  • 0 = blocked (card locked permanently)\n\n"
                f"PSC (3-byte PIN):\n"
                f"  Byte 1: 0x{sec[1]:02X}\n"
                f"  Byte 2: 0x{sec[2]:02X}\n"
                f"  Byte 3: 0x{sec[3]:02X}\n"
                f"  Combined: {sec[1:].hex().upper()}\n"
            )

            QtWidgets.QMessageBox.information(self, "Security Memory", info)
            self.log("Security memory displayed")
        except Exception as e:
            self.handle_exception(e, "Security memory")

    def show_protection_bits(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader first."
            )
            return

        try:
            self.log("Reading protection bits...")
            prot = self.intf.read_protection_bits()

            bits = []
            for byte in prot:
                for i in range(8):
                    bits.append((byte >> i) & 1)

            info = (
                f"Protection Bits (32 bits):\n\n"
                f"Hex: {prot.hex().upper()}\n"
                f"Binary: {' '.join(f'{b:08b}' for b in prot)}\n\n"
                f"Bit = 1: Byte is writable\n"
                f"Bit = 0: Byte is write-protected\n\n"
            )

            protected_count = sum(1 for b in bits if b == 0)
            info += (
                f"Protected bytes: {protected_count}/32\n"
                f"Writable bytes: {32 - protected_count}/32\n"
            )

            QtWidgets.QMessageBox.information(self, "Protection Bits", info)
            self.log("Protection bits displayed")
        except Exception as e:
            self.handle_exception(e, "Protection bits")

    def do_send_raw_apdu(self):
        if not self.intf.hcard:
            QtWidgets.QMessageBox.warning(
                self, "Not Connected",
                "Please select a reader first."
            )
            self.log("Send APDU failed: not connected")
            return

        reader_info = self.intf.get_reader_info()

        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Send Raw APDU")
        dialog.setMinimumWidth(600)

        layout = QtWidgets.QVBoxLayout(dialog)

        info_text = (
            "Enter APDU command as hex bytes (space-separated or continuous)\n"
            "Example: FF B0 00 00 10  or  FFB0000010\n\n"
            f"Current Reader: {reader_info['name']}\n"
            f"Reader Type: {reader_info['type']}\n"
        )

        if reader_info['is_omnikey']:
            info_text += (
                f"Write APDU: {reader_info['write_apdu']} [ADDR] [LEN] [DATA...]\n"
                f"Change PIN: FF 21 00 00 06 [OLD_PSC 3 bytes] [NEW_PSC 3 bytes]\n\n"
            )
        else:
            info_text += "\n"

        info_text += (
            "Common APDUs:\n"
            "• Read memory: FF B0 [ADDR] [LEN]\n"
        )

        if reader_info['is_omnikey']:
            info_text += (
                "• Write memory: FF D6 [ADDR] [LEN] [DATA...]\n"
                "• Read protection: FF B0 01 00 04\n"
                "• Read security: FF B0 01 04 04\n"
                "• Change PIN: FF 21 00 00 06 [OLD PSC] [NEW PSC]\n"
            )
        else:
            info_text += (
                "• Write memory: FF D0 [ADDR] [LEN] [DATA...]\n"
                "• Read protection: FF B2 00 00 04\n"
                "• Read security: FF B2 01 00 04\n"
                "• Change PIN: FF D2 01 00 03 [NEW PSC 3 bytes] (must unlock first)\n"
            )

        info_text += (
            "• Unlock: FF 20 00 00 03 [PSC 3 bytes]"
        )

        info_label = QtWidgets.QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        apdu_label = QtWidgets.QLabel("APDU Command:")
        layout.addWidget(apdu_label)

        apdu_input = QtWidgets.QLineEdit()
        apdu_input.setFont(QtGui.QFont("Courier", 11))
        apdu_input.setPlaceholderText("FF B0 00 00 10")
        layout.addWidget(apdu_input)

        templates_label = QtWidgets.QLabel("Quick Templates:")
        layout.addWidget(templates_label)

        templates_layout = QtWidgets.QHBoxLayout()

        if reader_info['is_omnikey']:
            templates = [
                ("Read 256 bytes", "FF B0 00 00 FF"),
                ("Read Protection", "FF B0 01 00 04"),
                ("Read Security", "FF B0 01 04 04"),
                ("Write 1 byte", "FF D6 00 00 01 FF"),
                ("Change PIN", "FF 21 00 00 06 FFFFFF 123456"),
            ]
        else:
            templates = [
                ("Read 256 bytes", "FF B0 00 00 FF"),
                ("Read Protection", "FF B2 00 00 04"),
                ("Read Security", "FF B2 01 00 04"),
                ("Write 1 byte", "FF D0 00 00 01 FF"),
            ]

        for name, apdu in templates:
            btn = QtWidgets.QPushButton(name)
            btn.clicked.connect(lambda checked, a=apdu: apdu_input.setText(a))
            templates_layout.addWidget(btn)

        templates_layout.addStretch()
        layout.addLayout(templates_layout)

        response_label = QtWidgets.QLabel("Response (will appear after sending):")
        layout.addWidget(response_label)

        response_view = QtWidgets.QPlainTextEdit()
        response_view.setFont(QtGui.QFont("Courier", 10))
        response_view.setReadOnly(True)
        response_view.setMaximumHeight(150)
        layout.addWidget(response_view)

        button_layout = QtWidgets.QHBoxLayout()

        send_btn = QtWidgets.QPushButton("Send APDU")
        send_btn.setDefault(True)

        if self.current_theme != "xp":
            send_btn.setStyleSheet(
                "QPushButton { background-color: #4CAF50; color: white; "
                "font-weight: bold; padding: 5px 15px; }"
            )

        close_btn = QtWidgets.QPushButton("Close")

        button_layout.addStretch()
        button_layout.addWidget(send_btn)
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)

        close_btn.clicked.connect(dialog.accept)

        def send_apdu():
            apdu_str = apdu_input.text().strip().replace(" ", "").upper()

            if not apdu_str:
                QtWidgets.QMessageBox.warning(dialog, "Empty APDU", "Please enter an APDU command.")
                return

            if not all(c in "0123456789ABCDEF" for c in apdu_str):
                QtWidgets.QMessageBox.warning(
                    dialog, "Invalid APDU",
                    "APDU must contain only hex digits (0-9, A-F)."
                )
                return

            if len(apdu_str) % 2 != 0:
                QtWidgets.QMessageBox.warning(
                    dialog, "Invalid APDU",
                    "APDU must have an even number of hex digits."
                )
                return

            try:
                apdu_bytes = bytes.fromhex(apdu_str)
                apdu_list = list(apdu_bytes)

                self.log(f"Sending raw APDU: {format_apdu(apdu_list)}")

                if self.intf.log_apdus:
                    self.log(f">> APDU: {format_apdu(apdu_list)}")

                hresult, response = SCardTransmit(self.intf.hcard, self.intf.protocol, apdu_list)
                if hresult != SCARD_S_SUCCESS:
                    raise RuntimeError("Transmit failed: " + SCardGetErrorMessage(hresult))

                if self.intf.log_apdus:
                    self.log(f"<< RESP: {format_apdu(response)} ({len(response)} bytes)")

                response_text = f"Raw Response ({len(response)} bytes):\n"
                response_text += format_apdu(response) + "\n\n"

                if len(response) >= 2:
                    sw1, sw2 = response[-2], response[-1]
                    response_text += f"Status Words:\n"
                    response_text += f"  SW1: 0x{sw1:02X}\n"
                    response_text += f"  SW2: 0x{sw2:02X}\n"

                    if sw1 == 0x90 and sw2 == 0x00:
                        response_text += "  Status: SUCCESS ✅\n\n"
                    elif sw1 == 0x6D and sw2 == 0x00:
                        response_text += "  Status: INS NOT SUPPORTED ⚠️\n\n"
                    elif sw1 == 0x69 and sw2 == 0x86:
                        response_text += "  Status: COMMAND NOT ALLOWED 🔒\n"
                        response_text += "  (Security restriction / Card locked)\n\n"
                    elif sw1 == 0x69 and sw2 == 0x82:
                        response_text += "  Status: SECURITY NOT SATISFIED 🔒\n"
                        response_text += "  (Authentication required)\n\n"
                    else:
                        response_text += f"  Status: ERROR ⚠️\n\n"

                    if len(response) > 2:
                        data_bytes = response[:-2]
                        response_text += f"Data ({len(data_bytes)} bytes):\n"
                        response_text += format_apdu(data_bytes) + "\n\n"

                        if len(data_bytes) > 8:
                            response_text += "Hex Dump:\n"
                            response_text += hexdump(bytes(data_bytes)) + "\n\n"

                        ascii_repr = ''.join(
                            chr(b) if 32 <= b < 127 else '.'
                            for b in data_bytes
                        )
                        response_text += f"ASCII: {ascii_repr}\n"
                else:
                    response_text += "Invalid response (too short)\n"

                response_view.setPlainText(response_text)
                self.log(f"APDU response: {format_apdu(response)}")

            except Exception as e:
                error_msg = f"Error sending APDU:\n{str(e)}"
                response_view.setPlainText(error_msg)
                self.log(f"APDU error: {e}")
                QtWidgets.QMessageBox.critical(dialog, "APDU Error", error_msg)

        send_btn.clicked.connect(send_apdu)

        apdu_input.returnPressed.connect(send_apdu)

        dialog.exec_()

    def show_about(self):
        about_text = """SLE4442 Manager

A tool for reading and writing SLE4442 memory cards.

Features:
• Read main memory (256 bytes)
• Write to card memory
• Import/Export raw HEX format
• Read security memory
• Read protection bits
• Unlock with 3-byte PSC (PIN)
• Change PSC (PIN)
• Send raw APDU commands
• Multiple reader support
• APDU logging (optional)
• Full CLI support

⚠️ WARNING: Write and PIN change operations are permanent!
Always backup your cards before making changes."""
        QtWidgets.QMessageBox.about(self, "About SLE4442 Manager", about_text)

    def closeEvent(self, event):
        try:
            if self.intf.hcard:
                self.intf.disconnect()
                self.log("Disconnected from reader")
        except:
            pass
        event.accept()