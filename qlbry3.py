#!/usr/bin/python3
from lbry_test2 import*
from PySide2.QtWidgets import *
from PySide2.QtGui import*
from PySide2.QtCore import*
from PySide2 import QtGui
from PySide2.QtMultimedia import *
from PySide2.QtMultimediaWidgets import *
from PySide2.QtMultimediaWidgets import *
import urllib
import sys
import _thread as thread
import numpy as np
import os
import asyncio
import qasync

def nothing(*args):
	pass

class DownloadImageThread(QThread):
	#thread that downloads an image and returns a pixmap
	pixmap=Signal(QPixmap)
	def __init__(self,img_url,parent=None):
		super().__init__(parent)
		self.img_url=img_url
	def run(self):
		pm=QPixmap()
		try:
			pm.loadFromData(urllib.request.urlopen(self.img_url).read())
		except:
			pass
		self.pixmap.emit(pm)

class FunctionAsQThread(QThread):
	function_complete=Signal(tuple)
	def __init__(self,function,*args,parent=None):
		super().__init__(parent)
		self.function=function
		self.args=args
	def run(self):
		try:
			result=(self.function(*self.args),)
		except Exception as e:
			result=(e,)
		self.function_complete.emit(result)

class IteratorAsQThread(QThread):
	iterate=Signal(tuple)
	def __init__(self,function,*args,parent=None):
		super().__init__(parent)
		print("PARENT:",self.parent())
		self.function=function
		self.args=args
		self.is_running=False
	def run(self):
		self.is_running=True
		for item in self.function(*self.args):
			if self.is_running:
				self.iterate.emit((item,))
			else:
				break
		
class NotAFunction:
	def __init__(self,function,*params):
		self.function=function
		self.params=params
	def __call__(self):
		return self.function(*self.params)

class SearchResultWidget(QPushButton):
	def __init__(self,claim,parent=None,minimum_width=700,minimum_height=110):
		self.claim=claim
		super().__init__(parent)
		self.setMinimumHeight(minimum_height)
		self.setMinimumWidth(minimum_width)
		self.threaded_init()
	def purge(self):
		self.thread.quit()
		self.thread.wait()
		self.deleteLater()
	
	def add_image(self,pm):
		#pm=pm.scaledToWidth(100)
		#pm=pm.scaledToHeight(100)
		self.img.setPixmap(pm)
		pm_size=pm.size()
		pm_size.scale(100,100,Qt.AspectRatioMode.KeepAspectRatio)
		self.img.setMaximumSize(pm_size)
	
	def threaded_init(self):
		#layout containing thumbnail and text
		#print(self.claim.__dict__)
		h_layout=QHBoxLayout()
		h_layout.setAlignment(Qt.AlignLeft)
		
		#image
		try:
			img_url=self.claim["value"]["thumbnail"]['url']
			self.thread=DownloadImageThread(img_url,parent=self)
			self.thread.pixmap.connect(self.add_image)
			self.thread.start()
		except:
			#no image for now. lool
			pass
		self.img=QLabel(self)
		self.img.setScaledContents(True)
		h_layout.addWidget(self.img)
		
		#layout for text elements (content title, channel name, etc)
		self.txt_layout_widget=QWidget(self)
		txt_layout=QVBoxLayout()
		
		#content title
		self.title_label=QLabel(self)
		self.title_label.setText(self.claim["value"]["title"])
		txt_layout.addWidget(self.title_label)
		
		#channel title
		if self.claim["value_type"]!="channel":
			try:
				self.channel_label=QLabel(self)
				self.channel_label.setText(self.claim["signing_channel"]["value"]["title"])
				txt_layout.addWidget(self.channel_label)
			except:
				#this keeps giving recursion errors, ugh
				pass
		
		#add stuff together
		self.txt_layout_widget.setLayout(txt_layout)
		h_layout.addWidget(self.txt_layout_widget)
		self.setLayout(h_layout)
		
