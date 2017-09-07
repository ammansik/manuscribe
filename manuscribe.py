#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys,os
from PyQt4 import QtGui, QtCore
from PyQt4.phonon import Phonon
from time import sleep
import threading
import argparse
import chardet 
import locale

class AlignThread(QtCore.QThread):
    def __init__(self,main_window):
        QtCore.QThread.__init__(self)
        self.main_window = main_window
    
    def run(self):
        if self.main_window.trn_encoding['encoding'] == 'utf-8':
            editor_text = str(self.main_window.textedit.toPlainText().toUtf8())
            editor_text = editor_text.decode(encoding='utf-8') 
        else:
            editor_text = str(self.main_window.textedit.toPlainText().toLatin1()) 
            editor_text = editor_text.decode(encoding='iso-8859-15') 
        editor_text = editor_text.encode(encoding='utf-8')   
        wordsegs = self.convert2wordsegs(editor_text)  
        #Read in wordseg text  
        self.main_window.wordstarts = []
        self.main_window.wordends = []
        self.main_window.words = []
        for line in wordsegs:
            start,end,word = line.split(" ",3)
            self.main_window.wordstarts.append(int(float(start)))
            self.main_window.wordends.append(int(float(end)))
            self.main_window.words.append(word.strip())
        self.main_window.prev_words = self.main_window.words

    def mono2triphone(monophone_pron):
        triphone_pron = ""
        index = 0
        monophones = monophone_pron.split(" ")
        if len(monophones) == 1:
            triphone_pron = "_-"+monophones[0]+"+_"
        else:
            for phone in monophones:
                if index == 0:
                    triphone_pron += "_-"+phone+"+"+monophones[index+1]+" "
                elif index == len(monophones)-1:
                    triphone_pron += monophones[index-1]+"-"+phone+"+_"
                else:
                    triphone_pron += monophones[index-1]+"-"+phone+"+"+monophones[index+1]+" "
                index += 1
        return triphone_pron


    def convert2wordsegs(self,txt):
        if self.main_window.args['lang'] == "fi":
            #trn2mphn
            trn = txt
            words = txt.split(" ")
            mphn = ""
            mphn += "__\n"
            i = 0
            trn_len = len(trn.strip())
            while i < trn_len:
                a_ball_index = trn.find("å",i)
                a_prick_index = trn.find("ä",i)
                o_prick_index = trn.find("ö",i)
                if i == a_prick_index:
                    mphn += trn[i:i+2]+"\n"
                    i = i + 2    
                elif i == o_prick_index:
                    mphn += trn[i:i+2]+"\n"
                    i = i + 2
                elif i == a_ball_index:
                    mphn += "o\no\n"
                    i = i + 2
                else:
                    if trn[i] == "x":
                        mphn += "k\ns\n"
                    elif trn[i] == "z":
                        mphn += "t\ns\n"
                    elif trn[i] == "c":
                        mphn += "k\n"
                    elif trn[i] == "w":
                        mphn += "v\n"
                    elif trn[i] == "q":
                        mphn += "k\nv\n"
                    elif trn[i] == " ":
                        mphn += "_\n"
                    else:
                        mphn += trn[i]+"\n"
                    i = i+1
            mphn += "__"
            #mphn2phn
            monophones = []
            for line in mphn.split("\n"):
                phone = line.strip()
                if phone != "__":
                    monophones.append(phone)
            index = 0
            phn = open("temp.phn","w")  
            for phone in monophones:
                if index == 0:
                    triphone = "__\n_-"+phone+"+"+monophones[index+1]+"\n"
                elif index == len(monophones) - 1:
                    triphone = monophones[index-1]+"-"+phone+"+_\n__"
                else:
                    if phone == "_":
                        triphone = phone+"\n"
                    else:
                        triphone = monophones[index-1]+"-"+phone+"+"+monophones[index+1]+"\n"
                triphone = triphone.decode(encoding='utf-8')
                #Encode to same character set used by HMM
                phn.write(triphone.encode(encoding='ISO-8859-15'))
                index = index + 1
            phn.close()
        else:
            words = txt.split(" ")
            phn_file = open("temp.phn","w")
            phn_file.write("__\n")    
            index = 0
            for w in words:
                word = w.strip().decode('utf-8').encode('iso-8859-15')
                if word in self.main_window.eng_dict_word:
                    index = self.main_window.eng_dict_word.index(word)
                    tri_phones = self.main_window.eng_dict_pronunciation[index]
                    phonemes = tri_phones.split(" ")
                    for phone in phonemes:
                        phn_file.write(phone+"\n") 
                else:
                    oov_file = open("temp_oov.txt","w")
                    oov_file.write(w.strip().decode('utf-8').encode('iso-8859-15'))
                    oov_file.close()
                    os.system(self.main_window.args['g2p_path']+" --model "+self.main_window.args['pron_model']+" --variants-number=1 --apply temp_oov.txt > temp_oov.lex")
                    oov_pron_file = open("temp_oov.lex","r")
                    for line in oov_pron_file:
                        line = line.decode('iso-8859-15').encode('utf-8')
                        try:
                            word,number1,number2,mono_pron = line.split("\t")
                            tri_pron = mono2triphone(mono_pron.strip())
                            phonemes = tri_pron.split(" ")
                            for phone in phonemes:
                                phn_file.write(phone+"\n") 
                        except:
                            pass
                    #os.system("rm temp_oov.txt")
                    #os.system("rm temp_oov.lex")
                if index != len(words)-1:
                    phn_file.write("_\n")
                else:
                    pass
                index +=1
            phn_file.write("__\n")     
            phn_file.close() 
        #phn2seg
        current_path = os.getcwd()+"/"
        temp_recipe = open(current_path+"temp.recipe","w")
        temp_recipe.write("audio="+str(self.main_window.mediaObject.currentSource().fileName())+" transcript="+current_path+"temp.phn alignment="+current_path+"temp.seg")
        temp_recipe.close()
        os.system(self.main_window.args['align_path']+" -b "+self.main_window.args['hmm']+" -c "+self.main_window.args['hmm']+".cfg -r "+current_path+"temp.recipe")
        #seg2wordseg
        wsegs = []
        seg_file = open(current_path+"temp.seg","r")
        prev_phone = ""
        word_start = ""
        word_end = ""
        word = ""
        index = 0
        #Frequency
        f = self.main_window.frequency
        for line in seg_file:
            start,end,ph = line.split(" ",2)
            phone,seg_index = ph.split(".")
            if phone == "__":
                if index == (len(words)-1) and int(seg_index.strip()) == 2:
                    word_end = prev_end
                    word = words[index]
                    start_ms = str(round((float(word_start)/f)*1000,1))
                    end_ms = str(round((float(word_end)/f)*1000,1))
                    wsegs.append(start_ms+" "+end_ms+" "+word.strip())
            elif phone == "_":
                word_end = prev_end
                word = words[index]
                index = index + 1
                start_ms = str(round((float(word_start)/f)*1000,0))
                end_ms = str(round((float(word_end)/f)*1000,0))
                wsegs.append(start_ms+" "+end_ms+" "+word.strip())
            else:
                if prev_phone == "_" or prev_phone == "__":
                    word_start = start
                else: 
                    pass
            prev_start = start
            prev_end = end
            prev_phone = phone
        seg_file.close()
        #Remove temp files
        os.system("rm "+current_path+"temp.seg")
        os.system("rm "+current_path+"temp.recipe")
        os.system("rm "+current_path+"temp.phn")
        return wsegs
    
