
# xbmc
import xbmcgui

# python standart lib
import urllib
import sys
import os
import time
import json
import os.path
from datetime import datetime
import CommonFunctions
import socket

# application
from utilities import *
from app_apiclient import AppApiClient, AuthenticationError
from cache import StvList, DuplicateStvIdException
import top

ACTIONS_CLICK = [7, 100]
LIST_ITEM_CONTROL_ID = 500
HACK_GO_BACK = -2

common = CommonFunctions
common.plugin = "SynopsiTV"

__addon__  = xbmcaddon.Addon()
__addonpath__	= __addon__.getAddonInfo('path')
__addonname__ = __addon__.getAddonInfo('name')
__cwd__	= __addon__.getAddonInfo('path')
__author__  = __addon__.getAddonInfo('author')
__version__   = __addon__.getAddonInfo('version')
__profile__      = __addon__.getAddonInfo('profile')

itemFolderBack = {'name': '...', 'cover_medium': 'DefaultFolderBack.png', 'id': HACK_GO_BACK, 'type': 'HACK'}

open_dialogs = []
closed_dialogs = []
stashed_dialogs = []

def get_current_dialog():
	if open_dialogs:
		return open_dialogs[-1]
	else:
		return None

def close_current_dialog():
	d = get_current_dialog()
	if d:
		d.close()

	return d

def close_all_dialogs():
	while 1:
		d = close_current_dialog()
		if not d:
			break

def stash_all_dialogs():
	while 1:
		d = close_current_dialog()
		if not d:
			break

		stashed_dialogs.append(d)

def unstash_all_dialogs():
	log('stashed_dialogs:' + str(stashed_dialogs))
	for d in stashed_dialogs:
		open_dialogs.append(d)
		d.doModal()

def open_dialog(dialogClass, xmlFile, tpl_data, close=False):		
	if close:
		close_current_dialog()
			
	ui = dialogClass(xmlFile, __cwd__, "Default", data=tpl_data)
	ui.doModal()
		
	result = ui.result
	return result	

class MyDialog(xbmcgui.WindowXMLDialog):
	def __init__(self):
		self.parentWindow = open_dialogs[-1] if open_dialogs else None
		open_dialogs.append(self)
		self.result = None
	
	def close(self):
		# check if closing the currently opened dialog
		if open_dialogs[-1] != self:
			log('WARNING: Dialog queue inconsistency. Non-top dialog close')

		xbmcgui.WindowXMLDialog.close(self)
		open_dialogs.remove(self)
	
class ListDialog(MyDialog):
	""" Dialog for choosing movie corrections """
	def __init__(self, strXMLname, strFallbackPath, strDefaultName, **kwargs):
		super(ListDialog, self).__init__()
		self.data = kwargs['data']
		#~ self.cb_init_data = kwargs['cb_init_data']
		self.controlId = None
		self.selectedMovie = None

	def onInit(self):
		#~ self.cb_init_data()
		self.updateItems()
		
	def updateItems(self):
		items = []
		items.append(self._getListItem(itemFolderBack))
		for item in self.data['items']:
			li = self._getListItem(item)
			items.append(li)

		try:
			listControl = self.getControl(LIST_ITEM_CONTROL_ID)
			listControl.addItems(items)
			self.setFocus(listControl)
		except:
			log('Adding items failed')
	
	def refresh(self):
		self.updateItems()
		
	def setWatched(self, stv_id):
		for item in self.data['items']:
			if item['id'] == stv_id:
				item['watched'] = True

	def correctItem(self, old_stv_id, new_item):
		for index, item in enumerate(self.data['items']):
			if item['id'] == old_stv_id:
				self.data['items'][index] = new_item

	def _getListItem(self, item):
		#~ itemPath = 'mode=' + str(ActionCode.VideoDialogShowById) + '&amp;stv_id=' + str(item['id'])
		li = xbmcgui.ListItem(item['name'], iconImage=item['cover_medium'])
		li.setProperty('id', str(item['id']))
		li.setProperty('type', str(item['type']))
		#~ li.setProperty('path', str(itemPath))		
			
		# prefer already set custom_overlay, if N/A set custom overlay
		if item.get('custom_overlay'):
			li.setProperty('CustomOverlay', item['custom_overlay'])
		else:
			oc = self._getItemOverlayCode(item)
			li.setProperty('CustomOverlay', overlay_image[oc])
			
		return li

	def _getItemOverlayCode(self, item):
		overlayCode = OverlayCode.Empty
		if item.get('file'):
			overlayCode += OverlayCode.OnYourDisk
		if item.get('watched'):
			overlayCode += OverlayCode.AlreadyWatched
			
		return overlayCode

	def onFocus(self, controlId):
		self.controlId = controlId

	def onAction(self, action):
		#~ log('action: %s focused id: %s' % (str(action.getId()), str(self.controlId)))
		
		if action in CANCEL_DIALOG:
			self.close()
		# if user clicked/entered an item
		elif self.controlId == LIST_ITEM_CONTROL_ID and action in ACTIONS_CLICK:
			item = self.getControl(LIST_ITEM_CONTROL_ID).getSelectedItem()			
			stv_id = int(item.getProperty('id'))

			if stv_id == HACK_GO_BACK:
				self.close()
			elif stv_id == HACK_SHOW_ALL_LOCAL_MOVIES:
				show_submenu(ActionCode.LocalMovies)
			else:
				show_video_dialog({'type': item.getProperty('type'), 'id': stv_id}, close=False)

		

