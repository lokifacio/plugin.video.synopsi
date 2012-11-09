
movies = test.jsfile
movie_response = { 'titles': movies }

reccoDefaultProps = ['id', 'cover_medium', 'name']
detailProps = [ 'id', 'cover_full', 'cover_large', 'cover_medium', 'cover_small', 'cover_thumbnail', 'date', 'genres', 'url', 'name', 'plot', 'released', 'trailer', 'type', 'year', 'directors', 'writers', 'runtime']

def log(msg):
    #logging.debug('ADDON: ' + str(msg))
    xbmc.log('ADDON / ' + str(msg))

def uniquote(s):
    return urllib.quote_plus(s.encode('ascii', 'backslashreplace'))

def uniunquote(uni):
    return urllib.unquote_plus(uni.decode('utf-8'))

def get_local_recco(movie_type):
    resRecco =  apiClient.profileRecco(movie_type, True, reccoDefaultProps)

    # log('local recco for ' + movie_type)
    # for title in resRecco['titles']:
    #    log('resRecco:' + title['name'])

    return resRecco


def get_global_recco(movie_type):
    resRecco =  apiClient.profileRecco(movie_type, False, reccoDefaultProps)

    # log('global recco for ' + movie_type)
    # for title in resRecco['titles']:
    #    log(title['name'])

    return resRecco


def get_unwatched_episodes():
    episodes =  apiClient.unwatchedEpisodes()

    log('unwatched episodes')
    for title in episodes['top']:
        log(title['name'])

    result = episodes['lineup']
    if not result:
        # let user know there is no lineup
        # provide some alternative listing
        result = episodes['upcoming']
        if not result:
            # let user know there is no upcoming
            # provide some alternative listing
            result = episodes['top']
        
    return result

def get_lists():
    log('get_lists')
    return movies


def get_movies_in_list(listid):
    log('get_movies_in_list')
    return movies


def get_trending_movies():
    log('get_trending_movies')
    return movies


def get_trending_tvshows():
    log('get_trending_tvshows')
    return movies


def get_items(_type, movie_type = None):
    log('get_items:' + str(_type))
    if _type == 1:
        return get_global_recco(movie_type)['titles']
    elif _type == 2:
        return get_local_recco(movie_type)['titles']
    elif _type == 3:
        return get_unwatched_episodes()
    elif _type == 4:
        return get_lists()
    elif _type == 5:
        return get_trending_movies()
    elif _type == 6:
        return get_trending_tvshows()

def add_to_list(movieid, listid):
    pass

def set_already_watched(stv_id, rating):
    log('already watched %d rating %d' % (stv_id, rating))
    apiClient.titleWatched(stv_id, rating=rating)

