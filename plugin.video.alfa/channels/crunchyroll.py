# -*- coding: utf-8 -*-

import sys
PY3 = False
if sys.version_info[0] >= 3: PY3 = True; unicode = str; unichr = chr; long = int

if PY3:
    import urllib.parse as urllib                                               # Es muy lento en PY2.  En PY3 es nativo
else:
    import urllib                                                               # Usamos el nativo de PY2 que es más rápido

import re

from core import httptools
from core import scrapertools
from core.item import Item
from platformcode import config, logger

canonical = {
             'channel': 'crunchyroll', 
             'host': config.get_setting("current_host", 'crunchyroll', default=''), 
             'host_alt': ["http://www.crunchyroll.com"], 
             'host_black_list': [], 
             'pattern': '', 
             'status': 'ERROR 403 - INACTIVO', 
             'CF': True, 'CF_test': True, 'alfa_s': True
            }           # No funciona en este canal
host = canonical['host'] or canonical['host_alt'][0]
patron_domain = '(?:http.*\:)?\/\/(?:.*ww[^\.]*)?\.?(?:[^\.]+\.)?([\w|\-]+\.\w+)(?:\/|\?|$)'
domain = scrapertools.find_single_match(host, patron_domain)

headers = {'User-Agent': 'Mozilla/5.0', 'Accept-Language': '*'}
#proxys y sus lios... El proxy debe ser el mismo en el conector
proxy_i = "https://www.usa-proxy.org/"
proxy = "https://www.usa-proxy.org/browse.php?u=%s&b=4"


def set_weblang():
    
    #para el idoma usaremos la cookie c_locale y set_cookie
    langs = ['deDE', 'ptPT', 'frFR', 'itIT', 'enUS', 'esLA', 'esES']
    lang = langs[config.get_setting("crunchyrollidioma", canonical['channel'])]
    
    #creamos la cookie c_locale y le asignamos 7 dias de vida
    dict_cookie = {'domain': '.%s' % domain,
                    'name': 'c_locale',
                    'value': lang,
                    'expires': 604800}
    
    httptools.set_cookies(dict_cookie, clear=False)

def login():
    logger.info()
    set_weblang()
    

    login_page = host  + "/login"
    user = config.get_setting("crunchyrolluser", canonical['channel'])
    password = config.get_setting("crunchyrollpassword", canonical['channel'])
    if not user or not password:
        return False, "", ""
    page = get_source(login_page)
    data = page.data
    #redirección, necesaria para que funcione el login 
    login_page = page.url
    
    #Login con proxy
    check_login = 'href="/logout"'
    proxy_usa = config.get_setting("proxy_usa", canonical['channel'])
    if proxy_usa:
        check_login = 'logout&amp;b=4"'

    if not check_login in data:
        token = scrapertools.find_single_match(data, 'name="login_form\[_token\]" value="([^"]+)"')

        redirect_url = scrapertools.find_single_match(data, 'name="login_form\[redirect_url\]" value="([^"]+)"')
        post = "login_form%5Bname%5D=" + user + "&login_form%5Bpassword%5D=" + password + \
               "&login_form%5Bredirect_url%5D=" + redirect_url + "&login_form%5B_token%5D=" + token
        data = get_source(login_page, post=post).data

        if not check_login in data:
            if "Usuario %s no disponible" % user in data:
                return False, "El usuario de crunchyroll no existe.", ""
            elif '<li class="error">Captcha' in data:
                return False, "Es necesario resolver un captcha. Loguéate desde un navegador y vuelve a intentarlo", ""
            else:
                return False, "No se ha podido realizar el login.", ""
    
    data = get_source(host).data
    premium = scrapertools.find_single_match(data, ',"premium_status":"([^"]+)"')
    premium = premium.replace("_", " ").replace("free trial", "Prueba Gratuita").capitalize()
    locate = scrapertools.find_single_match(data, 'title="Your detected location is (.*?)."')
    if locate:
        premium += " - %s" % locate
    return True, "", premium