class StreamPlayerWidget(QWidget):
	def __init__(self,*args,autoplay=False):
		if len(args)>1:
			#first arg is parent, second is claim
			parent=args[0]
			self.claim=args[1]
			super().__init__(parent)
		else:
			self.claim=args[0]
			super().__init__()
		self.claim.get()
		self.playing=False
		#vertical layout including player and transport controls container
		v_layout=QGridLayout()
		
		#stream player widget, be it audio or video
		if self.claim["value"]["stream_type"]=="video":
			#video stream
			print("VIDEO STREAM DETECTED")
			self.player_widget=QVideoWidget(self)
			self.player_widget.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
			self.player=QMediaPlayer(None,QMediaPlayer.VideoSurface)
			self.player.setVideoOutput(self.player_widget)
			v_layout.addWidget(self.player_widget,0,0)
			self.stream_info=self.claim["value"]["video"]
		elif self.claim["value"]["stream_type"]=="audio":
			#audio not yet supported
			self.player=QMediaPlayer(None)
			self.stream_info=self.claim["value"]["audio"]
			pass
		self.player.positionChanged.connect(self.position_changed)
		self.player.durationChanged.connect(self.duration_changed)
		self.player.setMedia(QMediaContent(QUrl(self.claim["streaming_url"])))
		self.player.setNotifyInterval(100)
		#container widget for transport controls
		self.transport=QWidget(self)
		transport_layout=QHBoxLayout()
		self.playpause_button=QPushButton(self.transport)
		self.playpause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
		self.playpause_button.clicked.connect(self.play_or_pause)
		transport_layout.addWidget(self.playpause_button)
		self.pos_slider=QSlider(Qt.Horizontal,parent=self.transport)
		self.pos_slider.setRange(0,self.stream_info["duration"])
		transport_layout.addWidget(self.pos_slider)
		self.transport.setLayout(transport_layout)
		
		#add everything together
		v_layout.addWidget(self.transport,1,0)
		self.setLayout(v_layout)
		self.playing=False
		self.media_set=False
		self.pos_to_go_to=-1
		self.current_pos=0
		if autoplay:
			self.play_or_pause()
			
		
	def position_changed(self,pos):
		if self.playing:
			self.current_pos=pos
		try:
			if not self.pos_slider.isSliderDown():
				if self.pos_to_go_to==-1:
					self.pos_slider.setValue(pos/1000)
					self.pos_to_go_to=-1
				else:
					#set position of player
					self.player.setPosition(self.pos_to_go_to)
					self.pos_to_go_to=-1
			else:
				self.pos_to_go_to=self.pos_slider.value()*1000
		except AttributeError:
			pass
	def duration_changed(self,*args):
		pass
	def play_or_pause(self,*args):
		if self.playing:
			self.playing=False
			self.player.pause()
			self.playpause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
		else:
			print(self.player.position())
			self.player.play()
			#self.player.setPosition(self.current_pos)
			self.playing=True
			self.playpause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
		
class ChannelWidget(QWidget):
	claim_selected=Signal(Claim)
	def __init__(self,channel,parent=None):
		super().__init__(parent)
		self.channel=channel
		main_vbox=QVBoxLayout()
		#main box will have a content widget (will contain all claims in channel)
		
		#this will contain channel picture, banner, title, etc
		self.header=QWidget(self)
		header_layout=QHBoxLayout()
		
		#channel image
		self.channel_img=QLabel(self)
		self.channel_img.setScaledContents(True)
		#do a threaded image download like the others
		img_url=self.channel["value"]["thumbnail"]["url"]
		self.c_img_thread=DownloadImageThread(img_url,parent=self)
		self.c_img_thread.pixmap.connect(self.add_c_image)
		self.c_img_thread.finished.connect(nothing)
		self.c_img_thread.start()
		header_layout.addWidget(self.channel_img)
		
		#text containing channel title
		self.title_text=QLabel(self)
		self.title_text.setText(self.channel["value"]["title"])
		header_layout.addWidget(self.title_text)
		self.header.setLayout(header_layout)
		
		#footer, might have a tab system eventually
		self.footer=QWidget(self)
		footer_layout=QVBoxLayout()
		
		self.claim_list=QWidget()
		self.claim_list.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Expanding)
		self.claim_list_layout=QVBoxLayout()
		self.claim_list.setLayout(self.claim_list_layout)
		footer_layout.addWidget(self.claim_list)
		self.footer.setLayout(footer_layout)
		
		#add everything
		main_vbox.addWidget(self.header)
		main_vbox.addWidget(self.footer)
		self.setLayout(main_vbox)
		self.load_claims()
	def load_claims(self):
		self.claim_search_thread=IteratorAsQThread(self.channel.channel_claims,parent=self)
		self.claim_search_thread.iterate.connect(self.render_claim)
		self.claim_search_thread.start()
	def add_c_image(self,pm):
		self.channel_img.setPixmap(pm)
		pm_size=pm.size()
		pm_size.scale(100,100,Qt.AspectRatioMode.KeepAspectRatio)
		self.channel_img.setMaximumSize(pm_size)
	
	def render_claim(self,claim):
		claim_to_add,=claim
		cw=SearchResultWidget(claim_to_add,parent=self)
		cw.setSizePolicy(QSizePolicy.Maximum,QSizePolicy.Expanding)
		cw.clicked.connect(NotAFunction(self.claim_selected.emit,claim_to_add))
		self.claim_list_layout.addWidget(cw)
	def purge(self):
		self.claim_search_thread.quit()
		self.claim_search_thread.wait()
		self.c_image_thread.quit()
		self.c_image_thread.wait()
		self.deleteLater()
		
