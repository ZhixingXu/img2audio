# -*- coding: utf-8 -*-

from glob import glob
import cv2
from matplotlib import pyplot
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from sympy import finite_diff_weights
from uidesigner import Ui_MainWindow
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox, QGraphicsScene, QPushButton
import sys
import time
import numpy as np
import re
import img2audio_core as ac
import wave
import matplotlib
import pyaudio
import threading

matplotlib.use("Qt5Agg")

pyplot.rcParams['font.sans-serif'] = ['SimHei']
pyplot.rcParams['axes.unicode_minus'] = False

finished = True
data_pointer=0
fig_handle=None
data_to_plot=None
timer = QtCore.QTimer()
# timer.setInterval(100)

class MyFigure(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # # 1、创建一个绘制窗口Figure对象
        # self.fig = Figure(figsize=(width,height),dpi=dpi)
        # # 2、在父类中激活Figure窗口,同时继承父类属性
        # super(MyFigure, self).__init__(self.fig)
        # -------
        # 创建一个Figure，注意：该Figure为matplotlib下的figure，不是matplotlib.pyplot下面的figure
        self.fig = Figure(figsize=(width, height), dpi=100)

        FigureCanvasQTAgg.__init__(self, self.fig)  # 初始化父类
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        # self.axes.set_facecolor('gray')
        # self.fig.patch.set_facecolor('gray')
        # self.fig.patch.set_alpha(1)
        self.fig.subplots_adjust(left=0.08, bottom=0.1, right=0.98, top=0.95,hspace=0.1,wspace=0.1)
        # 调用figure下面的add_subplot方法，类似于matplotlib.pyplot下面的subplot方法

    def updata_plot(self,x,y):
        self.axes.clear()
        # self.axes = self.fig.add_subplot(111)
        self.axes.plot(x,y)
        # self.axes.ylim(-0x7fff,0x7fff)
        self.fig.canvas.draw() # 这里注意是画布重绘，self.figs.canvas
        self.fig.canvas.flush_events() # 画布刷新self.figs.canvas

    def specgram(self,data,NFFT=2048,fs=16000):
        
        self.axes.clear()
        # self.axes = self.fig.add_subplot(111)
        self.axes.specgram(data,NFFT,fs)
        self.fig.canvas.draw() # 这里注意是画布重绘，self.figs.canvas
    
    def show_pic(self,data):
        self.axes.axis('off')
        self.axes.imshow(data)
        self.fig.canvas.draw() # 这里注意是画布重绘，self.figs.canvas
        self.fig.canvas.flush_events() # 画布刷新self.figs.canvas

class ImgDisp(QMainWindow,Ui_MainWindow):
    def __init__(self,parent=None):
        super(ImgDisp,self).__init__(parent)
        self.setupUi(self)
          
        self.btn_export.clicked.connect(self.btn_export_pressed)
        self.btn_play.clicked.connect(self.btn_play_pressed)
        self.textinput_pic.returnPressed.connect(self.show_picture)

        self.scene_wave = QGraphicsScene()  # 创建场景
        self.F1 = MyFigure(width=self.graphicsview_plot.width()//100, height=self.graphicsview_plot.height()//100, dpi=500)
        self.scene_wave.addWidget(self.F1)  # 将图形元素添加到场景中
        self.graphicsview_plot.setScene(self.scene_wave)  # 将创建添加到图形视图显示窗口
        # ------------------------------------------------------------------------------------------------
        self.scene_pic = QGraphicsScene()  # 创建场景
        # print('>>>{},{}'.format(self.graphicsview_pic.width(),self.graphicsview_pic.height()))
        self.F2 = MyFigure(width=self.graphicsview_pic.width()//100*0.9, height=self.graphicsview_pic.height()//100*0.9, dpi=500)
        self.F2.axes.axis('off')
        self.scene_pic.addWidget(self.F2)  # 将图形元素添加到场景中
        self.graphicsview_pic.setScene(self.scene_pic)

    def show_picture(self):
        img_path=self.textinput_pic.text()
            
        if None==re.match('.*\.(png|jpg)',img_path):
            QMessageBox.critical(self, "Error", "You should input a path to picture whose format is jpg or png!")
            return
        pic_data=cv2.imread(img_path)
        if pic_data is None:
            QMessageBox.critical(self, "Error", "You should input a path to picture whose format is jpg or png!")
            return
        self.F2.show_pic(pic_data)
        # self.graphicsview_pic.
        ...

    def btn_export_pressed(self,a):
        test=0
        if test:
            fs=400
            n=np.arange(1000)
            x=np.sin(2*np.pi*15*n/fs)

            self.F1.updata_plot(n,x)

            print("btn pressed")
            print('---',self.textinput_audio.text())
        else:
            print("shapae:",self.audio_out.shape)
            if self.audio_out is not None:
                try:
                    if ac.audio_export(self.audio_out):
                        # QMessageBox.critical(self, "Success", "\'output.wav\' has been experted")
                        QMessageBox.information(self, "Success", "\'output.wav\' has been experted")
                except:
                    QMessageBox.critical(self, "Error", "expert error!Probably because \'output.wav\' is occupied")

                self.audio_out=None

    def btn_play_pressed(self,a):
        global finished
        global data_pointer
        global fig_handle
        global data_to_plot
        global timer
        if finished==False:
            return
        finished=False
        test=0
        if test:
            print("btn2 pressed in")
            fs=400
            n=np.arange(100)
            x=np.sin(2*np.pi*30*n/fs)

            for i in range(10000):
                x=np.r_[x[1:],x[0]+np.random.randn(1)]
                self.F1.updata_plot(n,x)
                time.sleep(0.02)

            print("btn2 pressed")
        else:
            img_path=self.textinput_pic.text()
            aud_path=self.textinput_audio.text()
            if None==re.match('.*\.(png|jpg)',img_path):
                QMessageBox.critical(self, "Error", "You should input a path to picture whose format is jpg or png!")
                return
            aud_data=None
            try:
                fp       = wave.Wave_read(aud_path)
                aud_data     = fp.readframes(fp.getnframes())
                aud_data     = np.frombuffer(aud_data, dtype='short')
            except:
                print("no audio for phase specgram")

            pic_data=cv2.imread(img_path)
            # self.F2.show_pic(pic_data)
            self.audio_out=ac.generate_audio(pic_data,aud_data)
            # --------------------------
            data_to_plot=self.audio_out.copy()
            fig_handle=self.F1
            timer.timeout.connect(plot_process)
            # ----------------------------
            thread1=threading.Thread(target=play_audio,args=(data_to_plot,self.F1))
            thread1.setDaemon(True)
            thread1.start()
            timer.start(100)

def play_audio(data:np.ndarray,fig):
    global data_pointer
    global fig_handle
    global finished
    global timer
    ac.audio_play(data)
    print("finished playing audio")
    finished=True
    fig_handle=None
    data_pointer=0
    timer.stop()

def plot_process():
    global data_pointer
    fig_handle.updata_plot(np.arange(data_pointer,data_pointer+16000)/16000,data_to_plot[data_pointer:data_pointer+16000])
    data_pointer+=1600
    # print('timer:',data_pointer)

# def plot_audio(data:np.ndarray,fig):
#     global data_pointer
#     global fig_handle
#     global data_to_plot
#     global timer
#     data_to_plot=data.copy()
#     fig_handle=fig
#     timer.timeout.connect(plot_process)
#     timer.start(100)
#     print("timer.start()")
#     while finished == False:
#         continue
            
            
            


if __name__=='__main__':
    app=QApplication(sys.argv)
    ui=ImgDisp()
    ui.show()
    sys.exit(app.exec_())
