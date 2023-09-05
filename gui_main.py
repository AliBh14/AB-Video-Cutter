import sys
import os
import ctypes
import time
import threading
import cv2
import tempfile
import shutil
import subprocess as sp
from utils import *
from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QGridLayout, QWidget, QVBoxLayout, QHBoxLayout, QMenu, QAction, QLineEdit, QTextEdit, QScrollArea, QPlainTextEdit, QFileDialog, QSpacerItem, QSizePolicy, QShortcut
from PyQt5.QtGui import QPixmap, QMovie, QKeySequence, QTextCursor
from PyQt5.QtCore import QByteArray, QUrl, QTemporaryDir
from PyQt5.QtMultimedia import QMediaContent, QMediaPlayer
from PyQt5.QtMultimediaWidgets import QVideoWidget
from pyqtspinner.spinner import WaitingSpinner
from pyqtspinner.spinner import WaitingSpinner
from moviepy.editor import *
from moviepy.config import get_setting
import range_slider

        
def thrd_cb_get_vid_frames(vidcap, frame_curr_index, save_dir):
    count = frame_curr_index
    while True:
        success, image = vidcap.read()
        if not success:
            break

        cv2.imwrite(save_dir + '/vid_frame_%d.jpg' % count, image) 
        count += 1
        
        
def thrd_cb_convert_frames(target_dir, current_dir, target_name, left_handle_val, right_handle_val, fps):
    target_clip = []

    for i in range(left_handle_val, right_handle_val+1):
        target_clip.append(ImageClip(current_dir + '/vid_frame_' + str(i) + '.jpg').set_duration(round(1/fps, 2)))

    concat_clip = concatenate_videoclips(target_clip, method = 'compose')
    
    audio_clip = AudioFileClip(current_dir + '/tmp_audio_cut.mp3')
    new_audio_clip = CompositeAudioClip([audio_clip])
    
    concat_clip = concat_clip.set_audio(new_audio_clip)
    
    concat_clip.write_videofile(target_dir + '/ab_cut_' + target_name, fps, logger = None)