class LBRYClient(QMainWindow):
	def __init__(self,lbrynet):
		super().__init__()
		self.lbry=lbrynet
		self.setWindowTitle("qlbry")
		self.initialize_main_widgets()

	def initialize_main_widgets(self):
		self.main_container=QWidget(self)
		self.setCentralWidget(self.main_container)
		main_container_layout=QGridLayout()
		#search bar
		self.nav_bar=QWidget(self)
		nav_bar_layout=QGridLayout()
		self.search_field=QLineEdit(self)
		self.search_field.returnPressed.connect(self.search)
		self.search_button=QPushButton(self)
		self.search_button.setText("search")
		self.search_button.clicked.connect(self.search)
		nav_bar_layout.addWidget(self.search_field,0,0)
		nav_bar_layout.addWidget(self.search_button,0,1)
		self.nav_bar.setLayout(nav_bar_layout)
		
		#lower area
		self.content_area=QScrollArea()
		self.content_area.setWidgetResizable(True)
		
		#add everything together
		main_container_layout.addWidget(self.nav_bar,0,0)
		main_container_layout.addWidget(self.content_area,1,0)
		self.main_container.setLayout(main_container_layout)
	def clean_up_widgets(self):
		#clean up any widgets and threads from earlier tasks
		try:
			self.search_thread.is_running=False
			self.search_thread.wait()
		except AttributeError:
			pass
		try:
			self.current_channel.purge()
		except AttributeError:
			pass
		except RuntimeError:
			pass
		try:
			self.result_widgets[1]
			for w in self.result_widgets:
				try:
					w.purge()
				except:
					pass
			self.result_widgets=[]
		except AttributeError:
			pass
		except IndexError:
			pass
		try:
			self.claim_container.deleteLater()
		except AttributeError:
			pass
		except RuntimeError:
			pass
		try:
			self.stream_player.player.pause()
			self.stream_player.delete_later()
		except AttributeError:
			pass
		except RuntimeError:
			pass
		try:
			self.content_area_container.deleteLater()
		except AttributeError:
			pass
		except RuntimeError:
			pass
	def search(self):
		self.clean_up_widgets()
		
		#Initialize widgets used to display search results
		self.content_area_container=QWidget()
		self.content_area_layout=QGridLayout()
		self.content_area_container.setLayout(self.content_area_layout)
		self.content_area.setWidget(self.content_area_container)
		self.result_widgets=[]
		
		#start the search thread
		self.current_query=self.search_field.text()
		self.search_thread=IteratorAsQThread(self.threaded_search,self.current_query,parent=self)
		self.search_thread.iterate.connect(self.render_search_results)
		self.search_thread.start()
	def threaded_search(self,query):
		print("started search")
		#do actual searching
		for claim in self.lbry.search_continuously(query):
			yield claim
		print("end search")
	def render_search_results(self,claim,*args):
		claim,=claim
		try:
			w=SearchResultWidget(claim,self.content_area_container)
			w.clicked.connect(NotAFunction(self.navigate_to_claim,claim))
			self.result_widgets.append(w)
			self.content_area_layout.addWidget(w)
		except KeyError:
			pass
	def navigate_to_claim(self,*args):
		claim=args[0]
		self.clean_up_widgets()
		self.claim_container=QWidget()
		claim_container_layout=QGridLayout()
		if claim["value_type"]=="stream":
			#audio or video
			self.stream_player=StreamPlayerWidget(claim)
			self.stream_player.setSizePolicy(QSizePolicy.Minimum,QSizePolicy.Expanding)
			claim_container_layout.addWidget(self.stream_player,0,0)
			stream_title_label=QLabel(self.claim_container)
			stream_title_label.setText(claim["value"]["title"])
			claim_container_layout.addWidget(stream_title_label,1,0)
		elif claim["value_type"]=="channel":
			#probably channel, i think
			self.current_channel=ChannelWidget(claim)
			self.current_channel.claim_selected.connect(self.navigate_to_claim)
			claim_container_layout.addWidget(self.current_channel,0,0)
			#print(claim.__dict__)
			pass
		self.claim_container.setLayout(claim_container_layout)
		self.content_area.setWidget(self.claim_container)
		self.claim_container.show()

async def main():
	running = True
	def stop_running():
		nonlocal running
		running = False

	QApplication.instance().aboutToQuit.connect(stop_running)

	lbrynet_daemon = LBRY(os.getenv("APPDIR", os.getcwd()) + "/lbrynet")
	
	pb_window = QWidget()
	pb_layout = QVBoxLayout()

	pb_label = QLabel(pb_window)
	pb_label.setText("Starting lbrynet daemon, please wait...")
	pb_layout.addWidget(pb_label)

	pb = QProgressBar(pb_window)
	pb.setMinimum(0)
	pb.setMaximum(0)
	pb_layout.addWidget(pb)

	pb_window.setLayout(pb_layout)
	pb_window.show()

	try:
		await lbrynet_daemon.start()
	except FileNotFoundError as e:
		print("Could not start lbrynet daemon:", e)
		exit(1)

	pb_window.deleteLater()
	window = LBRYClient(lbrynet_daemon)
	window.show()
	
	while running:
		await asyncio.sleep(0)
		
if __name__=="__main__":
	qasync.run(main())