def mainlist(item):
    logger.info()
    itemlist = []

    proxy_usa = config.get_setting("proxy_usa", canonical['channel'])
    
    if proxy_usa:
        get_source(proxy_i)
        item.proxy = "usa"
    item.login = False
    error_message = ""
    
    item.login, error_message, premium = login()
    
    if not item.login and error_message:
        itemlist.append(Item(channel=item.channel, title=error_message, action="configuracion", folder=False ))
    
    elif item.login:
        itemlist.append(Item(channel=item.channel, title="Tipo de cuenta: %s" % premium, action="",
                                   folder=False ))
    if item.proxy:
        itemlist.append(Item(channel=item.channel, title="Usando proxy: %s" % item.proxy.capitalize(), 
                                    action="",  folder=False))
    
    itemlist.append(Item(channel=item.channel, title="Anime", action="", folder=False ))
    item.contentType = "tvshow"
    itemlist.append(
        Item(channel=item.channel, title="     Novedades", action="lista", url=host + "/videos/anime/updated/ajax_page?pg=0", page=0))
    itemlist.append(
        Item(channel=item.channel, title="     Popular", action="lista", url=host + "/videos/anime/popular/ajax_page?pg=0", page=0))
    itemlist.append(Item(channel=item.channel, title="     Emisiones Simultáneas", action="lista",
                               url=host + "/videos/anime/simulcasts/ajax_page?pg=0", page=0))
    itemlist.append(Item(channel=item.channel, title="     Índices", action="indices"))

    itemlist.append(Item(channel=item.channel, title="Drama", action="" ))
    itemlist.append(
        Item(channel=item.channel, title="     Popular", action="lista", url=host + "/videos/drama/popular/ajax_page?pg=0", page=0))
    itemlist.append(Item(channel=item.channel, title="     Índice Alfabético", action="indices",
                               url=host + "/videos/drama/alpha"))
    itemlist.append(Item(channel=item.channel, title="Buscar...", action="search",
                               url=host + "/search?q=%s&o=m" ))
    
    itemlist.append(Item(channel=item.channel, action="calendario", title="Calendario de Estrenos Anime" ,
                                   url=host + "/simulcastcalendar"))
    itemlist.append(Item(channel=item.channel, title="Configuración del canal", action="configuracion"))
    return itemlist


def configuracion(item):
    from platformcode import platformtools
    ret = platformtools.show_channel_settings()
    user = config.get_setting("crunchyrolluser", canonical['channel'])
    password = config.get_setting("crunchyrollpassword", canonical['channel'])
    sub = config.get_setting("crunchyrollsub", canonical['channel'])
    config.set_setting("crunchyrolluser", user)
    config.set_setting("crunchyrollpassword", password)
    values = [6, 5, 4, 3, 2, 1, 0]
    config.set_setting("crunchyrollsub", str(values[sub]))
    platformtools.itemlist_refresh()
    set_weblang()
    return ret


def lista(item):
    logger.info()
    itemlist = []
    data = get_source(item.url).data
    next = item.url.replace("?pg=%s" % item.page, "?pg=%s" % str(item.page + 1))
    data_next = get_source(next).data
    patron = '<li id="media_group_(\d+)".*?title="([^"]+)".*?href="([^"]+)".*?src="([^"]+)"' \
             '.*?<span class="series-data.*?>\s*([^<]+)</span>'
    matches = scrapertools.find_multiple_matches(data, patron)
    for id, title, url, thumb, videos in matches:
        if item.proxy:
            url = urllib.unquote(url.replace("/browse.php?u=", "").replace("&amp;b=4", ""))
        elif not item.proxy:
            url = host + url
        thumb = urllib.unquote(thumb.replace("/browse.php?u=", "").replace("_thumb", "_full").replace("&amp;b=4", ""))
        scrapedtitle = scrapertools.htmlclean("%s (%s)" % (title, videos.strip()))
        plot = scrapertools.find_single_match(data, '%s"\).data.*?description":"([^"]+)"' % id)
        if PY3:
            plot = plot.encode().decode('unicode-escape', "ignore")
        else:
            plot = unicode(plot, 'unicode-escape', "ignore")
        itemlist.append(Item(channel=item.channel, action="episodios", url=url, title=scrapedtitle, thumbnail=thumb,
                                   contentTitle=title, contentSerieName=title, infoLabels={'plot': plot}))
    if '<li id="media_group' in data_next:
        itemlist.append(Item(channel=item.channel, action="lista", url=next, title=">> Página Siguiente", page=item.page + 1))
    return itemlist