class VideoDialog(xbmcgui.WindowXMLDialog):
    """
    Dialog about video information.
    """
    def __init__(self, *args, **kwargs):
        self.data = kwargs['data']

    def onInit(self):
        win = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
        win.setProperty("Movie.Title", self.data["name"])
        win.setProperty("Movie.Plot", self.data["plot"])
        win.setProperty("Movie.Cover", self.data["cover_full"])
        # win.setProperty("Movie.Cover", "default.png")

        for i in range(5):
            win.setProperty("Movie.Similar.{0}.Cover".format(i + 1), "default.png")
            
        labels = dict()
        labels['Director'] = ', '.join(self.data['directors'])
        labels['Writer'] = ', '.join(self.data['writers'])
        labels['Runtime'] = '%d min' % self.data['runtime']
        labels['Release date'] = datetime.fromtimestamp(self.data['date']).strftime('%x')

        xlabels = dict()
        if self.data.has_key('xbmc_movie_detail'):
            xlabels["Director"] = ', '.join(self.data['xbmc_movie_detail']['director'])
            xlabels["Writer"] = ', '.join(self.data['xbmc_movie_detail']['writer'])
            xlabels["Runtime"] = self.data['xbmc_movie_detail']['runtime'] + ' min'
            xlabels["Release date"] = self.data['xbmc_movie_detail']['premiered']
            tFile = self.data['xbmc_movie_detail'].get('file')
            xbmc.log('file:' + str(tFile))
            if tFile:
                win.setProperty("Movie.File", tFile)
                self.getControl(5).setEnabled(True)

        labels.update(xlabels)

        # set available labels
        i = 1
        for key in labels.keys():
            win.setProperty("Movie.Label.{0}.1".format(i), key)
            win.setProperty("Movie.Label.{0}.2".format(i), labels[key])
            i = i + 1


        # similars
        i = 1
        if self.data.has_key('similars'):
            for item in self.data['similars']:
                win.setProperty("Movie.Similar.{0}.Label".format(i), item['name'])
                win.setProperty("Movie.Similar.{0}.Cover".format(i), item['cover_medium'])
                i = i + 1

        tmpTrail = self.data.get('trailer')
        if tmpTrail:
            _youid = tmpTrail.split("/")
            _youid.reverse()
            win.setProperty("Movie.Trailer.Id", str(_youid[0]))
        else:
            self.getControl(10).setEnabled(False)


    def onClick(self, controlId):
        log('onClick: ' + str(controlId))
        if controlId == 5: # play
            self.close()
        if controlId == 6: # add to list
            dialog = xbmcgui.Dialog()
            ret = dialog.select('Choose list', ['Watch later', 'Action', 'Favorite'])
        if controlId == 10: # trailer
            self.close()
        if controlId == 11: # already watched
            rating = get_rating()
            if rating < 4:
                set_already_watched(self.data['id'], rating)

    def onFocus(self, controlId):
        self.controlId = controlId

    def onAction(self, action):
        if (action.getId() in CANCEL_DIALOG):
            self.close()