def open_list_dialog(tpl_data, close=False):
	open_dialog(ListDialog, "custom_MyVideoNav.xml", tpl_data, close)

def show_movie_list(item_list):
	open_list_dialog({ 'items': item_list })


def show_tvshows_episodes(stv_id):
	items = top.apiClient.get_tvshow_season(stv_id)
	open_list_dialog({'items': items })


class VideoDialog(MyDialog):
	"""
	Dialog about video information.
	"""
	def __init__(self, *args, **kwargs):
		super(VideoDialog, self).__init__()
		self.data = kwargs['data']
		self.controlId = None
		
	def _init_data(self):
		json_data = self.data
		if json_data.get('type') == 'tvshow':
			stv_details = top.apiClient.tvshow(json_data['id'], cast_props=defaultCastProps)
		else:
			stv_details = top.apiClient.title(json_data['id'], defaultDetailProps, defaultCastProps)
			
		top.stvList.updateTitle(stv_details)
		log('stv_details:' + dump(stv_details))

		# add xbmc id if available
		if json_data.has_key('id') and top.stvList.hasStvId(json_data['id']):
			cacheItem = top.stvList.getByStvId(json_data['id'])
			json_data['xbmc_id'] = cacheItem['id']
			try:
				json_data['xbmc_movie_detail'] = xbmc_rpc.get_details('movie', json_data['xbmc_id'], True)
			except:
				pass

		# add similars or seasons (bottom covers list)
		if stv_details['type'] == 'movie':
			# get similar movies
			t1_similars = top.apiClient.titleSimilar(stv_details['id'])
			if t1_similars.has_key('titles'):
				stv_details['similars'] = t1_similars['titles']
		elif stv_details['type'] == 'tvshow' and stv_details.has_key('seasons'):
			seasons = top.stvList.get_tvshow_local_seasons(stv_details['id'])
			log('seasons on disk:' + str(seasons))		
			stv_details['similars'] = [ {'id': i['id'], 'name': 'Season %d' % i['season_number'], 'cover_medium': i['cover_medium'], 'watched': i['episodes_count'] == i['watched_count'], 'file': i['season_number'] in seasons} for i in stv_details['seasons'] ]

		# similar overlays
		if stv_details.has_key('similars'):
			for item in stv_details['similars']:
				top.stvList.updateTitle(item)

				oc = 0
				if item.get('file'):
					oc |= OverlayCode.OnYourDisk
				if item.get('watched'):
					oc |= OverlayCode.AlreadyWatched

				if oc:
					item['overlay'] = overlay_image[oc]

		self.data = video_dialog_template_fill(stv_details, json_data)

	def onInit(self):
		self._init_data()
		win = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
		win.setProperty("Movie.Title", self.data["name"] + '[COLOR=gray] (' + unicode(self.data.get('year')) + ')[/COLOR]')
		win.setProperty("Movie.Plot", self.data["plot"])
		win.setProperty("Movie.Cover", self.data["cover_full"])

		for i in range(5):
			win.setProperty("Movie.Similar.{0}.Cover".format(i + 1), "default.png")

		# set available labels
		i = 1
		for key, value in self.data['labels']:
			win.setProperty("Movie.Label.{0}.1".format(i), key)
			win.setProperty("Movie.Label.{0}.2".format(i), value)
			i = i + 1

		# enable file playing and correction if available
		if self.data.has_key('file'):
			win.setProperty("Movie.File", self.data['file'])
			win.setProperty("Movie.FileInfo", '%s in [%s]' % (os.path.basename(self.data['file']), os.path.dirname(self.data['file'])))
			self.getControl(5).setEnabled(True)
			self.getControl(13).setEnabled(True)

		# disable watched button for non-released movies
		if self.data.has_key('release_date') and self.data['release_date'] > datetime.today():
			self.getControl(11).setEnabled(False)


		win.setProperty('BottomListingLabel', self.data['BottomListingLabel'])

		# similars
		items = []

		if self.data.has_key('similars'):
			for item in self.data['similars']:
				li = xbmcgui.ListItem(item['name'], iconImage=item['cover_medium'])
				if item.get('overlay'):
					li.setProperty('Overlay', item['overlay'])

				li.setProperty('id', str(item['id']))
				items.append(li)

			# similars alternative
			self.getControl(59).addItems(items)

		tmpTrail = self.data.get('trailer')
		if tmpTrail:
			_youid = tmpTrail.split("/")
			_youid.reverse()
			win.setProperty("Movie.Trailer.Id", str(_youid[0]))
		else:
			self.getControl(10).setEnabled(False)

		if not self.data['type'] in ['movie', 'episode']:
			self.getControl(11).setEnabled(False)

	def onClick(self, controlId):
		log('onClick: ' + str(controlId))

		# play
		if controlId == 5:
			close_all_dialogs()

		# trailer
		elif controlId == 10:
			close_all_dialogs()

		# already watched
		elif controlId == 11:
			rating = get_rating()
			if rating < 4:
				top.apiClient.titleWatched(self.data['id'], rating=rating)
				self.parentWindow.setWatched(self.data['id'])
			self.close()			
			self.parentWindow.refresh()

		# similars / tvshow seasons	cover
		elif controlId == 59:
			selected_item = self.getControl(59).getSelectedItem()
			stv_id = int(selected_item.getProperty('id'))

			if self.data['type'] == 'tvshow':
				show_tvshows_episodes(stv_id)				
			else:
				show_video_dialog_byId(stv_id, close=True)

		# correction
		elif controlId == 13:
			new_title = self.user_title_search()
			#~ log('old_title:' + dump(filtertitles(self.data)))
			#~ log('new_title:' + dump(filtertitles(new_title)))
			if new_title and self.data.has_key('id') and self.data.get('type') not in ['tvshow', 'season']:
				try:
					top.stvList.correct_title(self.data, new_title)
					self.close()
					self.parentWindow.correctItem(self.data['id'], new_title)
					self.parentWindow.refresh()
					show_video_dialog_byId(new_title['id'])
				except DuplicateStvIdException, e:
					log(unicode(e))
					dialog_ok('This title is already in library. Cannot correct identity to this title')


	def onFocus(self, controlId):
		self.controlId = controlId

	def onAction(self, action):
		#~ log('action: %s focused id: %s' % (str(action.getId()), str(self.controlId)))
		if (action.getId() in CANCEL_DIALOG):
			self.close()

	def user_title_search(self):
		try:
			search_term = common.getUserInput(t_correct_search_title, "")
			if search_term:
				results = top.apiClient.search(search_term, SEARCH_RESULT_LIMIT)
				if len(results['search_result']) == 0:
					dialog_ok('No results')
				else:
					data = { 'movies': results['search_result'] }
					return open_select_movie_dialog(data)
			else:
				dialog_ok(t_enter_title_to_search)
		except:
			dialog_ok('Search failed. Unknown error.')

		return