def episodios(item):
    logger.info()
    itemlist = []
    episodes_list_1 = []
    _season = 1

    data = get_source(item.url).data
    data = re.sub(r'\n|\t|\s{2,}', '', data)
    #logger.error(data)
    patron = '<li id="showview_videos.*?href="([^"]+)".*?(?:src|data-thumbnailUrl)="([^"]+)".*?media_id="([^"]+)"' \
             'style="width:(.*?)%.*?<span class="series-title.*?>\s*(.*?)</span>.*?<p class="short-desc".*?>' \
             '\s*(.*?)</p>.*?description":"(.*?)"'
    if data.count('class="season-dropdown') > 1:
        bloques = scrapertools.find_multiple_matches(data, 'class="season-dropdown[^"]+".*?title="([^"]+)"(.*?)</ul>')
        bloques.reverse()
        for season, b in bloques:
            matches = scrapertools.find_multiple_matches(b, patron)
            matches.reverse()
            if matches:
                itemlist.append(Item(channel=item.channel, action="", title=season ))
            for url, thumb, media_id, visto, scrapedtitle, subt, plot in matches:
                
                url_p = urllib.unquote(scrapertools.find_single_match(url, 'php\?u=([^*&]+)'))
                if not url_p:
                    url = host + url
                else:
                    url = url_p
                
                thumb = urllib.unquote(
                    thumb.replace("/browse.php?u=", "").replace("_wide.", "_full.").replace("&amp;b=4", ""))
                
                episode = scrapertools.find_single_match(scrapedtitle, '(\d+)')
                '''_season = scrapertools.find_single_match(season, '(\d+)$')
                if not _season:
                    _season = '1'
                '''
                title_s = scrapertools.find_single_match(season, '\((.*?)\)')

                count_title = '%sx%s %s' % (_season, episode, title_s)
                if count_title in episodes_list_1:
                    _season += 1
                    
                title = '%sx%s' %  (_season, episode)
                title = scrapertools.htmlclean("     %s - %s" % (title, subt))

                if not episode:
                    title = "     %s" % (scrapedtitle)
                    
                count_title = '%sx%s %s' % (_season, episode, title_s)
                episodes_list_1.append(count_title)
                
                if visto.strip() != "0":
                    title += " [COLOR limegreen][V][/COLOR]"
                if PY3:
                    plot = plot.encode().decode('unicode-escape', "ignore")
                else:
                    plot = unicode(plot, 'unicode-escape', "ignore")
                if not thumb.startswith('http'):
                    thumb = host+thumb

                if config.get_setting('unify'):
                    title += "[COLOR grey] [online][/COLOR]"
            
                itemlist.append(
                    Item(channel=item.channel, action="play", title=title, url=url, thumbnail=thumb, media_id=media_id,
                         server="crunchyroll", contentTitle=item.contentTitle,
                         contentSerieName=item.contentSerieName, plot=plot))
    else:
        matches = scrapertools.find_multiple_matches(data, patron)
        matches.reverse()
        for url, thumb, media_id, visto, title, subt, plot in matches:
            url_p = urllib.unquote(scrapertools.find_single_match(url, 'php\?u=([^*&]+)'))
            if not url_p:
                url = host + url
            else:
                url = url_p
            
            thumb = urllib.unquote(
                thumb.replace("/browse.php?u=", "").replace("_wide.", "_full.").replace("&amp;b=4", ""))
            
            episode = scrapertools.find_single_match(title, '(\d+)')
            title = '1x%s' % episode
            title = scrapertools.htmlclean("%s - %s" % (title, subt))
            
            if visto.strip() != "0":
                title += " [COLOR limegreen][V][/COLOR]"
            
            if PY3:
                plot = plot.encode().decode('unicode-escape', "ignore")
            else:
                plot = unicode(plot, 'unicode-escape', "ignore")
            
            if not thumb.startswith('http'):
                thumb = host+thumb
            
            if config.get_setting('unify'):
                title += "[COLOR grey] [online][/COLOR]"
            
            itemlist.append(
                Item(channel=item.channel, action="play", title=title, url=url, thumbnail=thumb, media_id=media_id,
                     server="crunchyroll", contentTitle=item.contentTitle,
                     contentSerieName=item.contentSerieName, plot=plot))
    
    if config.get_videolibrary_support() and len(itemlist) > 0:
        itemlist.append(Item(channel=item.channel, title="Añadir esta serie a la videoteca", 
                             url=item.url , action="add_serie_to_library",
                             proxy=item.proxy,
                             extra="episodios",  contentSerieName=item.contentSerieName))
    return itemlist

