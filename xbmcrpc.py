# xbmc
import xbmc, xbmcgui, xbmcaddon

# python standart lib
import json

# application
from utilities import *
from loggable import Loggable

props_all_tvshow = ['title', 'genre', 'year', 'rating', 'plot', 'studio', 'mpaa', 'cast', 'playcount', 'episode', 'imdbnumber', 'premiered', 'votes', 'lastplayed', 'fanart', 'thumbnail', 'file', 'originaltitle', 'sorttitle', 'episodeguide', 'season', 'watchedepisodes', 'dateadded', 'tag', 'art']
props_default_tvshow = ['file'] 

props_all_movie = ['title', 'genre', 'year', 'rating', 'director', 'trailer', 'tagline', 'plot', 'plotoutline', 'originaltitle', 'lastplayed', 'playcount', 'writer', 'studio', 'mpaa', 'cast', 'country', 'imdbnumber', 'runtime', 'set', 'showlink', 'streamdetails', 'top250', 'votes', 'fanart', 'thumbnail', 'file', 'sorttitle', 'resume', 'setid', 'dateadded', 'tag', 'art']
props_default_movie = ['file', 'lastplayed', 'playcount']


class xbmcRPCclient(Loggable):

	def __init__(self, logLevel = 0):
		super(xbmcRPCclient, self).__init__()
		self.__logLevel = logLevel

	def execute(self, methodName, params):
		req = {
			'params': params,
			'jsonrpc': '2.0',
			'method': methodName,
			'id': 1
		}


		self._log.debug('xbmc RPC request: ' + dump(req))

		response = xbmc.executeJSONRPC(json.dumps(req))

		json_response = json.loads(response)

		self._log.debug('xbmc RPC response: ' + dump(json_response))

		if json_response.has_key('error') and json_response['error']:
			self._log.debug('xbmc RPC ERROR: ' + json_response['error']['message'])
			self._log.debug('xbmc RPC request: ' + dump(req))
			self._log.debug('xbmc RPC response: ' + dump(json_response))
			raise Exception(json_response['error']['message'])

		return json_response['result']

	def get_movies(self, properties=props_default_movie, start=None, end=None):
		"""
		Get movies from xbmc library. Start is the first in list and end is the last.
		"""

		data = {
			'properties': properties
		}

		if start or end:
			data['limits'] = {}
			if start:
				data['limits']['start'] = start
			if end:
				data['limits']['end'] = end


		response = self.execute('VideoLibrary.GetMovies', data)

		return response

	def get_all_tvshows(self, properties=props_default_tvshow):
		"""
		Get movies from xbmc library. Start is the first in list and end is the last.
		"""

		response = self.execute(
			'VideoLibrary.GetTVShows',
			{
				'properties': properties
			}
		)

		return response

	def get_episodes(self, twshow_id, season=-1):
		"""
		Get episodes from xbmc library.
		"""
		properties = ['file', "lastplayed", "playcount", "season", "episode"]
		if season == -1:
			params = {
				'properties': properties,
				'tvshowid': twshow_id
			}
		else:
			params = {
				'properties': properties,
				'tvshowid': twshow_id,
				'season': season
			}

		response = self.execute(
			'VideoLibrary.GetEpisodes',
			params
		)

		return response

	def get_movie_details(self, movie_id, properties=props_all_movie):
		"""
		Get dict of movie_id details.
		"""

		response = self.execute(
			'VideoLibrary.GetMovieDetails',
			{
				'properties': properties,
				'movieid': movie_id
			}
		)

		return response['moviedetails']

	def get_tvshow_details(self, movie_id, properties=props_default_tvshow):
		"""
		Get dict of movie_id details. Docs: http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v6#VideoLibrary.GetTVShowDetails
		"""

		response = self.execute(
			'VideoLibrary.GetTVShowDetails',
			{
				'properties': properties,
				'tvshowid': movie_id
			}
		)

		return response

	def get_episode_details(self, movie_id):
		"""
		Get dict of movie_id details.
		"""
		properties = ['file', "lastplayed", "playcount", "season", "episode", "tvshowid"]

		response = self.execute(
			'VideoLibrary.GetEpisodeDetails',
			{
				'properties': properties,
				'episodeid': movie_id
			}
		)

		return response['episodedetails']

	def get_details(self, atype, aid):
		if atype == "movie":
			movie = self.get_movie_details(aid)
		elif atype == "episode":
			movie = self.get_episode_details(aid)
		elif atype == "tvshow":
			movie = self.get_tvshow_details(aid)
		else:
			raise Exception('Unknow video type: %s' % atype)

		return movie


	def GetInfoLabels(self):
		"""
		"""

		response = self.execute(
			'XBMC.GetInfoLabels',
			{
				'properties' : [ 'System.CpuFrequency', 'System.KernelVersion','System.FriendlyName','System.BuildDate','System.BuildVersion' ]
			}
		)

		return response


	def set_movie_details(self, details):
		"""
			Update the given movie with the given details. More info at http://wiki.xbmc.org/index.php?title=JSON-RPC_API/v6#VideoLibrary.SetMovieDetails
		"""

		response = self.execute(
			'VideoLibrary.SetMovieDetails',
			details
		)

		log('set_movie_details response: %s' % dump(response))
		return response


	def set_episode_details(self, details):
		response = self.execute(
			'VideoLibrary.SetEpisodeDetails',
			details
		)

		log('set_episode_details response: %s' % dump(response))
		return response


	def set_tvshow_details(self, details):
		response = self.execute(
			'VideoLibrary.SetTVShowDetails',
			details
		)

		log('set_tvshow_details response: %s' % dump(response))
		return response




# init local variables
xbmc_rpc = xbmcRPCclient()