class Window(QtGui.QMainWindow):
    def __init__(self,args):
        super(Window, self).__init__()
        self.initUI()
        self.args = args
        #Read frequency from .cfg file
        cfg_file = open(self.args['hmm']+".cfg","r")
        self.frequency = 16000 #default value
        for line in cfg_file:
            param = line.strip()
            if param.startswith("sample_rate"):
                p,freq = param.split(" ")
                self.frequency = int(freq.strip())
                break
        cfg_file.close()
        if self.args['lang'] == 'en' or self.args['lang'] == 'swe':
            #English pronunciation dictionary
            tri_dict_file = open(self.args['lexicon'],"r")
            self.eng_dict_word = []
            self.eng_dict_pronunciation = []
            #Read vocabulary from dictionary
            for voc in tri_dict_file:
                word,pronunciation = voc.split("(1.0)")
                self.eng_dict_word.append(word.strip())
                self.eng_dict_pronunciation.append(pronunciation.strip())  
            tri_dict_file.close()

    def initUI(self):
        #Dummy widget
        self.mainWidget=QtGui.QWidget(self) 
        self.setCentralWidget(self.mainWidget)
      
        #Media object
        self.mediaObject = Phonon.MediaObject(self)
        self.audioOutput = Phonon.AudioOutput(Phonon.MusicCategory, self)
        self.mediaObject.setTickInterval(10)
        Phonon.createPath(self.mediaObject, self.audioOutput)
        self.connect(self.mediaObject, QtCore.SIGNAL("tick(qint64)"), self.tick)
        self.connect(self.mediaObject,QtCore.SIGNAL("totalTimeChanged(qint64)"),self.totalTimeChanged)
        self.connect(self.mediaObject,QtCore.SIGNAL("finished()"),self.finishedPlaying)
        self.current_pos = 0
        
        #Control buttons
        #self.btn_play = QtGui.QPushButton(QtGui.QIcon("play_icon.png"),"Play",self.mainWidget)
        #self.btn_pause = QtGui.QPushButton(QtGui.QIcon("pause_icon.png"),"Pause",self.mainWidget)
        #self.btn_stop = QtGui.QPushButton(QtGui.QIcon("stop_icon.png"),"Stop",self.mainWidget)
        self.btn_play = QtGui.QPushButton("Play",self.mainWidget)
        self.btn_pause = QtGui.QPushButton("Pause",self.mainWidget)
        self.btn_stop = QtGui.QPushButton("Stop",self.mainWidget)
        self.btn_play.clicked.connect(self.buttonClicked)            
        self.btn_pause.clicked.connect(self.buttonClicked)
        self.btn_stop.clicked.connect(self.buttonClicked)
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
       
        self.btn_align = QtGui.QPushButton("Align", self.mainWidget)
        self.btn_align.clicked.connect(self.startAligning)
        self.btn_align.setEnabled(False)

        self.audio_select_next = QtGui.QPushButton("Next",self.mainWidget)
        self.audio_select_prev = QtGui.QPushButton("Prev",self.mainWidget)
        self.audio_select_next.clicked.connect(self.buttonClicked)       
        self.audio_select_prev.clicked.connect(self.buttonClicked)      
        self.audio_select_next.setEnabled(False)
        self.audio_select_prev.setEnabled(False)

        #Custom seek slider
        self.custom_slider = QtGui.QSlider(QtCore.Qt.Horizontal, self.mainWidget)       
        self.connect(self.mediaObject, QtCore.SIGNAL("tick(qint64)"),self.sliderUpdate)
        self.connect(self.custom_slider,QtCore.SIGNAL("sliderMoved(int)"),self.sliderMoved)
        self.connect(self.custom_slider,QtCore.SIGNAL("sliderPressed()"),self.sliderPressed)
        self.connect(self.custom_slider,QtCore.SIGNAL("sliderReleased()"),self.sliderReleased)

        self.custom_slider.setEnabled(False)
        self.wasPlaying = False

        #Text area
        self.textedit = QtGui.QTextEdit(self.mainWidget)
        self.textedit.setEnabled(False)
        self.vbar = self.textedit.verticalScrollBar()
        self.connect(self.vbar,QtCore.SIGNAL("valueChanged(int)"),self.scrollBarChanged)
        self.current_vbar_value = 0

        #Menu bar
        self.exitAction = QtGui.QAction('&Exit', self)        
        self.exitAction.triggered.connect(QtGui.qApp.quit)
        self.openAudioFileAction = QtGui.QAction('&Open Audio file', self)        
        self.openAudioFileAction.triggered.connect(self.audioFileSelection)
        self.openRecipeFileAction = QtGui.QAction('&Open Recipe file', self)        
        self.openRecipeFileAction.triggered.connect(self.recipeFileSelection)
        self.openTrnFileAction = QtGui.QAction('&Open Transcription file', self)
        self.openTrnFileAction.triggered.connect(self.trnFileSelection)
        self.openTrnFileAction.setEnabled(False)  
        self.saveTrnFileAction = QtGui.QAction('Save Transcription File',self)
        self.saveTrnFileAction.triggered.connect(self.trnSaveFile)
        self.saveTrnFileAction.setEnabled(False)
        self.saveAsTrnFileAction = QtGui.QAction('Save Transcription File As...',self)
        self.saveAsTrnFileAction.triggered.connect(self.trnSaveFileAs)
        self.saveAsTrnFileAction.setEnabled(False) 
        self.current_path = os.getcwd() 

        self.menubar = self.menuBar()
        self.fileMenu = self.menubar.addMenu('&File')
        self.fileMenu.addAction(self.openAudioFileAction)
        self.fileMenu.addAction(self.openRecipeFileAction)
        self.fileMenu.addAction(self.openTrnFileAction)
        self.fileMenu.addAction(self.saveTrnFileAction)
        self.fileMenu.addAction(self.saveAsTrnFileAction)
        self.fileMenu.addAction(self.exitAction)

        #Status bar
        self.statusBar().showMessage(self.tr("Ready"))

        #Audio selector
        self.audioSelector = QtGui.QComboBox(self.mainWidget)
        self.connect(self.audioSelector,QtCore.SIGNAL("currentIndexChanged(int)"), self.updateAudioSelection)
        self.audioSelector.setEnabled(False)
        self.audioSelector.setFixedWidth(400)
        self.audioFileLabel = QtGui.QLabel("File:")
        self.audioFileLabel.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignCenter)


        #Align thread
        self.align_thread = AlignThread(self)
        self.connect(self.align_thread,QtCore.SIGNAL("finished()"),self.finishedAligning)

               
        #Transcriptions
        self.current_trn_index = 0
        self.trn_texts = []
        self.trn_file_ids = []
        self.html_header = "<html><head></head><body><font size=\"8\">"
        self.html_end = "</font></body></html>"
        self.words = []
        self.prev_words = []
        self.wordstarts = []
        self.wordends = []

        #Audio files
        self.current_audio_index = 0
        self.audio_files = []
        self.audio_file_ids = []
  
        #Alignment files
        self.current_alignment_index = 0
        self.alignment_files = [] 
        self.alignment_file_ids = []
 
        #Playback Box Layout
        self.hboxPlayback = QtGui.QHBoxLayout()
        self.hboxPlayback.addWidget(self.btn_play)
        self.hboxPlayback.addWidget(self.btn_pause)
        self.hboxPlayback.addWidget(self.btn_stop)
        self.hboxPlayback.addStretch(0)
 
        #Grid Layout
        self.grid = QtGui.QGridLayout()
        self.grid.addWidget(self.textedit,0,0,1,7)
        self.grid.addWidget(self.custom_slider,1,0,1,7)
        self.grid.addWidget(self.btn_align,3,0,1,1)
        self.grid.addLayout(self.hboxPlayback,3,2,1,2)
        self.grid.addWidget(self.audioFileLabel,3,5,1,1)
        self.grid.addWidget(self.audioSelector,3,6,1,-1)

        self.grid.addWidget(self.audio_select_prev,2,6,1,1)
        self.grid.addWidget(self.audio_select_next,4,6,1,1)

        #Main Window
        self.mainWidget.setLayout(self.grid)
        self.statusBar()
        self.setGeometry(300, 300, 840, 480)
        self.setWindowTitle('Manual Speech Transcription Tool')
        self.show()
        
    def buttonClicked(self):
        sender = self.sender()
        if self.mediaObject.state() != Phonon.PlayingState:
            if sender.text() == "Play":
                self.mediaObject.seek(self.current_pos)
                self.mediaObject.play()
                self.btn_align.setEnabled(False)
                self.audioSelector.setEnabled(False)
                self.wasPlaying = True
            elif sender.text() == "Next":
                self.audioSelector.setCurrentIndex(self.current_trn_index+1)
                #self.updateAudioSelection(self.current_trn_index+1)
            elif sender.text() == "Prev":
                self.audioSelector.setCurrentIndex(self.current_trn_index-1)  
                #self.updateAudioSelection(self.current_trn_index-1)
        else:
            if sender.text() == "Pause":
                self.mediaObject.pause()
                self.btn_align.setEnabled(True)
                self.audioSelector.setEnabled(True)
                self.wasPlaying = False
            elif sender.text() == "Stop":
                self.mediaObject.stop()
                self.btn_align.setEnabled(True)
                self.audioSelector.setEnabled(True)
                self.wasPlaying = False

    def updateAudioSelection(self,new_index):
        if new_index >= 0 and self.audioSelector.isEnabled() == True:
            #Save current transcritption
            if self.trn_encoding['encoding'] == 'utf-8':
                self.trn_texts[self.current_trn_index] = self.textedit.toPlainText().toUtf8()
                self.trn_texts[self.current_trn_index] = str(self.trn_texts[self.current_trn_index]).decode(encoding = self.trn_encoding['encoding'])
            else:
                self.trn_texts[self.current_trn_index] = self.textedit.toPlainText().toLatin1() 
                self.trn_texts[self.current_trn_index] = str(self.trn_texts[self.current_trn_index])
            self.trnSaveFile()
            self.current_trn_index = new_index
            self.current_audio_index = self.audio_file_ids.index(self.trn_file_ids[self.current_trn_index])
            #Load audio
            self.mediaObject.setCurrentSource(Phonon.MediaSource(self.audio_files[self.current_audio_index]))
            #Load transcription
            self.textedit.setText(QtCore.QString(self.html_header+self.trn_texts[self.current_trn_index]+self.html_end))
            self.textedit.setEnabled(False)
            self.btn_play.setEnabled(False)
            self.btn_pause.setEnabled(False)
            self.btn_stop.setEnabled(False)
            self.custom_slider.setEnabled(False)
            self.btn_align.setEnabled(True)
            self.statusBar().showMessage(self.tr("Loaded audio file: "+str  (self.current_audio_index+1)+" out of "+str(len(self.audio_files))))
            if self.current_trn_index < (len(self.trn_file_ids)-1):
                self.audio_select_next.setEnabled(True)
            else:
                self.audio_select_next.setEnabled(False)
            if self.current_trn_index > 0:
                self.audio_select_prev.setEnabled(True)  
            else:
                self.audio_select_prev.setEnabled(False)  

            #Update alignment
            if self.alignment_files[self.current_audio_index] != "null":
                current_alignment_file = self.alignment_files[self.current_audio_index]
                self.alignment2words(current_alignment_file)
                self.btn_play.setEnabled(True)
                self.btn_pause.setEnabled(True)
                self.btn_stop.setEnabled(True)
                self.custom_slider.setEnabled(True)
                self.textedit.setEnabled(True)
                self.btn_align.setEnabled(True)
                self.audioSelector.setEnabled(True)      

    def audioFileSelection(self):
        path = QtGui.QFileDialog.getOpenFileName(self,"Open audio file",self.current_path,"Audio (*.wav *.raw)")
        if path:
            #Clear Text area and variables
            self.audio_files = []
            self.audio_file_ids = []
            self.trn_texts = []
            self.trn_file_ids = []
            self.audioSelector.clear()
            self.audioSelector.setEnabled(False)
            self.textedit.clear()
            self.textedit.setEnabled(False)
            #Extract file_id
            self.audio_files.append(str(path))
            dir_path,base_name = str(path).rsplit("/",1)
            self.current_path = dir_path
            base_name,pos = base_name.rsplit(".",1)
            self.audio_file_ids.append(base_name)
            #Open audio file
            self.current_audio_index = 0    
            self.mediaObject.setCurrentSource(Phonon.MediaSource(self.audio_files[self.current_audio_index]))
            self.openTrnFileAction.setEnabled(True)
            self.statusBar().showMessage(self.tr("Loaded audio file: "+str  (self.current_audio_index+1)+" out of "+str(len(self.audio_files))))
            
    def recipeFileSelection(self):
        path = QtGui.QFileDialog.getOpenFileName(self,"Open recipe file",self.current_path,"Recipe (*.recipe)")
        if path:
            self.current_path = os.path.dirname(str(path))
            #Clear Text area and variables
            self.audio_files = []
            self.audio_file_ids = []
            self.trn_texts = []
            self.trn_file_ids = []
            self.alignment_files = [] 
            self.alignment_file_ids = []
            self.audioSelector.clear()
            self.audioSelector.setEnabled(False)
            self.textedit.clear()
            self.textedit.setEnabled(False)
            #Load recipe
            recipe = open(path,"r")
            for line in recipe:
                recipe_encoding = chardet.detect(line)
                if recipe_encoding['encoding'] == 'utf-8':
                    line = line.decode(encoding = recipe_encoding['encoding'])
                line = line.strip()
                fields = line.split(" ")
                for f in fields:
                    f = f.strip()
                    #Check for audio file
                    if f.startswith("audio="):
                        filename = f.replace("audio=","")
                        dir_path,base_name = filename.rsplit("/",1)
                        base_name,pos = base_name.rsplit(".",1)
                        self.audio_files.append(filename)
                        self.audio_file_ids.append(base_name)
                        if line.find("alignment=") == -1:
                            self.alignment_files.append("null")
                            self.alignment_file_ids.append(base_name)
                    #Check if alignment file is available
                    elif f.startswith("alignment="):
                        filename = f.replace("alignment=","")
                        dir_path,base_name = filename.rsplit("/",1)
                        base_name,pos = base_name.rsplit(".",1)
                        self.alignment_files.append(filename)
                        self.alignment_file_ids.append(base_name)                     
            #Open first audio file in recipe
            self.current_audio_index = 0    
            self.mediaObject.setCurrentSource(Phonon.MediaSource(self.audio_files[self.current_audio_index]))
            self.openTrnFileAction.setEnabled(True)
            self.statusBar().showMessage(self.tr("Loaded audio file: "+str  (self.current_audio_index+1)+" out of "+str(len(self.audio_files))))
            recipe.close()


    def trnFileSelection(self):
        path = QtGui.QFileDialog.getOpenFileName(self,'Open transcription file',self.current_path,"Text files (*.txt *.trn)")
        if path:
            self.current_path = os.path.dirname(str(path))
            #Clear variables
            self.trn_texts = []
            self.trn_file_ids = []
            id_texts = []
            #Load text into editor
            text_file = open(path,"r")
            self.current_trn_file = path
            index = 0
            for line in text_file:
                trn = line.strip()
                if index == 0:
                    self.trn_encoding = chardet.detect(trn)
                if self.trn_encoding['encoding'] == 'utf-8':
                    trn = trn.decode(encoding = self.trn_encoding['encoding'])
                words = trn.split(" ")
                trn_text = ""
                for w in words:
                    if w.startswith("("):
                        trn_file_id = w.lstrip("(").rstrip(")")
                        self.trn_file_ids.append(trn_file_id)
                    else:
                        trn_text += w+" "              
                trn_text = trn_text.strip()
                self.trn_texts.append(trn_text)
                id_texts.append((trn_file_id,trn_text))
                '''
                try:
                    if self.audio_file_ids.index(self.trn_file_ids[index]) >= 0:
                        self.audioSelector.addItem(self.trn_file_ids[index])
                except:
                    pass
                '''
                index += 1
            #Sort the ids and trn texts
            id_texts.sort()
            self.trn_texts = []
            self.trn_file_ids = []
            index = 0
            for id_text in id_texts:
                trn_file_id = id_text[0]
                trn_text = id_text[1]
                self.trn_texts.append(trn_text)
                self.trn_file_ids.append(trn_file_id)
                try:
                    if self.audio_file_ids.index(self.trn_file_ids[index]) >= 0:
                        self.audioSelector.addItem(self.trn_file_ids[index])
                except:
                    pass
                index += 1  
 
            
            #Check current audio file
            self.current_trn_index = 0
            #self.current_audio_index = self.audio_file_ids.index(self.trn_file_ids[self.current_trn_index])   
            self.current_trn_index = self.trn_file_ids.index(self.audio_file_ids[self.current_audio_index])      
            self.mediaObject.setCurrentSource(Phonon.MediaSource(self.audio_files[self.current_audio_index]))        
            self.textedit.setText(QtCore.QString(self.html_header+self.trn_texts[self.current_trn_index]+self.html_end)) 
            #Check if alignment file exists
            if self.alignment_files[self.current_audio_index] != "null":
                current_alignment_file = self.alignment_files[self.current_audio_index]
                self.alignment2words(current_alignment_file)
                self.btn_play.setEnabled(True)
                self.btn_pause.setEnabled(True)
                self.btn_stop.setEnabled(True)
                self.custom_slider.setEnabled(True)
                self.textedit.setEnabled(True)
                self.btn_align.setEnabled(True)
                self.audioSelector.setEnabled(True)
            
            self.btn_align.setEnabled(True)
            self.saveTrnFileAction.setEnabled(True)
            self.saveAsTrnFileAction.setEnabled(True)
            self.audioSelector.setEnabled(True)

            if self.current_trn_index < (len(self.trn_file_ids)-1):
                self.audio_select_next.setEnabled(True)
            else:
                self.audio_select_next.setEnabled(False)
            if self.current_trn_index > 0:
                self.audio_select_prev.setEnabled(True)  
            else:
                self.audio_select_prev.setEnabled(False) 

            self.statusBar().showMessage(self.tr("Loaded audio file:  "+str  (self.current_audio_index+1)+" out of "+str(len(self.audio_files))))
            #self.statusBar().showMessage(self.tr("Loaded transcription file "+path))
            text_file.close()

    def trnSaveFile(self):
        text_file = open(self.current_trn_file,"w")
        if self.trn_encoding['encoding'] == 'utf-8':
            self.trn_texts[self.current_trn_index] = self.textedit.toPlainText().toUtf8()
        else:
            self.trn_texts[self.current_trn_index] = self.textedit.toPlainText().toLatin1()            
        trn_text = ""
        index = 0
        for trn in self.trn_texts:
            if index == self.current_trn_index:
                if self.trn_encoding['encoding'] == 'utf-8': 
                    trn_text += str(trn)+" ("+self.trn_file_ids[index].encode(encoding='utf-8')+")"
                else:
                    trn_text += str(trn)+" ("+self.trn_file_ids[index]+")"
            else:
                if self.trn_encoding['encoding'] == 'utf-8':
                    trn_text += trn.encode(encoding='utf-8')+" ("+self.trn_file_ids[index].encode(encoding='utf-8')+")"
                else:
                    trn_text += trn+" ("+self.trn_file_ids[index]+")"               
     
            trn_text += "\n"
            index += 1
        text_file.write(trn_text)     
        text_file.close()

        #self.statusBar().showMessage(self.tr("Saved transcription file "+self.current_path))
        if self.trn_encoding['encoding'] == 'utf-8':
            self.trn_texts[self.current_trn_index] = str(self.trn_texts[self.current_trn_index]).decode(encoding = self.trn_encoding['encoding'])
        else:
            self.trn_texts[self.current_trn_index] = str(self.trn_texts[self.current_trn_index])

    def trnSaveFileAs(self):
        path = QtGui.QFileDialog.getSaveFileName(self,'Save transcription file as',self.current_path,"Text files (*.txt *.trn)")
        if path:
            self.current_path = os.path.dirname(str(path))
            text_file = open(path,"w")
            if self.trn_encoding['encoding'] == 'utf-8':
                self.trn_texts[self.current_trn_index] = self.textedit.toPlainText().toUtf8()
            else:
                self.trn_texts[self.current_trn_index] = self.textedit.toPlainText().toLatin1()            
            trn_text = ""
            index = 0
            for trn in self.trn_texts:
                if index == self.current_trn_index:
                    if self.trn_encoding['encoding'] == 'utf-8': 
                        trn_text += str(trn)+" ("+self.trn_file_ids[index].encode(encoding='utf-8')+")"
                    else:
                        trn_text += str(trn)+" ("+self.trn_file_ids[index]+")"
                else:
                    if self.trn_encoding['encoding'] == 'utf-8':
                        trn_text += trn.encode(encoding='utf-8')+" ("+self.trn_file_ids[index].encode(encoding='utf-8')+")"
                    else:
                        trn_text += trn+" ("+self.trn_file_ids[index]+")"               

                trn_text += "\n"
                index += 1
            text_file.write(trn_text)     
            text_file.close()
            #self.statusBar().showMessage(self.tr("Saved transcription file as "+path))
            if self.trn_encoding['encoding'] == 'utf-8':
                self.trn_texts[self.current_trn_index] = str(self.trn_texts[self.current_trn_index]).decode(encoding = self.trn_encoding['encoding'])
            else:
                self.trn_texts[self.current_trn_index] = str(self.trn_texts[self.current_trn_index])      

    def disableButtons(self):
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.custom_slider.setEnabled(False)
        self.textedit.setEnabled(False)
        self.btn_align.setEnabled(False)
        self.audioSelector.setEnabled(False)
  
    def startAligning(self):
        self.align_thread.start()
        self.btn_play.setEnabled(False)
        self.btn_pause.setEnabled(False)
        self.btn_stop.setEnabled(False)
        self.custom_slider.setEnabled(False)
        self.textedit.setEnabled(False)
        self.btn_align.setEnabled(False)
        self.audioSelector.setEnabled(False)
        self.statusBar().showMessage(self.tr("Aligning "+str(self.current_audio_index+1)+" out of "+str(len(self.audio_files))+" ..please wait"))

    def finishedAligning(self):
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.custom_slider.setEnabled(True)
        self.textedit.setEnabled(True)
        self.btn_align.setEnabled(True)
        self.audioSelector.setEnabled(True)
        #self.trnSaveFile()
        self.statusBar().showMessage(self.tr("Aligned audio file: "+str  (self.current_audio_index+1)+" out of "+str(len(self.audio_files))))

    def finishedPlaying(self):
        self.btn_play.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.btn_stop.setEnabled(True)
        self.custom_slider.setEnabled(True)
        self.textedit.setEnabled(True)
        self.btn_align.setEnabled(True)
        self.audioSelector.setEnabled(True)
        #self.trnSaveFile()
        self.statusBar().showMessage(self.tr("Played audio file: "+str  (self.current_audio_index+1)+" out of "+str(len(self.audio_files))))

    def tick(self,time):
        try:
            editor_text = str(self.textedit.toPlainText().toLatin1())            
            self.words= []
            for w in editor_text.split(" "):
                word = w.strip()
                if len(word) == 0:
                    pass
                else:
                    self.words.append(w.strip())
            if len(self.words) != len(self.prev_words):           
                if len(self.words) > len(self.prev_words):
                    index = 0
                    word_diff = len(self.words) - len(self.prev_words)
                    for w in self.prev_words:
                        if w != self.words[index]:
                            for i in range(index,index+word_diff):
                                self.wordstarts.insert(i,self.wordstarts[i])
                                self.wordends.insert(i,self.wordends[i])
                            break
                        index += 1
                else:
                    index = 0
                    word_diff =  len(self.prev_words) - len(self.words)
                    for w in self.prev_words:
                        if w != self.words[index]:
                            for i in range(index,index+word_diff):
                                self.wordstarts.pop(i)
                                self.wordends.pop(i)
                            break
                        index += 1
            if len(self.words) > 0:
                index = 0
                self.trn_text = ""
                for word in self.words:
                    if time >= self.wordstarts[index] and time <= self.wordends[index]:
                        self.trn_text +="<font color=red>"+word.strip()+"</font> "
                    else:
                        self.trn_text += word.strip()+" " 
                    index += 1
                prev_vbar_value = self.current_vbar_value
                self.trn_text = self.trn_text.strip()
                self.trn_text = self.html_header+self.trn_text+self.html_end
                self.textedit.setText(QtCore.QString(self.trn_text))
                self.vbar.setSliderPosition(prev_vbar_value)
            self.current_pos = time
            self.prev_words = self.words
        except:
            pass     
    
    def sliderUpdate(self,time):
        self.custom_slider.setValue(time)

    def sliderPressed(self):
        self.mediaObject.pause()
        self.btn_align.setEnabled(True)

    def sliderReleased(self):
        if self.wasPlaying:
            self.mediaObject.seek(self.current_pos)
            self.mediaObject.play()
            self.btn_align.setEnabled(False)

    def sliderMoved(self,pos):
        editor_text = str(self.textedit.toPlainText().toLatin1()) 
        self.words= []
        for w in editor_text.split(" "):
            word = w.strip()
            if len(word) == 0:
                pass
            else:
                self.words.append(w.strip())
        if len(self.words) != len(self.prev_words):           
            if len(self.words) > len(self.prev_words):
                index = 0
                word_diff = len(self.words) - len(self.prev_words)
                for w in self.prev_words:
                    if w != self.words[index]:
                        for i in range(index,index+word_diff):
                            self.wordstarts.insert(i,self.wordstarts[i])
                            self.wordends.insert(i,self.wordends[i])
                        break
                    index += 1
            else:
                index = 0
                word_diff =  len(self.prev_words) - len(self.words)
                for w in self.prev_words:
                    if w != self.words[index]:
                        for i in range(index,index+word_diff):
                            self.wordstarts.pop(i)
                            self.wordends.pop(i)
                        break
                    index += 1
        if len(self.words) > 0:
            index = 0
            self.trn_text = ""
            for word in self.words:
                if pos >= self.wordstarts[index] and pos < self.wordends[index]:
                    self.trn_text +="<font color=red>"+word.strip()+"</font> "
                else:
                    self.trn_text += word.strip()+" " 
                index += 1  
            self.trn_text = self.trn_text.strip()
            self.trn_text = self.html_header+self.trn_text+self.html_end
            self.textedit.setText(QtCore.QString(self.trn_text))
        self.current_pos = pos  
        self.prev_words = self.words       

    def totalTimeChanged(self,changedTime):
        self.custom_slider.setRange(0,self.mediaObject.totalTime())  

    def scrollBarChanged(self,new_value):
        self.current_vbar_value = new_value

    def alignment2words(self,alignment_file):
        if self.trn_encoding['encoding'] == 'utf-8':
            editor_text = str(self.textedit.toPlainText().toUtf8())
            editor_text = editor_text.decode(encoding='utf-8') 
        else:
            editor_text = str(self.textedit.toPlainText().toLatin1()) 
            editor_text = editor_text.decode(encoding='iso-8859-15') 
        editor_text = editor_text.encode(encoding='utf-8')  
        words = []
        for w in editor_text.split(" "):
            w = w.strip()
            if len(w) > 0:
                words.append(w)

        seg_file = open(alignment_file,"r")
        wsegs = []
        index = 0
        f = self.frequency
        for line in seg_file:
            start,end,ph = line.split(" ",2)
            phone,seg_index = ph.split(".")
            if phone == "__":
                if index == (len(words)-1) and int(seg_index.strip()) == 2:
                    word_end = prev_end
                    word = words[index]
                    start_ms = str(round((float(word_start)/f)*1000,1))
                    end_ms = str(round((float(word_end)/f)*1000,1))
                    wsegs.append(start_ms+" "+end_ms+" "+word.strip())
            elif phone == "_":
                word_end = prev_end
                word = words[index]
                index = index + 1
                start_ms = str(round((float(word_start)/f)*1000,0))
                end_ms = str(round((float(word_end)/f)*1000,0))
                wsegs.append(start_ms+" "+end_ms+" "+word.strip())
            else:
                if prev_phone == "_" or prev_phone == "__":
                    word_start = start
                else: 
                    pass
            prev_start = start
            prev_end = end
            prev_phone = phone
        seg_file.close()

        self.wordstarts = []
        self.wordends = []
        self.words = []
        for line in wsegs:
            start,end,word = line.split(" ",3)
            self.wordstarts.append(int(float(start)))
            self.wordends.append(int(float(end)))
            self.words.append(word.strip())
        self.prev_words = self.words
    