def search(item, texto):
    logger.info()
    texto = texto.replace(" ", "+")
    item.url = item.url % texto

    try:
        return search_results(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []

def search_results(item):
    logger.info()
    itemlist = []
    
    data = get_source(item.url).data
    data = re.sub(r'\n|\t|\s{2,}', '', data)
    
    bloque = scrapertools.find_single_match(data, 
                            '<ul class="search-results">(.*?)</ul>')
    patron = '<a href="([^"]+)".*?img src="([^"]+)".*?' #url, img
    patron += 'class="name">([^<]+).*?class="desc">([^<]+)' #title, plot
    matches = scrapertools.find_multiple_matches(bloque, patron)
    
    for url, img, title, plot in matches:
        if 'library' in url:
            continue
        if item.proxy:
            url = urllib.unquote(url.replace("/browse.php?u=", "").replace("&amp;b=4", ""))
        elif not item.proxy:
            url = host + url
        url = url.replace(proxy, "")
        img = urllib.unquote(
                img.replace("/browse.php?u=", "").replace("_thumb.", "_full.").replace("&amp;b=4", ""))
            
        title = title.strip()

        itemlist.append(Item(channel=item.channel, action="episodios", title=title, url=url,
                                    page=0, plot=plot, contentSerieName=title,
                                    thumbnail=img, contentTitle=title))
    
    return itemlist

def indices(item):
    logger.info()
    itemlist = []
    if not item.url:
        itemlist.append(Item(channel=item.channel, title="Alfabético", url=host + "/videos/anime/alpha"))
        itemlist.append(Item(channel=item.channel, title="Géneros", url=host + "/videos/anime"))
        if not item.proxy:
            itemlist.append(Item(channel=item.channel, title="Temporadas", url=host + "/videos/anime/seasons"))
    else:
        data = get_source(item.url).data
        if "Alfabético" in item.title:
            bloque = scrapertools.find_single_match(data, '<div class="content-menu cf">(.*?)</div>')
            matches = scrapertools.find_multiple_matches(bloque, '<a href="([^"]+)".*?>([^<]+)<')
            for url, title in matches:
                if "todo" in title:
                    continue
                if item.proxy:
                    url = proxy_i + url.replace("&amp;b=4/", "")
                else:
                    url = host + url
                itemlist.append(Item(channel=item.channel, action="alpha", title=title, url=url, page=0))
        elif "Temporadas" in item.title:
            bloque = scrapertools.find_single_match(data,
                                                    '<div class="season-selectors cf selectors">(.*?)<div id="container"')
            matches = scrapertools.find_multiple_matches(bloque, 'href="#([^"]+)".*?title="([^"]+)"')
            for url, title in matches:
                url += "/ajax_page?pg=0"
                if item.proxy:
                    url = proxy_i + url.replace("&amp;b=4/", "")
                else:
                    url = host + url
                itemlist.append(Item(channel=item.channel, action="lista", title=title, url=url, page=0))
        else:
            bloque = scrapertools.find_single_match(data, '<div class="genre-selectors selectors">(.*?)</div>')
            matches = scrapertools.find_multiple_matches(bloque, '<input id="([^"]+)".*?title="([^"]+)"')
            for url, title in matches:
                url = "%s/genres/ajax_page?pg=0&tagged=%s" % (item.url, url)
                if item.proxy:
                    url = proxy % url.replace("&", "%26")
                
                itemlist.append(Item(channel=item.channel, action="lista", title=title, url=url, page=0))
    return itemlist


def alpha(item):
    logger.info()
    itemlist = []
    data = get_source(item.url).data
    patron = '<div class="wrapper hover-toggle-queue.*?title="([^"]+)".*?href="([^"]+)".*?src="([^"]+)"' \
             '.*?<span class="series-data.*?>\s*([^<]+)</span>.*?<p.*?>(.*?)</p>'
    matches = scrapertools.find_multiple_matches(data, patron)
    for title, url, thumb, videos, plot in matches:
        if item.proxy:
            url = proxy_i + url.replace("&amp;b=4", "")
        else:
            url = host + url
        thumb = urllib.unquote(thumb.replace("/browse.php?u=", "").replace("_small", "_full").replace("&amp;b=4", ""))
        scrapedtitle = "%s (%s)" % (title, videos.strip())
        itemlist.append(Item(channel=item.channel, action="episodios", url=url, title=scrapedtitle, thumbnail=thumb,
                                   contentTitle=title, contentSerieName=title, infoLabels={'plot': plot}))
    return itemlist


def calendario(item):
    logger.info()
    itemlist = []
    data = get_source(item.url).data
    patron = '<div class="specific-date">.*?datetime="\d+-(\d+)-(\d+).*?class="day-name">.*?>\s*([^<]+)</time>(.*?)</section>'
    bloques = scrapertools.find_multiple_matches(data, patron)
    for mes, dia, title, b in bloques:
        patron = 'class="available-time">([^<]+)<.*?<cite itemprop="name">(.*?)</cite>.*?href="([^"]+)"' \
                 '.*?>\s*(.*?)\s*</a>(.*?)</article>'
        matches = scrapertools.find_multiple_matches(b, patron)
        if matches:
            title = "%s/%s - %s" % (dia, mes, title.strip())
            itemlist.append(Item(channel=item.channel, action="", title=title))
        for hora, title, url, subt, datos in matches:
            subt = subt.replace("Available", "Disponible").replace("Episode", "Episodio").replace("in ", "en ")
            subt = re.sub(r"\s{2,}", " ", subt)
            if "<time" in subt:
                subt = re.sub(r"<time.*?>", "", subt).replace("</time>", "")
            scrapedtitle = "   [%s] %s - %s" % (hora, scrapertools.htmlclean(title), subt)
            scrapedtitle = re.sub(r"\[email&#160;protected\]|\[email\xc2\xa0protected\]", "Idolm@ster", scrapedtitle)
            if "Disponible" in scrapedtitle:
                if item.proxy:
                    url = urllib.unquote(url.replace("/browse.php?u=", "").replace("&amp;b=4", ""))
                action = "play"
                server = "crunchyroll"
            else:
                action = ""
                server = ""
            thumb = scrapertools.find_single_match(datos, '<img class="thumbnail" src="([^"]+)"')
            if not thumb:
                thumb = scrapertools.find_single_match(datos, 'src="([^"]+)"')
            if thumb:
                thumb = urllib.unquote(thumb.replace("/browse.php?u=", "").replace("_thumb", "_full") \
                                       .replace("&amp;b=4", "").replace("_large", "_full"))
            itemlist.append(Item(channel=item.channel, action=action, url=url, title=scrapedtitle, contentTitle=title, thumbnail=thumb,
                                 contentSerieName=title, server=server))
    next = scrapertools.find_single_match(data, 'js-pagination-next"\s*href="([^"]+)"')
    if next:
        if item.proxy:
            next = proxy_i + url.replace("&amp;b=4", "")
        else:
            next = host + next
        itemlist.append(Item(channel=item.channel, action="calendario", url=next, title=">> Siguiente Semana"))
    prev = scrapertools.find_single_match(data, 'js-pagination-last"\s*href="([^"]+)"')
    if prev:
        if item.proxy:
            prev = proxy_i + url.replace("&amp;b=4", "")
        else:
            prev = host + prev
        itemlist.append(Item(channel=item.channel, action="calendario", url=prev, title="<< Semana Anterior"))
    return itemlist

def get_source(url, post=None):
    logger.info()
    proxy_usa = config.get_setting("proxy_usa", canonical['channel'])
    if proxy_usa and not proxy_i in url:
        url = proxy % url
    data = httptools.downloadpage(url, post=post)
    if 'div id="error">Hotlinking' in data.data:
        httptools.downloadpage(proxy_i)
        data = httptools.downloadpage(url, post=post)
    return data

def play(item):
    logger.info()
    if item.login and not "[V]" in item.title:
        post = "cbelapsed=60&h=&media_id=%s" % item.media_id + "&req=RpcApiVideo_VideoView&cbcallcount=1&ht=0" \
                                                               "&media_type=1&video_encode_id=0&playhead=10000"
        httptools.downloadpage(host + "/ajax/", post)
    return [item]