class MainWindow(QMainWindow):
    
    def __init__(self):
        super().__init__()

        self.settings = QtCore.QSettings()
             
        try:
            self.vid_frames_path = self.settings.value('save_dir')
            shutil.rmtree(self.vid_frames_path)
        except:
            pass
        
        self.first_exec = True

        self.new_vid_w, self.new_vid_h, self.new_vid_frm_cnt, self.new_vid_fps = self.get_vid_info('cutter.gif')
        self.screen_size_w, self.screen_size_h = get_disp_size()
        
        self.mediaPlayer = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.videoWidget = QVideoWidget()
        self.videoWidget.setMaximumHeight(round(0.34*self.screen_size_h))
        self.videoWidget.setAspectRatioMode(QtCore.Qt.KeepAspectRatio)
        self.videoWidget.setStyleSheet("background-color:transparent;border-radius:1px")
        self.mediaPlayer.setVideoOutput(self.videoWidget)
        self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile('cutter.gif')))

        self.qp_tape_bottom = QPixmap('./tape.png')
        self.lbl_tape_bottom = QLabel(self)
        self.qp_tape_bottom = self.qp_tape_bottom.scaled(self.screen_size_w, 20)
        self.lbl_tape_bottom.setPixmap(self.qp_tape_bottom)

        self.qp_tape_top = QPixmap('./tape.png')
        self.lbl_tape_top = QLabel(self)
        self.qp_tape_top = self.qp_tape_top.scaled(self.screen_size_w, 20)
        self.lbl_tape_top.setPixmap(self.qp_tape_top)
        
        self.new_vid_frm_cnt = 255
        self.qslider = range_slider.RangeSlider(QtCore.Qt.Horizontal)
        self.qslider.setMinimumWidth(round(0.85*self.screen_size_w))
        self.qslider.setMinimum(0)
        self.qslider.setMaximum(int(self.new_vid_frm_cnt)-1)
        self.qslider.setLow(0)
        self.qslider.setHigh(int(self.new_vid_frm_cnt)-1)
        self.qs_prev_val_low = 0
        self.qs_prev_val_high = int(self.new_vid_frm_cnt)-1
        self.qslider.setTickPosition(QtWidgets.QSlider.TicksAbove)
        self.qslider.sliderMoved.connect(self.qslider_change_cb)
        self.qslider.setStyleSheet("background-color:black;")

        self.recent_qs = 'l'

        QShortcut(QKeySequence(QtCore.Qt.Key_Right), self, activated = self.move_qs_right)
        QShortcut(QKeySequence(QtCore.Qt.Key_Left), self, activated = self.move_qs_left)

        self.qle_t_1 = QLineEdit(self)
        self.qle_t_2 = QLineEdit(self)
        self.qle_t_1.setText('00:00:00:00')
        self.qle_t_1.installEventFilter(self)        
        self.qle_t_1.setFixedWidth(80)
        self.qle_t_1.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.qle_t_1.setEnabled(False)
        self.qle_t_2.setText(format_seconds(self.new_vid_frm_cnt/self.new_vid_fps))
        self.qle_t_2.setFixedWidth(80)
        self.qle_t_2.setAlignment(QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter)
        self.qle_t_2.setEnabled(False)
        self.qle_t_2.installEventFilter(self)

        self.qte_logger = QTextEdit(self)
        self.qte_logger.setPlainText('  For Development\n  _______________\n\n  Hurry up! Do Something! 💪')
        self.qte_logger.setReadOnly(True)
        self.qte_logger.setMinimumWidth(round((self.screen_size_w/2)-2*0.015*self.screen_size_w))
        self.qte_logger.setMinimumHeight(round(0.18*self.screen_size_h)) 
        self.font_logger = QtGui.QFont()
        self.font_logger.setPointSize(11)
        self.font_logger.setFamily('Courier New')
        self.qte_logger.setFont(self.font_logger)
        self.qte_logger.setStyleSheet('background-color: #EAEAEA; padding-top:20; padding-bottom:20; border: 1px solid rgb(65, 65, 65)')
        self.qte_logger.textChanged.connect(self.qte_move_cursor_to_end)
        self.qte_logger.ensureCursorVisible()

        self.qv_lyt = QVBoxLayout()

        self.qh_lyt_1 = QHBoxLayout()
        self.qh_lyt_2 = QHBoxLayout()
        self.qh_lyt_3 = QHBoxLayout()
        self.qh_lyt_tape_top_container = QHBoxLayout()
        self.qh_lyt_tape_bottom_container = QHBoxLayout()
        self.qh_lyt_logger = QHBoxLayout()
        self.qh_lyt_2.setContentsMargins(round(self.screen_size_w*0.025),round(self.screen_size_h/10)*0,round(self.screen_size_w*0.025),0)
        self.qh_lyt_3.setContentsMargins(round(0.015*self.screen_size_w),0,round(0.015*self.screen_size_w),0)
        self.qh_lyt_logger.setContentsMargins(round(0.015*self.screen_size_w), round(0.03*self.screen_size_w)*0, round(0.015*self.screen_size_w), round(0.015*self.screen_size_w))
        self.qv_lyt.addLayout(self.qh_lyt_1)
        self.qv_lyt.addLayout(self.qh_lyt_tape_top_container)
        self.qv_lyt.addLayout(self.qh_lyt_2)
        self.qv_lyt.addLayout(self.qh_lyt_tape_bottom_container)
        self.qv_lyt.addLayout(self.qh_lyt_3)
        self.qv_lyt.addLayout(self.qh_lyt_logger)
        self.qv_lyt.setContentsMargins(0,round(self.screen_size_h/25),0,0)
        self.qv_lyt.setSpacing(0)
        
        self.qh_lyt_1.addWidget(self.videoWidget, alignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        
        self.qh_lyt_3.addWidget(self.qle_t_1, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)
        self.qh_lyt_3.addWidget(self.qslider, alignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.qh_lyt_3.addWidget(self.qle_t_2, alignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)
        self.qh_lyt_tape_top_container.addWidget(self.lbl_tape_top, alignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignBottom)
        self.qh_lyt_tape_bottom_container.addWidget(self.lbl_tape_bottom, alignment = QtCore.Qt.AlignHCenter | QtCore.Qt.AlignTop)
        self.qh_lyt_logger.addWidget(self.qte_logger, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignBottom)
            
        self.qp_frame_holder = []
        self.lbl_frame_holder = []
        self.frame = cv2.imread('./tgd.jpg')
        self.frame_h, self.frame_w, c = self.frame.shape
        self.num_of_frames_qhl2 = round(0.9*self.screen_size_w*self.frame_h/(0.1*self.screen_size_h*self.frame_w))
        
        self.lbl_frame_holder_left = QLabel(self)
        self.qh_lyt_2.addWidget(self.lbl_frame_holder_left, alignment =  QtCore.Qt.AlignTop)
        self.lbl_frame_holder_left.setStyleSheet("background-color:black;")
        self.lbl_frame_holder_left.setFixedSize(round((0.9*self.screen_size_w-(self.num_of_frames_qhl2*0.1*self.screen_size_h*self.frame_w/self.frame_h)+2*self.screen_size_w*0.025)/self.num_of_frames_qhl2), round(0.1*self.screen_size_h)+5)
        
        for i in range(self.num_of_frames_qhl2):
            self.qp_frame_holder.append(QPixmap('./tgd.jpg'))
            self.lbl_frame_holder.append(QLabel(self))
            self.lbl_frame_holder[i].setObjectName('lbl_frame_holder' + str(i))
            self.qp_frame_holder[i] = self.qp_frame_holder[i].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
            self.lbl_frame_holder[i].setPixmap(self.qp_frame_holder[i])
            self.lbl_frame_holder[i].setMaximumHeight(round(0.1*self.screen_size_h)+5)
            self.qh_lyt_2.addWidget(self.lbl_frame_holder[i])
            self.lbl_frame_holder[i].setStyleSheet('background-color:black;')

        self.qh_lyt_2.setSpacing(0)

        self.qsa_segments = QScrollArea()
        self.qsa_segments.setStyleSheet('background-color: transparent; border: 0px')
        self.widget = QWidget()
        self.qsa_segments.setMinimumWidth(round((self.screen_size_w/2)-2*0.015*self.screen_size_w))
        self.qsa_segments.setFixedHeight(round(0.18*self.screen_size_h))
        self.qsa_segments.setAlignment(QtCore.Qt.AlignLeft)
        self.qv_lyt_segments = QVBoxLayout()

        self.qh_lyt_seg_0 = QHBoxLayout()

        self.seg_0 = QLabel('seg_0')
        self.qpp = QPixmap('./tgd.jpg')
        self.qpp = self.qpp.scaled(round(0.07*self.screen_size_h*self.frame_w/self.frame_h), round(0.07*self.screen_size_h))
        self.seg_0.setPixmap(self.qpp)
        self.qh_lyt_seg_0.addWidget(self.seg_0, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.qle_seg_0 = QLineEdit()
        self.qle_seg_0.setText('Segment 1')
        self.qle_seg_0.setFixedHeight(round(0.07*self.screen_size_h))
        self.qle_seg_0.setMaximumWidth(round(0.083*self.screen_size_h*self.frame_w/self.frame_h))
        self.qle_seg_0.setStyleSheet('padding-left:30;padding-right:30;font-weight: bold;font-family:\'Arial\';font-size:10pt;')
        self.qle_seg_0.setAlignment(QtCore.Qt.AlignVCenter)
        self.qh_lyt_seg_0.addWidget(self.qle_seg_0, alignment = QtCore.Qt.AlignVCenter)
        self.qh_lyt_seg_0.setSpacing(0)

        self.qs_seg_0 = range_slider.RangeSlider(QtCore.Qt.Horizontal)
        self.qs_seg_0.setMinimumWidth(round(0.255*self.screen_size_w))
        self.qs_seg_0.setMinimum(0)
        self.qs_seg_0.setMaximum(255)
        self.qs_seg_0.setLow(150)
        self.qs_seg_0.setHigh(255)
        self.qs_seg_0.setC(1);

        self.qh_lyt_seg_0.addWidget(self.qs_seg_0, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)

        self.qh_lyt_seg_1 = QHBoxLayout()
        self.qh_lyt_seg_1.setContentsMargins(0, 15, 0, 0)

        self.seg_1 = QLabel('seg_0')
        self.qp_seg_1 = QPixmap('./tgd.jpg')
        self.qp_seg_1 = self.qp_seg_1.scaled(round(0.07*self.screen_size_h*self.frame_w/self.frame_h), round(0.07*self.screen_size_h))
        self.seg_1.setPixmap(self.qp_seg_1)
        self.qh_lyt_seg_1.addWidget(self.seg_1, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignTop)

        self.qle_seg_1 = QLineEdit()
        self.qle_seg_1.setText('Segment 2')
        self.qle_seg_1.setFixedHeight(round(0.07*self.screen_size_h))
        self.qle_seg_1.setMaximumWidth(round(0.083*self.screen_size_h*self.frame_w/self.frame_h))
        self.qle_seg_1.setStyleSheet('padding-left:30;padding-right:30;font-weight: bold;font-family:\'Arial\';font-size:10pt;')
        self.qle_seg_1.setAlignment(QtCore.Qt.AlignVCenter)
        self.qh_lyt_seg_1.addWidget(self.qle_seg_1, alignment = QtCore.Qt.AlignVCenter)
        self.qh_lyt_seg_1.setSpacing(0)

        self.qs_seg_1 = range_slider.RangeSlider(QtCore.Qt.Horizontal)
        self.qs_seg_1.setMinimumWidth(round(0.255*self.screen_size_w))
        self.qs_seg_1.setMinimum(0)
        self.qs_seg_1.setMaximum(255)
        self.qs_seg_1.setLow(0)
        self.qs_seg_1.setHigh(120)
        self.qs_seg_1.setC(1);
        
        self.qh_lyt_seg_1.addWidget(self.qs_seg_1, alignment = QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter)
                
        self.qv_lyt_segments.addLayout(self.qh_lyt_seg_0)
        self.qv_lyt_segments.addLayout(self.qh_lyt_seg_1) 
        self.widget.setLayout(self.qv_lyt_segments)
        self.qsa_segments.setWidget(self.widget)

        self.qh_lyt_logger.addWidget(self.qsa_segments, alignment = QtCore.Qt.AlignRight | QtCore.Qt.AlignTop)

        self.centralwidget = QWidget(self)
        self.centralwidget.setObjectName(u"centralwidget")
        self.setCentralWidget(self.centralwidget)
        self.centralwidget.setLayout(self.qv_lyt)

        ############### Adding Menu Items ###############
        self.main_menu_bar = self.menuBar()
        self.menu_file = QMenu('File', self)
        self.main_menu_bar.addMenu(self.menu_file)
        
        ############### Adding Menu Items Actions ###############
        self.vid_load_action = QAction(self)
        self.vid_load_action.setText('Load Video File')
        self.menu_file.addAction(self.vid_load_action)
        self.vid_load_action.triggered.connect(self.select_vid_file)

        self.vid_export_action = QAction(self)
        self.vid_export_action.setText('Export')
        self.menu_file.addAction(self.vid_export_action)
        self.vid_export_action.triggered.connect(self.export_vid)

        self.mediaPlayer.play()

        self.setGeometry(0, 0, 0, 0)
        self.setWindowIcon(QtGui.QIcon('window_icon.jpg'))
        self.setWindowTitle("AB Video Cutter")
        self.showMaximized()


    def eventFilter(self, obj, event):
        if (obj == self.qle_t_1 or obj == self.qle_t_2) and event.type() == QtCore.QEvent.MouseButtonDblClick:
            pass
            
        return super(MainWindow, self).eventFilter(obj, event)

    def qte_move_cursor_to_end(self):
        self.qte_logger.moveCursor(QTextCursor.End, QTextCursor.MoveAnchor)

    def move_qs_right(self):
        if self.qslider.low() == self.qslider.maximum() or self.qslider.low() > self.qslider.high():
            return

        self.qp_frame_holder = []
        
        if self.recent_qs == 'l':
            self.qslider.setLow(self.qslider.low() + 1)
            self.qle_t_1.setText(format_seconds(self.qslider.low()/self.new_vid_fps))

            if 'selected' not in ('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1]):
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
            if 'Hurry up' in self.qte_logger.toPlainText() or 'Nothing to' in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText('  For Development\n_______________' + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
            elif 'Left Cursor on Frame Index' not in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))

            if self.first_exec:
                return
            
            qslider_low = self.qslider.low()
            
            for i in range(qslider_low, qslider_low + self.num_of_frames_qhl2):
                self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
                self.qp_frame_holder[i-qslider_low] = self.qp_frame_holder[i-qslider_low].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
                self.lbl_frame_holder[i-qslider_low].setPixmap(self.qp_frame_holder[i-qslider_low])
                
        elif self.recent_qs == 'h':
            if self.qslider.maximum() > self.qslider.high():
                self.qslider.setHigh(self.qslider.high() + 1)
            else:
                return
                
            self.qle_t_2.setText(format_seconds((self.qslider.high()+1)/self.new_vid_fps))

            if 'selected' not in ('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1]):
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
            if 'Hurry up' in self.qte_logger.toPlainText() or 'Nothing to' in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText('  For Development\n_______________' + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
            elif 'Left Cursor on Frame Index' not in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
            
            if self.first_exec:
                return
                        
            qslider_high = self.qslider.high()
            
            for i in range(qslider_high - self.num_of_frames_qhl2 + 1, qslider_high + 1):
                self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
                self.qp_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)] = self.qp_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
                self.lbl_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)].setPixmap(self.qp_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)])

    def move_qs_left(self):
        if self.qslider.high() == 0 or self.qslider.low() > self.qslider.high():
            return
            
        self.qp_frame_holder = []

        if 'selected' not in ('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1]):
            self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
            self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
        if 'Hurry up' in self.qte_logger.toPlainText() or 'Nothing to' in self.qte_logger.toPlainText():
            self.qte_logger.setPlainText('  For Development\n_______________' + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
        elif 'Left Cursor on Frame Index' not in self.qte_logger.toPlainText():
            self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
        
        if self.recent_qs == 'l':
            if self.qslider.minimum() < self.qslider.low():
                self.qslider.setLow(self.qslider.low() - 1)
            else:
                return
                
            self.qle_t_1.setText(format_seconds(self.qslider.low()/self.new_vid_fps))

            if 'selected' not in ('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1]):
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
            if 'Hurry up' in self.qte_logger.toPlainText() or 'Nothing to' in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText('  For Development\n_______________' + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
            elif 'Left Cursor on Frame Index' not in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))

            if self.first_exec:
                return
        
            qslider_low = self.qslider.low()
        
            for i in range(qslider_low, qslider_low + self.num_of_frames_qhl2):
                self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
                self.qp_frame_holder[i-qslider_low] = self.qp_frame_holder[i-qslider_low].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
                self.lbl_frame_holder[i-qslider_low].setPixmap(self.qp_frame_holder[i-qslider_low])
                
        elif self.recent_qs == 'h':
            self.qslider.setHigh(self.qslider.high() - 1)
            self.qle_t_2.setText(format_seconds(self.qslider.high()/self.new_vid_fps))

            if 'selected' not in ('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1]):
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
                self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
            if 'Hurry up' in self.qte_logger.toPlainText() or 'Nothing to' in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText('  For Development\n_______________' + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))
            elif 'Left Cursor on Frame Index' not in self.qte_logger.toPlainText():
                self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➥ Left Cursor on Frame Index ' + str(self.qslider.low()) + '\n\n  ➥ Right Cursor on Frame Index ' + str(self.qslider.high()))            
            
            if self.first_exec:
                return
        
            qslider_high = self.qslider.high()
            
            for i in range(qslider_high - self.num_of_frames_qhl2 + 1, qslider_high + 1):
                self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
                self.qp_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)] = self.qp_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
                self.lbl_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)].setPixmap(self.qp_frame_holder[i-(qslider_high - self.num_of_frames_qhl2 + 1)])


    def qslider_change_cb(self, low_value, high_value):
        
        self.qle_t_1.setText(format_seconds(low_value/self.new_vid_fps))
        self.qle_t_2.setText(format_seconds((high_value+1)/self.new_vid_fps))

        if 'selected' not in ('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1]):
            self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
            self.qte_logger.setPlainText(self.qte_logger.toPlainText().replace('\n\n' + self.qte_logger.toPlainText().split('\n\n')[-1], ''))
        if 'Hurry up' in self.qte_logger.toPlainText() or 'Nothing to' in self.qte_logger.toPlainText():
            self.qte_logger.setPlainText('  For Development\n_______________' + '\n\n  ➥ Left Cursor on Frame Index ' + str(low_value) + '\n\n  ➥ Right Cursor on Frame Index ' + str(high_value))
        elif 'Left Cursor on Frame Index' not in self.qte_logger.toPlainText():
            self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➥ Left Cursor on Frame Index ' + str(low_value) + '\n\n  ➥ Right Cursor on Frame Index ' + str(high_value))

        if self.qs_prev_val_low != low_value:

            self.recent_qs = 'l'
                    
            if self.first_exec:
                return

            self.qp_frame_holder = []
            
            for i in range(low_value, low_value + self.num_of_frames_qhl2):
                self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
                self.qp_frame_holder[i-low_value] = self.qp_frame_holder[i-low_value].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
                self.lbl_frame_holder[i-low_value].setPixmap(self.qp_frame_holder[i-low_value])

        if self.qs_prev_val_high != high_value:
            
            self.recent_qs = 'h'

            if self.first_exec:
                return

            self.qp_frame_holder = []

            for i in range(high_value - self.num_of_frames_qhl2 + 1, high_value + 1):
                self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
                self.qp_frame_holder[i-(high_value - self.num_of_frames_qhl2 + 1)] = self.qp_frame_holder[i-(high_value - self.num_of_frames_qhl2 + 1)].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
                self.lbl_frame_holder[i-(high_value - self.num_of_frames_qhl2 + 1)].setPixmap(self.qp_frame_holder[i-(high_value - self.num_of_frames_qhl2 + 1)])

        self.qs_prev_val_low = low_value
        self.qs_prev_val_high = high_value


    def get_vid_info(self, vid_dir):
        vid = cv2.VideoCapture(vid_dir)
        return vid.get(cv2.CAP_PROP_FRAME_WIDTH), vid.get(cv2.CAP_PROP_FRAME_HEIGHT), vid.get(cv2.CAP_PROP_FRAME_COUNT), vid.get(cv2.CAP_PROP_FPS)

    def get_vid_frames(self, vid_dir):
        self.tmp_dir = QTemporaryDir()
        self.tmp_dir.setAutoRemove(True)
        if self.tmp_dir.isValid():
            self.vid_frames_path = self.tmp_dir.path()
        else:
            self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➤ Wrong Path!')

        self.settings.setValue('save_dir', self.vid_frames_path)
            
        vidcap = cv2.VideoCapture(vid_dir)
        count = 0

        for i in range(self.num_of_frames_qhl2):
            success, image = vidcap.read()
            if not success:
                break
            cv2.imwrite(self.vid_frames_path + '/vid_frame_%d.jpg' % i, image) #save frame as JPEG file

        thrd_get_vid_frames = threading.Thread(target = thrd_cb_get_vid_frames, args = (vidcap, i, self.vid_frames_path,), daemon = True)    
        thrd_get_vid_frames.start()

        thrd_get_audio = threading.Thread(target = lambda: VideoFileClip(vid_dir).audio.write_audiofile(self.vid_frames_path + '/tmp_audio.mp3', logger = None))
        thrd_get_audio.start()
        
    def select_vid_file(self):
        self.selected_vid = QFileDialog.getOpenFileName(self, 'Select Video File', '',"video files (*.mp4 *.mov *.wmv *.mkv *.avi)")
        if self.selected_vid[0] == '':
            return

        self.first_exec = False

        self.qte_logger.setPlainText('  For Development\n  _______________' + '\n\n  ➤ ' + self.selected_vid[0] + ' selected!')

        self.new_vid_w, self.new_vid_h, self.new_vid_frm_cnt, self.new_vid_fps = self.get_vid_info(self.selected_vid[0])
        self.videoWidget.resize(round(0.34*self.screen_size_h*(self.new_vid_w/self.new_vid_h)), round(0.34*self.screen_size_h))
        self.mediaPlayer.setMedia(QMediaContent(QUrl.fromLocalFile(self.selected_vid[0])))
        time.sleep(0.5)
        self.videoWidget.show()
        self.mediaPlayer.pause()
        
        self.qle_t_2.setText(format_seconds((self.new_vid_frm_cnt-1)/self.new_vid_fps))

        self.qslider.setMinimum(0)
        self.qslider.setMaximum(int(self.new_vid_frm_cnt)-2)
        self.qslider.setLow(0)
        self.qslider.setHigh(int(self.new_vid_frm_cnt)-2)
        self.qs_prev_val_low = 0
        self.qs_prev_val_high = int(self.new_vid_frm_cnt)-2

        self.lbl_frame_holder_left.setParent(None)

        for i in range(self.num_of_frames_qhl2):
            self.lbl_frame_holder[i].setParent(None)

        self.frame_h, self.frame_w = self.new_vid_h, self.new_vid_w
        self.num_of_frames_qhl2 = round(0.9*self.screen_size_w*self.frame_h/(0.1*self.screen_size_h*self.frame_w))

        self.get_vid_frames(self.selected_vid[0])

        self.qp_frame_holder = []
        self.lbl_frame_holder = []

        self.qh_lyt_2.addWidget(self.lbl_frame_holder_left, alignment =  QtCore.Qt.AlignTop)
        self.lbl_frame_holder_left.setStyleSheet("background-color:black;")
        
        for i in range(self.num_of_frames_qhl2):
            self.qp_frame_holder.append(QPixmap(self.vid_frames_path + '/vid_frame_' + str(i) + '.jpg'))
            self.lbl_frame_holder.append(QLabel(self))
            self.qp_frame_holder[i] = self.qp_frame_holder[i].scaled(round(0.1*self.screen_size_h*self.frame_w/self.frame_h), round(0.1*self.screen_size_h)) 
            self.lbl_frame_holder[i].setPixmap(self.qp_frame_holder[i])
            self.lbl_frame_holder[i].setMaximumHeight(round(0.1*self.screen_size_h)+5)
            self.qh_lyt_2.addWidget(self.lbl_frame_holder[i])
            self.lbl_frame_holder[i].setStyleSheet('background-color:black;')


    def ffmpeg_extract_subclip(self, filename, t1, t2, targetname = None):
        name, ext = os.path.splitext(filename)
        if not targetname:
            T1, T2 = [int(1000*t) for t in [t1, t2]]
            targetname = "%sSUB%d_%d.%s" % (name, T1, T2, ext)

        cmd = [get_setting("FFMPEG_BINARY"),"-y",
               "-ss", "%0.2f"%t1,
               "-i", filename,
               "-t", "%0.2f"%(t2-t1),
               "-map", "0", "-vcodec", "copy", "-acodec", "copy", targetname]

        popen_params = {"stdout": sp.DEVNULL,
                "stderr": sp.PIPE,
                "stdin": sp.DEVNULL}

        if os.name == "nt":
            popen_params["creationflags"] = 0x08000000

        proc = sp.Popen(cmd, **popen_params)

        out, err = proc.communicate() # proc.wait()
        proc.stderr.close()

        del proc

    def export_vid(self):
        if self.first_exec == True:
            self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➤ Nothing to Export!')
            return

        target_dir = QFileDialog.getExistingDirectory(self, 'Select Folder')

        if target_dir == '':
            return

        self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➤ Export In Progress ...')
        QApplication.processEvents()
                
        thrd_get_audio = threading.Thread(target = lambda: self.ffmpeg_extract_subclip(self.vid_frames_path + '/tmp_audio.mp3', round(((self.qslider.low()+1)/self.new_vid_fps), 2), round(((self.qslider.high()+1)/self.new_vid_fps), 2), self.vid_frames_path + '/tmp_audio_cut.mp3'))
        thrd_get_audio.start()

        thrd_get_audio.join()
        
        thrd_convert_frames = threading.Thread(target = thrd_cb_convert_frames, args = (target_dir, self.vid_frames_path, self.selected_vid[0][self.selected_vid[0].rfind('/')+1:], self.qslider.low(), self.qslider.high(), self.new_vid_fps,), daemon = True)    
        thrd_convert_frames.start()
        
        thrd_convert_frames.join()
        
        self.qte_logger.setPlainText(self.qte_logger.toPlainText() + '\n\n  ➤ Export Finished!')

        
    def closeEvent(self, event):
        shutil.rmtree(self.vid_frames_path)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    QtCore.QCoreApplication.setOrganizationName('AB')
    QtCore.QCoreApplication.setOrganizationDomain('AB.AB')
    QtCore.QCoreApplication.setApplicationName('AB Video Cutter')
    window = MainWindow()
    sys.exit(app.exec_())
    
