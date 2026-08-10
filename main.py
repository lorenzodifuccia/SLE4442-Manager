#!/usr/bin/env python3
from card.CLI import *
from gui.qt import *

# PyQt GUI
if __name__ == "__main__":
    parser = build_cli_parser()
    args = parser.parse_args()

    # If a command is specified, run CLI mode
    if args.command: sys.exit(run_cli_with_args(args))

    # Otherwise, try to launch GUI
    if args.nogui or not HAS_QT:
        if not HAS_QT and not args.nogui:
            print("PyQt5 not available. Use CLI commands or install PyQt5 for GUI.")
            print("\nTry: python main.py --help")
        else:
            print("Use CLI commands. Try: python main.py --help")
        sys.exit(0)

    app = QtWidgets.QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())