def add_directory(name, url, mode, iconimage, atype, pluginhandle):
    u = sys.argv[0]+"?url="+uniquote(url)+"&mode="+str(mode)+"&name="+uniquote(name)+"&type="+str(atype)
    ok = True
    liz = xbmcgui.ListItem(name, iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    # liz.setInfo(type="Video", infoLabels={"Title": name} )
    # liz.setProperty("Fanart_Image", addonPath + 'fanart.jpg')
    ok=xbmcplugin.addDirectoryItem(handle=pluginhandle,url=u,listitem=liz,isFolder=True)
    return ok


def add_movie(movie, url, mode, iconimage, movieid):
    json_data = json.dumps(movie)
    u = sys.argv[0]+"?url="+uniquote(url)+"&mode="+str(mode)+"&name="+uniquote(movie.get('name'))+"&data="+uniquote(json_data)
    ok = True
    liz = xbmcgui.ListItem(movie.get('name'), iconImage="DefaultFolder.png", thumbnailImage=iconimage)
    liz.setInfo( type="Video", infoLabels={ "Title": "Titulok" } )
    liz.setProperty("Fanart_Image", addonPath + 'fanart.jpg')
    ok=xbmcplugin.addDirectoryItem(handle=int(sys.argv[1]),url=u,listitem=liz,isFolder=False)
    return ok


def show_categories(pluginhandle):
    """
    Shows initial categories on home screen.
    """
    xbmc.executebuiltin("Container.SetViewMode(503)")
    add_directory("Movie Recommendations", "url", 1, "list.png", 1, pluginhandle)
    add_directory("TV Show", "url", 11, "list.png", 1, pluginhandle)
    add_directory("Local Movie recommendations", "url", 12, "list.png", 2, pluginhandle)
    add_directory("Unwatched TV Show Episodes", "url", 20, "icon.png", 3, pluginhandle)
    add_directory("Upcoming TV Episodes", "url", 20, "icon.png", 3, pluginhandle)
    add_directory("Login and Settings", "url", 90, "icon.png", 1, pluginhandle)

def show_movies(url, type, movie_type, dirhandle):
    errorMsg = None
    try:
        for movie in get_items(type, movie_type):
            log(json.dumps(movie, indent=4))
            movie['type'] = movie_type
            add_movie(movie, "url",
                2, movie.get('cover_medium'), movie.get("id"))
    except AuthenticationError:
        errorMsg = True
    except:
        errorMsg = "Three was an error getting movie list"

    finally:
        xbmcplugin.endOfDirectory(dirhandle)
        xbmc.executebuiltin("Container.SetViewMode(500)")

    if errorMsg == True:
        if dialog_check_login_correct():
            xbmc.executebuiltin('Container.Refresh')
        else:
            xbmc.executebuiltin('Container.Update(plugin://plugin.video.synopsi, replace)')         
    elif errorMsg:
        # dialog with error message
        pass
  
    # xbmc.executebuiltin('Container.Update(plugin://plugin.video.synopsi?url=url&mode=999)')



def test_dialogwindow():
    xbmcplugin.endOfDirectory(pluginhandle)
    jdata = {
        'id': 1232,
        'name': 'XBMC Skinning Tutorial',
        'plot': 'Lorem Ipsum je fiktívny text, používaný pri návrhu tlačovín a typografie. Lorem Ipsum je štandardným výplňovým textom už od 16. storočia, keď neznámy tlačiar zobral sadzobnicu plnú tlačových znakov a pomiešal ich, aby tak vytvoril vzorkovú knihu. Prežil nielen päť storočí, ale aj skok do elektronickej sadzby, a pritom zostal v podstate nezmenený. Spopularizovaný bol v 60-tych rokoch 20.storočia, vydaním hárkov Letraset, ktoré obsahovali pasáže Lorem Ipsum, a neskôr aj publikačným softvérom ako Aldus PageMaker, ktorý obsahoval verzie Lorem Ipsum. Lorem Ipsum je fiktívny text, používaný pri návrhu tlačovín a typografie. Lorem Ipsum je štandardným výplňovým textom už od 16. storočia, keď neznámy tlačiar zobral sadzobnicu plnú tlačových znakov a pomiešal ich, aby tak vytvoril vzorkovú knihu. Prežil nielen päť storočí, ale aj skok do elektronickej sadzby, a pritom zostal v podstate nezmenený. Spopularizovaný bol v 60-tych rokoch 20.storočia, vydaním hárkov Letraset, ktoré obsahovali pasáže Lorem Ipsum, a neskôr aj publikačným softvérom ako Aldus PageMaker, ktorý obsahoval verzie Lorem Ipsum.',
        'cover_large': 'https://s3.amazonaws.com/titles.synopsi.tv/01498059-267.jpg',
        'xbmc_movie_detail': {
            'director': 'Ratan Hatan',
            'writer': 'Eugo Aianora',
            'runtime': '102',
            'premiered': '1. aug. 2012',
        }
    }
    show_video_dialog(0, 0, jdata)



def show_video_dialog(url, name, json_data):
    global stvList, apiClient

    stv_details = apiClient.title(json_data['id'], detailProps)

    # add xbmc id if available
    if stvList.hasStvId(json_data['id']):
        cacheItem = stvList.getByStvId(json_data['id'])
        json_data['xbmc_id'] = cacheItem['id']
        log('xbmc id:' + str(json_data['xbmc_id']))
        json_data['xbmc_movie_detail'] = get_details('movie', json_data['xbmc_id'], True)

    log('show video:' + json.dumps(json_data, indent=4))
    log('stv_details video:' + json.dumps(stv_details, indent=4))
    stv_details.update(json_data)
    json_data=stv_details

    # get similar movies
    similars = apiClient.titleSimilar(json_data['id'])
    if similars.has_key('titles'):
        json_data['similars'] = similars['titles']

    try:
        win = xbmcgui.Window(xbmcgui.getCurrentWindowDialogId())
    except ValueError, e:
        ui = VideoDialog("VideoInfo.xml", __cwd__, "Default", data=json_data)
        ui.doModal()
        del ui
    else:
        win = xbmcgui.WindowDialog(xbmcgui.getCurrentWindowDialogId())
        win.close()
        ui = VideoDialog("VideoInfo.xml", __cwd__, "Default", data=json_data)
        ui.doModal()
        del ui

def addon_openSettings():
    addon = get_current_addon()
    addon.openSettings()