class SelectMovieDialog(MyDialog):
	""" Dialog for choosing movie corrections """
	def __init__(self, *args, **kwargs):
		super(SelectMovieDialog, self).__init__()
		self.data = kwargs['data']
		self.controlId = None
		self.selectedMovie = None

	def onInit(self):
		items = []
		for item in self.data['movies']:
			text = '%s [COLOR=gray](%s)[/COLOR]' % (item['name'], item.get('year', '?'))

			if item.get('type') == 'episode':
				text = 'S%sE%s - ' % (item.get('season_number', '??'), item.get('episode_number', '??')) + text

			li = xbmcgui.ListItem(text, iconImage=item['cover_medium'])
			li.setProperty('id', str(item['id']))
			li.setProperty('director', ', '.join(item.get('directors')) if item.has_key('directors') else t_unavail)
			cast = ', '.join([i['name'] for i in item['cast']]) if item.has_key('cast') else t_unavail			
			li.setProperty('cast', cast)
			items.append(li)

			self.getControl(59).addItems(items)

	def onClick(self, controlId):
		log('onClick: ' + str(controlId))
		if self.controlId == 59:
			sel_index = self.getControl(59).getSelectedPosition()
			self.result = self.data['movies'][sel_index]
			self.close()


	def onFocus(self, controlId):
		self.controlId = controlId

	def onAction(self, action):
		#~ log('action: %s focused id: %s' % (str(action.getId()), str(self.controlId)))
		if (action.getId() in CANCEL_DIALOG):
			self.close()