def make_unicode(text_input):
    text_input = text_input.decode('ISO-8859-15')
    return text_input.encode('utf-8')


        
def main():    
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Phonon')
    parser = argparse.ArgumentParser(description='Manuscribe')
    parser.add_argument('--lang',dest='lang',type=str,help='Language (fi|en|swe)',choices=['fi','en','swe'],required=True)
    parser.add_argument('--align-path',dest='align_path',type=str,help='Path to the aku align command',required=True)
    parser.add_argument('--hmm',dest='hmm',type=str,help='Acoustic model base name',required=True)
    parser.add_argument('--lexicon',dest='lexicon',type=str,help='Lexicon (for English)')
    parser.add_argument('--pron-model',dest='pron_model',type=str,help='G2P pronunciation model for OOV words (for English)')
    parser.add_argument('--g2p-path',dest='g2p_path',type=str,help='Path to Sequitur G2P (for English)')
    args = vars(parser.parse_args())
    if args['lang']=='en' or args['lang'] == 'swe':
        if args['lexicon'] == None:
            parser.print_usage()
            print "manuscribe.py: error: argument --lexicon is required"
            sys.exit()
        elif args['pron_model'] == None:
            parser.print_usage()
            print "manuscribe.py: error: argument --pron-model is required"
            sys.exit()
        elif args['g2p_path'] == None:
            parser.print_usage()
            print "manuscribe.py: error: argument --g2p-path is required"
            sys.exit()
        else:
	    pass        
    ex = Window(args)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
