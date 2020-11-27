from PyQt5 import QtCore,QtGui,QtWidgets
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


class SensorDataCanvas(FigureCanvas):

    def __init__(self):
        plt.style.use('ggplot')
        self.fig = Figure(figsize=(8,4), dpi=100)
        self.fig.subplots_adjust(left=0.15, bottom=0.2, right=0.95, top=0.95, hspace=0.2, wspace=0.2)
        #self.fig = Figure()
        self.ax = self.fig.add_subplot(111)
        FigureCanvas.__init__(self, self.fig)
        FigureCanvas.setSizePolicy(self, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        prefer_color = '#FFE882'
        self.ax.set_xlabel("Times", fontdict=dict(fontsize=16, fontweight='bold', color=prefer_color))
        self.ax.set_ylabel("Data", fontdict=dict(fontsize=16, fontweight='bold', color=prefer_color))

        #self.ax.legend()
        self.ax.set_ylim(-180, 180)
        self.ax.grid(True)
    
        self.curveObj = None

    def plot(self, datax, datay):
        if self.curveObj is None:
            self.curveObj, = self.ax.plot(np.array(datax), np.array(datay), 'o-', color='#DB6756')
        else:
            self.curveObj.set_data(np.array(datax), np.array(datay))
            try:
                self.ax.set_xlim(datax[0], datax[-1])
            except IndexError:
                pass
        self.draw()


    def clear(self):
        self.plot([],[])

    def set_ylim(self, low_bound, up_bound):
        self.ax.set_ylim(low_bound, up_bound)