def open_select_movie_dialog(tpl_data):
	return open_dialog(SelectMovieDialog, "SelectMovie.xml", tpl_data)

def show_video_dialog_byId(stv_id, close=False):
	show_video_dialog({'id': stv_id}, close)	

def show_video_dialog(json_data, close=False):	
	open_video_dialog(json_data, close)


def video_dialog_template_fill(stv_details, json_data={}):

	log('show video:' + dump(json_data))
	log('stv_details video:' + dump(stv_details))

	# update empty stv_details with only nonempty values from xbmc
	for k, v in json_data.iteritems():
		if v and not stv_details.get(k):
			stv_details[k] = v

	tpl_data=stv_details

	# store file in tpl
	if tpl_data.has_key('xbmc_movie_detail'):
		if d.get('file'):
			tpl_data['file'] = d.get('file')

	# store labels
	labels = []	

	# append tuple to labels, translated by trfn, or the N/A string
	def append_tuple(stv_label, tpl_label, trfn):
		log('tpl_label:' + tpl_label)
		if tpl_data.get(tpl_label):
			log('tpl_data[tpl_label]:' + str(tpl_data[tpl_label]))
			val = trfn(tpl_data[tpl_label])
		else:
			val = t_unavail
				
		labels.append((stv_label, val))
	
	# translate functions
	def tr_genre(data): return ', '.join(data)
	def tr_cast(data): return ', '.join(map(lambda x:x['name'], data))
	def tr_runtime(data): return '%d min' % data

	append_tuple('Genre', 'genres', tr_genre)
	append_tuple('Cast', 'cast', tr_cast)
	append_tuple('Director', 'directors', tr_genre)		# reuse tr_genre here	
	append_tuple('Runtime', 'runtime', tr_runtime)
		
	if tpl_data.get('date'):
		tpl_data['release_date'] = datetime.fromtimestamp(tpl_data['date'])
		labels.append(('Release date', tpl_data['release_date'].strftime('%x')))
		
	tpl_data['labels'] = labels
	tpl_data['BottomListingLabel'] = type2listinglabel.get(tpl_data['type'], '')

	return tpl_data

def open_video_dialog(tpl_data, close=False):
	open_dialog(VideoDialog, "VideoInfo.xml", tpl_data, close)


def show_submenu(action_code, **kwargs):
	try:
		item_list = top.apiClient.get_item_list(action_code=action_code, **kwargs)
		
		# hack HACK_SHOW_ALL_LOCAL_MOVIES
		if action_code==ActionCode.LocalMovieRecco:
			item_list.append(item_show_all_movies_hack)

		if not item_list:
			raise ListEmptyException()

	except AuthenticationError as e:
		if dialog_check_login_correct():
			show_submenu(action_code, **kwargs)
			
		return

	except ListEmptyException:
		dialog_ok(exc_text_by_mode(action_code))
		return
		
	except:
		log(traceback.format_exc())
		dialog_ok(t_listing_failed)
			
	show_movie_list(item_list)

