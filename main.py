import sys
from PyQt5 import QtWidgets
from view import SchedulerView
from controller import SchedulerController

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")  # Style moderne
    view = SchedulerView()
    ctrl = SchedulerController(view)
    view.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
